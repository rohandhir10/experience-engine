"""Public API key issuance, lookup, and per-key daily rate limiting.

Separate from server/accounts.py's browser-facing session model: a
signed-in user can hold several keys (one per project/integration), each
independently revocable, meant for server-to-server callers rather than
a browser. Same trust model as everywhere else in this project though -
only a hash is ever stored (`ApiKey.key_hash`), never the raw key, so a
leaked database can't be turned into working credentials. The raw key
is returned to the caller exactly once, at creation time.

Unlike accounts.py/cache.py/quota.py, there is no meaningful "no
database" fallback here: an API key IS a database row, and a key can't
be issued, looked up, or rate-limited without one. Every function below
degrades to a no-op/empty/None result when DATABASE_URL is unset, same
convention as the rest of this project, but the practical effect is
that the public API refuses every request outright without a database
configured - matching how server/main.py already treats
CASTIA_INTERNAL_API_SECRET being unset as "accounts are off", not a
silent partial mode.
"""
from __future__ import annotations

import hashlib
import os
import secrets

_KEY_PREFIX = "castia_sk_"
_RAW_KEY_BYTES = 32  # secrets.token_urlsafe(32) - well past brute-force range


def _use_db() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_key(user_id: str, name: str) -> dict | None:
    """Creates a new key for user_id. Returns the RAW key exactly once -
    {"id", "name", "key", "prefix", "createdAt"} - the caller (the
    dashboard settings page) must show this to the human immediately and
    never again; only the hash and a short prefix are ever persisted.
    """
    if not _use_db():
        return None

    import uuid as _uuid

    from . import db
    from .db_models import ApiKey

    raw_key = f"{_KEY_PREFIX}{secrets.token_urlsafe(_RAW_KEY_BYTES)}"
    prefix = raw_key[: len(_KEY_PREFIX) + 8]

    with db.session_scope() as session:
        row = ApiKey(
            user_id=_uuid.UUID(user_id),
            name=name,
            key_hash=_hash(raw_key),
            key_prefix=prefix,
        )
        session.add(row)
        session.commit()
        return {
            "id": str(row.id),
            "name": row.name,
            "key": raw_key,
            "prefix": row.key_prefix,
            "createdAt": row.created_at.isoformat(),
        }


def resolve_key(raw_key: str) -> dict | None:
    """Returns {"user_id", "key_id"} for a live (not revoked) key, or
    None for anything else - unrecognized, revoked, or no database.
    Does NOT touch last_used_at itself (see touch_last_used) so a
    read-only lookup and "record that this key was just used" stay
    separate concerns, same as elsewhere in this project (e.g. cache.get
    vs. accounts.record_adaptation being distinct steps in server/main.py).
    """
    if not _use_db():
        return None

    from . import db
    from .db_models import ApiKey

    with db.session_scope() as session:
        row = session.query(ApiKey).filter_by(key_hash=_hash(raw_key)).one_or_none()
        if row is None or row.revoked_at is not None:
            return None
        return {"user_id": str(row.user_id), "key_id": str(row.id)}


def touch_last_used(key_id: str) -> None:
    if not _use_db():
        return

    import uuid as _uuid
    from datetime import datetime, timezone

    from . import db
    from .db_models import ApiKey

    with db.session_scope() as session:
        row = session.get(ApiKey, _uuid.UUID(key_id))
        if row is not None:
            row.last_used_at = datetime.now(timezone.utc)
            session.commit()


def list_keys(user_id: str) -> list[dict]:
    """Newest-first, for the dashboard settings page. Never returns the
    raw key or its hash - key_prefix is the only identifying fragment
    shown once a key has been created, same convention GitHub/Stripe use
    so a listing page can't leak working credentials even if the page
    itself were somehow exposed."""
    if not _use_db():
        return []

    import uuid as _uuid

    from . import db
    from .db_models import ApiKey

    uid = _uuid.UUID(user_id)
    with db.session_scope() as session:
        rows = (
            session.query(ApiKey)
            .filter_by(user_id=uid)
            .order_by(ApiKey.created_at.desc())
            .all()
        )
        return [
            {
                "id": str(row.id),
                "name": row.name,
                "prefix": row.key_prefix,
                "createdAt": row.created_at.isoformat(),
                "lastUsedAt": row.last_used_at.isoformat() if row.last_used_at else None,
                "revokedAt": row.revoked_at.isoformat() if row.revoked_at else None,
            }
            for row in rows
        ]


def revoke_key(user_id: str, key_id: str) -> bool:
    """Scoped by user_id, same authorization boundary as
    accounts.set_favorite: a key that doesn't exist and a key that
    belongs to someone else are both just False, never distinguished.
    Idempotent - revoking an already-revoked key still returns True and
    leaves its original revoked_at untouched, rather than bumping it to
    now."""
    if not _use_db():
        return False

    import uuid as _uuid
    from datetime import datetime, timezone

    from . import db
    from .db_models import ApiKey

    with db.session_scope() as session:
        row = (
            session.query(ApiKey)
            .filter_by(id=_uuid.UUID(key_id), user_id=_uuid.UUID(user_id))
            .one_or_none()
        )
        if row is None:
            return False
        if row.revoked_at is None:
            row.revoked_at = datetime.now(timezone.utc)
            session.commit()
        return True


def check_and_increment_usage(key_id: str, daily_limit: int) -> bool:
    """Returns True if this request is allowed (and counts it against
    today's total for this key), False if key_id has already reached
    daily_limit today. daily_limit <= 0 disables the limit entirely.
    Same atomic-UPSERT-under-concurrency reasoning as
    server/quota.py::check_and_increment, keyed by api_key_id instead of
    ip - deliberately not reusing that function directly (it's
    hardcoded to the (day, ip) shape); this is the same pattern applied
    to a different dimension, not a refactor of the existing one.
    """
    if daily_limit <= 0:
        return True
    if not _use_db():
        return False

    import uuid as _uuid
    from datetime import date

    from sqlalchemy.dialects.postgresql import insert

    from . import db
    from .db_models import ApiKeyUsage

    today = date.today().isoformat()
    kid = _uuid.UUID(key_id)

    with db.session_scope() as session:
        # Increment-then-check, not check-then-increment: the atomic
        # UPSERT is what makes this race-free across concurrent
        # requests/processes, same reasoning as server/quota.py's
        # identical pattern for the (day, ip) dimension.
        stmt = (
            insert(ApiKeyUsage)
            .values(day=today, api_key_id=kid, count=1)
            .on_conflict_do_update(
                index_elements=["day", "api_key_id"],
                set_={"count": ApiKeyUsage.count + 1},
            )
            .returning(ApiKeyUsage.count)
        )
        new_count = session.execute(stmt).scalar_one()
        session.commit()
        return new_count <= daily_limit
