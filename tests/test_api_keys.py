"""server/api_keys.py, run against a real (sqlite file) database via
DATABASE_URL - same convention as tests/test_accounts.py: these exercise
the actual DB code paths, not mocks.
"""
from __future__ import annotations

import pytest

import server.db as db
from server import accounts, api_keys


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/api_keys_test.db"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)
    db.create_all()
    yield url
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)


def _user(sqlite_db, sub="key-user-1"):
    return accounts.sync_user(sub, f"{sub}@m.com", None)["id"]


def test_generate_key_returns_the_raw_key_exactly_once(sqlite_db):
    user_id = _user(sqlite_db)
    created = api_keys.generate_key(user_id, "My integration")

    assert created["name"] == "My integration"
    assert created["key"].startswith("castia_sk_")
    assert created["prefix"] == created["key"][: len(created["prefix"])]
    assert created["id"]
    assert created["createdAt"]


def test_generate_key_never_persists_the_raw_key(sqlite_db):
    user_id = _user(sqlite_db)
    created = api_keys.generate_key(user_id, "Leak check")

    from server.db_models import ApiKey

    with db.session_scope() as session:
        row = session.get(ApiKey, __import__("uuid").UUID(created["id"]))
        assert row.key_hash != created["key"]
        assert created["key"] not in row.key_hash


def test_resolve_key_finds_the_owning_user(sqlite_db):
    user_id = _user(sqlite_db)
    created = api_keys.generate_key(user_id, "resolve test")

    resolved = api_keys.resolve_key(created["key"])
    assert resolved == {"user_id": user_id, "key_id": created["id"]}


def test_resolve_key_rejects_an_unknown_key(sqlite_db):
    _user(sqlite_db)
    assert api_keys.resolve_key("castia_sk_not-a-real-key") is None


def test_resolve_key_rejects_a_revoked_key(sqlite_db):
    user_id = _user(sqlite_db)
    created = api_keys.generate_key(user_id, "will be revoked")

    assert api_keys.revoke_key(user_id, created["id"]) is True
    assert api_keys.resolve_key(created["key"]) is None


def test_touch_last_used_updates_the_timestamp(sqlite_db):
    user_id = _user(sqlite_db)
    created = api_keys.generate_key(user_id, "touch test")

    before = api_keys.list_keys(user_id)[0]
    assert before["lastUsedAt"] is None

    api_keys.touch_last_used(created["id"])

    after = api_keys.list_keys(user_id)[0]
    assert after["lastUsedAt"] is not None


def test_list_keys_never_includes_the_raw_key_or_hash(sqlite_db):
    user_id = _user(sqlite_db)
    created = api_keys.generate_key(user_id, "listing test")

    [entry] = api_keys.list_keys(user_id)
    assert entry["id"] == created["id"]
    assert entry["prefix"] == created["prefix"]
    assert "key" not in entry
    assert "keyHash" not in entry
    assert "key_hash" not in entry


def test_list_keys_is_newest_first(sqlite_db):
    user_id = _user(sqlite_db)
    api_keys.generate_key(user_id, "first")
    api_keys.generate_key(user_id, "second")

    names = [entry["name"] for entry in api_keys.list_keys(user_id)]
    assert names == ["second", "first"]


def test_revoke_key_is_scoped_to_the_owning_user(sqlite_db):
    """Same authorization boundary as accounts.set_favorite: a key
    belonging to someone else is indistinguishable from one that
    doesn't exist at all."""
    owner = _user(sqlite_db, "owner")
    other = _user(sqlite_db, "other")
    created = api_keys.generate_key(owner, "owner's key")

    assert api_keys.revoke_key(other, created["id"]) is False
    assert api_keys.resolve_key(created["key"]) is not None  # untouched


def test_revoke_key_returns_false_for_an_unknown_key(sqlite_db):
    user_id = _user(sqlite_db)
    assert api_keys.revoke_key(user_id, "00000000-0000-0000-0000-000000000000") is False


def test_revoke_key_is_idempotent(sqlite_db):
    user_id = _user(sqlite_db)
    created = api_keys.generate_key(user_id, "double revoke")

    assert api_keys.revoke_key(user_id, created["id"]) is True
    first_revoked_at = api_keys.list_keys(user_id)[0]["revokedAt"]

    assert api_keys.revoke_key(user_id, created["id"]) is True
    second_revoked_at = api_keys.list_keys(user_id)[0]["revokedAt"]

    assert first_revoked_at == second_revoked_at


def test_usage_limit_blocks_the_request_once_exceeded(sqlite_db):
    user_id = _user(sqlite_db)
    created = api_keys.generate_key(user_id, "rate limited")

    assert api_keys.check_and_increment_usage(created["id"], daily_limit=2) is True
    assert api_keys.check_and_increment_usage(created["id"], daily_limit=2) is True
    assert api_keys.check_and_increment_usage(created["id"], daily_limit=2) is False


def test_usage_limit_zero_disables_the_limit(sqlite_db):
    user_id = _user(sqlite_db)
    created = api_keys.generate_key(user_id, "unlimited")

    for _ in range(5):
        assert api_keys.check_and_increment_usage(created["id"], daily_limit=0) is True


def test_usage_is_tracked_independently_per_key(sqlite_db):
    user_id = _user(sqlite_db)
    key_a = api_keys.generate_key(user_id, "a")
    key_b = api_keys.generate_key(user_id, "b")

    assert api_keys.check_and_increment_usage(key_a["id"], daily_limit=1) is True
    # key_a is now at its limit, but key_b hasn't been touched at all.
    assert api_keys.check_and_increment_usage(key_a["id"], daily_limit=1) is False
    assert api_keys.check_and_increment_usage(key_b["id"], daily_limit=1) is True


def test_no_database_means_api_keys_decline_not_crash(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert api_keys.generate_key("any-id", "name") is None
    assert api_keys.resolve_key("castia_sk_whatever") is None
    assert api_keys.list_keys("any-id") == []
    assert api_keys.revoke_key("any-id", "any-key-id") is False
    assert api_keys.check_and_increment_usage("any-key-id", daily_limit=5) is False
    api_keys.touch_last_used("any-key-id")  # no-op, no raise
