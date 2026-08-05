"""Paddle Billing webhook handling: signature verification and crediting
a purchase/subscription-renewal transaction to the right account.

Verified against Paddle's own documented format (developer.paddle.com/
webhooks/overview and their signature-verification guide), not guessed:
the `Paddle-Signature` header is `ts=<unix ts>;h1=<hex hmac>`, and the
HMAC is SHA-256 of `f"{ts}:{raw_body}"` using the webhook's notification
secret, over the exact bytes Paddle sent - reformatting the body before
hashing (even just re-serializing the same JSON) produces a different
signature, so this must run against the raw request body, never the
parsed dict (server/main.py's webhook route passes `await request.body()`
straight through, before FastAPI/Pydantic ever touches it).

Idempotency: Paddle documents that the same event can be redelivered
(retry on a slow or ambiguous response from us), and crediting a
purchase twice is a real money bug, not a cosmetic one - handled via
PaddleProcessedEvent's atomic INSERT (db_models.py's docstring), not a
"have we seen this event_id" SELECT, which two near-simultaneous
deliveries of the same event could both pass before either commits.

Deliberately narrow: only transaction.completed is handled. Paddle fires
that same event for both one-time pack purchases and every subscription
renewal (a subscription bills via transactions same as a one-time
purchase), so crediting is entirely price-id-driven - there is no
separate subscription-specific code path to keep in sync with it.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time

logger = logging.getLogger("castia.server")

# Paddle's own guidance: reject a webhook whose timestamp is too old, to
# block a replayed (captured-and-resent) request. Their docs are quoted
# as "5-30 seconds" for this tolerance, but that's tight enough to reject
# a legitimate delivery under ordinary network/queueing latency - 5
# minutes is the more commonly used real-world figure for this exact
# check (e.g. Stripe's own webhook-signature guidance), and is what's
# used here; tightenable via env var without a code change if that turns
# out to be too loose in practice.
MAX_SIGNATURE_AGE_SECONDS = int(os.environ.get("CASTIA_PADDLE_MAX_SIGNATURE_AGE", "300"))


class PaddleWebhookError(Exception):
    """Raised for a webhook that fails verification - a bad/missing
    signature, an unparseable signature header, or one that's simply too
    old. The caller (server/main.py) turns this into a 400, not a 500:
    the request itself is the problem, not our server."""


def _price_credits_map() -> dict[str, int]:
    """CASTIA_PADDLE_PRICE_CREDITS: a JSON object mapping a Paddle price
    id (created in Paddle's own dashboard - this project has no API
    credentials to create them, only to receive webhooks about them) to
    the credits one unit of that price grants, e.g.
    '{"pri_01abc...": 144, "pri_01def...": 272}'. Empty/unset means every
    price is unrecognized, which is a safe default (nothing gets
    credited from a purchase we can't identify) rather than a crash.
    """
    raw = os.environ.get("CASTIA_PADDLE_PRICE_CREDITS", "")
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("CASTIA_PADDLE_PRICE_CREDITS is not valid JSON - ignoring it")
        return {}
    return {str(k): int(v) for k, v in parsed.items()}


def verify_signature(raw_body: bytes, signature_header: str | None, secret: str) -> None:
    """Raises PaddleWebhookError on any failure; returns None (no
    exception) when the signature checks out. `secret` is passed in
    rather than read from the environment here so this function is
    independently testable against a known secret, not tied to
    monkeypatching os.environ.
    """
    if not signature_header:
        raise PaddleWebhookError("Missing Paddle-Signature header.")

    parts = dict(
        part.split("=", 1) for part in signature_header.split(";") if "=" in part
    )
    ts = parts.get("ts")
    h1 = parts.get("h1")
    if not ts or not h1:
        raise PaddleWebhookError("Malformed Paddle-Signature header.")

    try:
        ts_int = int(ts)
    except ValueError as exc:
        raise PaddleWebhookError("Malformed Paddle-Signature timestamp.") from exc

    age = abs(time.time() - ts_int)
    if age > MAX_SIGNATURE_AGE_SECONDS:
        raise PaddleWebhookError(
            f"Paddle-Signature timestamp is {age:.0f}s old, over the "
            f"{MAX_SIGNATURE_AGE_SECONDS}s tolerance - possible replay."
        )

    signed_payload = f"{ts}:".encode() + raw_body
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    # Constant-time comparison - a real Paddle security advisory
    # (GHSA-mjgf-xj26-9qf9) exists for exactly the class of bug a plain
    # `==` here would be: a non-constant-time compare leaks how many
    # leading bytes matched via response timing, letting an attacker
    # forge a valid signature byte-by-byte.
    if not hmac.compare_digest(expected, h1):
        raise PaddleWebhookError("Signature does not match.")


def _mark_event_processed(event_id: str) -> bool:
    """True the first time this event_id is seen, False if it's a
    redelivery already recorded - see PaddleProcessedEvent's docstring
    for why this has to be an atomic insert, not a SELECT then INSERT.
    Without a database there are no accounts to credit either, so this
    returns False (treat as already-processed / do nothing) rather than
    pretending idempotency it can't actually provide.
    """
    if not os.environ.get("DATABASE_URL"):
        return False

    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy.exc import IntegrityError

    from . import db
    from .db_models import PaddleProcessedEvent

    with db.session_scope() as session:
        try:
            stmt = (
                insert(PaddleProcessedEvent)
                .values(event_id=event_id)
                .on_conflict_do_nothing(index_elements=["event_id"])
                .returning(PaddleProcessedEvent.event_id)
            )
            row = session.execute(stmt).first()
            session.commit()
            return row is not None
        except IntegrityError:
            # sqlite (local dev/tests) doesn't support ON CONFLICT the
            # same way for every dialect path here - a plain insert that
            # raises on the duplicate primary key is the same atomic
            # guarantee (the second insert simply can't succeed).
            session.rollback()
            return False


def handle_transaction_completed(data: dict) -> None:
    """`data` is the webhook envelope's `data` object for a
    transaction.completed event - the transaction itself, whether it
    came from a one-time pack purchase or a subscription renewal
    (Paddle bills both through a transaction; there's nothing in this
    event that needs to distinguish them, see this module's docstring).
    """
    transaction_id = data.get("id")
    user_id = (data.get("custom_data") or {}).get("user_id")
    if not user_id:
        # Checkout was opened without custom_data.user_id attached (see
        # web/lib/paddle.ts) - can't credit an account we can't identify.
        # Logged, not raised: the webhook itself is valid and Paddle
        # doesn't need to retry a malformed integration on our end.
        logger.error(
            "Paddle transaction %s completed with no custom_data.user_id - cannot credit it",
            transaction_id,
        )
        return

    price_credits = _price_credits_map()
    total_credits = 0
    for item in data.get("items", []):
        price_id = (item.get("price") or {}).get("id")
        quantity = item.get("quantity", 1)
        per_unit = price_credits.get(price_id)
        if per_unit is None:
            logger.warning(
                "Paddle transaction %s: unrecognized price %r - not credited "
                "(is CASTIA_PADDLE_PRICE_CREDITS missing this price id?)",
                transaction_id, price_id,
            )
            continue
        total_credits += per_unit * quantity

    if total_credits <= 0:
        return

    from . import credits

    new_balance = credits.grant(
        user_id, total_credits, reason="purchase", reference=transaction_id
    )
    if new_balance is None:
        logger.error(
            "Paddle transaction %s: grant to user %s failed (unknown user or no database)",
            transaction_id, user_id,
        )


def handle_webhook(raw_body: bytes, signature_header: str | None, secret: str) -> None:
    """Verifies and dispatches one webhook delivery. Raises
    PaddleWebhookError on a bad signature (the caller turns that into a
    400); any other event type than transaction.completed is
    acknowledged and ignored, not an error - Paddle sends many event
    types this product has no reason to act on.
    """
    verify_signature(raw_body, signature_header, secret)
    payload = json.loads(raw_body)

    event_id = payload.get("event_id")
    if event_id and not _mark_event_processed(event_id):
        logger.info("Paddle event %s already processed - skipping (redelivery)", event_id)
        return

    event_type = payload.get("event_type")
    if event_type == "transaction.completed":
        handle_transaction_completed(payload.get("data") or {})
    else:
        logger.info("Paddle event %s (%s) acknowledged, no handler", event_id, event_type)
