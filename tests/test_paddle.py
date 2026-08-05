"""server/paddle.py: signature verification (pure, no database) and
event handling (idempotency + crediting, run against a real sqlite
database, same convention as tests/test_credits.py).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

import server.db as db
import server.main as main
from server import credits, paddle

SECRET = "whsec_test_secret"


def _sign(body: bytes, secret: str = SECRET, ts: int | None = None) -> str:
    ts = ts if ts is not None else int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}:".encode() + body, hashlib.sha256).hexdigest()
    return f"ts={ts};h1={sig}"


# ---------------------------------------------------------------------------
# verify_signature - pure function, no database
# ---------------------------------------------------------------------------


def test_verify_signature_accepts_a_correctly_signed_payload():
    body = b'{"event_id": "evt_1"}'
    paddle.verify_signature(body, _sign(body), SECRET)  # must not raise


def test_verify_signature_rejects_a_wrong_secret():
    body = b'{"event_id": "evt_1"}'
    with pytest.raises(paddle.PaddleWebhookError):
        paddle.verify_signature(body, _sign(body), "wrong-secret")


def test_verify_signature_rejects_a_tampered_body():
    body = b'{"event_id": "evt_1"}'
    signature = _sign(body)
    tampered = b'{"event_id": "evt_2"}'
    with pytest.raises(paddle.PaddleWebhookError):
        paddle.verify_signature(tampered, signature, SECRET)


def test_verify_signature_rejects_a_missing_header():
    with pytest.raises(paddle.PaddleWebhookError, match="Missing"):
        paddle.verify_signature(b"{}", None, SECRET)


def test_verify_signature_rejects_a_malformed_header():
    with pytest.raises(paddle.PaddleWebhookError, match="Malformed"):
        paddle.verify_signature(b"{}", "not-the-right-format", SECRET)


def test_verify_signature_rejects_a_stale_timestamp():
    body = b'{"event_id": "evt_1"}'
    old_ts = int(time.time()) - paddle.MAX_SIGNATURE_AGE_SECONDS - 60
    with pytest.raises(paddle.PaddleWebhookError, match="replay"):
        paddle.verify_signature(body, _sign(body, ts=old_ts), SECRET)


# ---------------------------------------------------------------------------
# handle_webhook / handle_transaction_completed - real sqlite database
# ---------------------------------------------------------------------------


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/paddle_test.db"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)
    db.create_all()
    yield url
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)


def _make_user() -> str:
    from server.db_models import User

    with db.session_scope() as session:
        user = User(credits=0)
        session.add(user)
        session.commit()
        return str(user.id)


def _transaction_payload(
    event_id: str, user_id: str, price_id: str, quantity: int = 1, transaction_id: str = "txn_1"
) -> bytes:
    return json.dumps(
        {
            "event_id": event_id,
            "event_type": "transaction.completed",
            "data": {
                "id": transaction_id,
                "custom_data": {"user_id": user_id},
                "items": [{"price": {"id": price_id}, "quantity": quantity}],
            },
        }
    ).encode()


def test_handle_webhook_credits_the_account_named_in_custom_data(sqlite_db, monkeypatch):
    monkeypatch.setenv("CASTIA_PADDLE_PRICE_CREDITS", json.dumps({"pri_starter": 144}))
    user_id = _make_user()
    body = _transaction_payload("evt_1", user_id, "pri_starter")

    paddle.handle_webhook(body, _sign(body), SECRET)

    assert credits.get_balance(user_id) == 144
    [row] = credits.list_transactions(user_id)
    assert row["reason"] == "purchase"
    assert row["reference"] == "txn_1"


def test_handle_webhook_multiplies_by_quantity(sqlite_db, monkeypatch):
    monkeypatch.setenv("CASTIA_PADDLE_PRICE_CREDITS", json.dumps({"pri_starter": 144}))
    user_id = _make_user()
    body = _transaction_payload("evt_1", user_id, "pri_starter", quantity=3)

    paddle.handle_webhook(body, _sign(body), SECRET)

    assert credits.get_balance(user_id) == 432


def test_handle_webhook_is_idempotent_on_a_redelivered_event(sqlite_db, monkeypatch):
    """The actual scenario PaddleProcessedEvent exists for: Paddle sends
    the same event_id twice. Must credit exactly once, not twice."""
    monkeypatch.setenv("CASTIA_PADDLE_PRICE_CREDITS", json.dumps({"pri_starter": 144}))
    user_id = _make_user()
    body = _transaction_payload("evt_1", user_id, "pri_starter")

    paddle.handle_webhook(body, _sign(body), SECRET)
    paddle.handle_webhook(body, _sign(body), SECRET)  # redelivery of the same event

    assert credits.get_balance(user_id) == 144
    assert len(credits.list_transactions(user_id)) == 1


def test_handle_webhook_rejects_an_invalid_signature_before_touching_the_database(
    sqlite_db, monkeypatch
):
    monkeypatch.setenv("CASTIA_PADDLE_PRICE_CREDITS", json.dumps({"pri_starter": 144}))
    user_id = _make_user()
    body = _transaction_payload("evt_1", user_id, "pri_starter")

    with pytest.raises(paddle.PaddleWebhookError):
        paddle.handle_webhook(body, _sign(body, secret="wrong"), SECRET)

    assert credits.get_balance(user_id) == 0


def test_handle_webhook_ignores_an_unrecognized_price_without_crediting(sqlite_db, monkeypatch):
    monkeypatch.setenv("CASTIA_PADDLE_PRICE_CREDITS", json.dumps({"pri_starter": 144}))
    user_id = _make_user()
    body = _transaction_payload("evt_1", user_id, "pri_unknown")

    paddle.handle_webhook(body, _sign(body), SECRET)  # must not raise

    assert credits.get_balance(user_id) == 0


def test_handle_webhook_logs_and_skips_when_custom_data_has_no_user_id(sqlite_db, monkeypatch):
    monkeypatch.setenv("CASTIA_PADDLE_PRICE_CREDITS", json.dumps({"pri_starter": 144}))
    body = json.dumps(
        {
            "event_id": "evt_1",
            "event_type": "transaction.completed",
            "data": {
                "id": "txn_1",
                "custom_data": {},
                "items": [{"price": {"id": "pri_starter"}, "quantity": 1}],
            },
        }
    ).encode()

    paddle.handle_webhook(body, _sign(body), SECRET)  # must not raise


def test_handle_webhook_ignores_other_event_types(sqlite_db, monkeypatch):
    user_id = _make_user()
    body = json.dumps(
        {"event_id": "evt_1", "event_type": "subscription.created", "data": {"id": "sub_1"}}
    ).encode()

    paddle.handle_webhook(body, _sign(body), SECRET)  # must not raise

    assert credits.get_balance(user_id) == 0


# ---------------------------------------------------------------------------
# POST /webhooks/paddle - the actual route, via a real TestClient (needed
# for the raw-body/async plumbing test_server.py's plain-function-call
# convention can't exercise)
# ---------------------------------------------------------------------------


@pytest.fixture()
def api_client():
    return TestClient(main.app)


def test_webhook_route_is_503_when_no_secret_is_configured(api_client, monkeypatch):
    monkeypatch.setattr(main, "PADDLE_WEBHOOK_SECRET", "")
    response = api_client.post("/webhooks/paddle", content=b"{}")
    assert response.status_code == 503


def test_webhook_route_is_400_on_an_invalid_signature(api_client, monkeypatch):
    monkeypatch.setattr(main, "PADDLE_WEBHOOK_SECRET", SECRET)
    response = api_client.post(
        "/webhooks/paddle",
        content=b'{"event_id": "evt_1"}',
        headers={"paddle-signature": "ts=1;h1=deadbeef"},
    )
    assert response.status_code == 400


def test_webhook_route_credits_the_account_on_a_valid_signed_request(
    sqlite_db, api_client, monkeypatch
):
    monkeypatch.setattr(main, "PADDLE_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("CASTIA_PADDLE_PRICE_CREDITS", json.dumps({"pri_starter": 144}))
    user_id = _make_user()
    body = _transaction_payload("evt_route_1", user_id, "pri_starter")

    response = api_client.post(
        "/webhooks/paddle", content=body, headers={"paddle-signature": _sign(body)}
    )

    assert response.status_code == 200
    assert credits.get_balance(user_id) == 144
