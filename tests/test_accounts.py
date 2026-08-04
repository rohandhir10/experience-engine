"""Accounts + per-user history, run against a real (sqlite file) database
via DATABASE_URL — these exercise the actual DB code paths in
server/accounts.py, not mocks. Postgres-specific behavior (the quota
UPSERT) is out of scope here, same disclosure as tests/test_quota.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import server.db as db
import server.main as main
from server import accounts, cache


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    """Point DATABASE_URL at a fresh sqlite file and reset server/db.py's
    cached engine/sessionmaker so it actually binds to it (get_engine
    caches globally — without the reset, the first test to run would pin
    every later test to its own URL)."""
    url = f"sqlite:///{tmp_path}/accounts_test.db"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)
    db.create_all()
    yield url
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)


@pytest.fixture()
def client():
    return TestClient(main.app)


# ---------------------------------------------------------------------------
# accounts.py against the real schema
# ---------------------------------------------------------------------------


def test_sync_creates_a_user_and_is_idempotent(sqlite_db):
    first = accounts.sync_user("google-sub-1", "a@b.com", "A")
    again = accounts.sync_user("google-sub-1", "a@b.com", "A")
    assert first["plan"] == "free"
    assert first["id"] == again["id"]


def test_sync_adopts_a_preexisting_email_only_row(sqlite_db):
    from server.db_models import User

    with db.session_scope() as session:
        session.add(User(email="pre@existing.com"))
        session.commit()
        pre_id = str(session.query(User).one().id)

    synced = accounts.sync_user("google-sub-2", "pre@existing.com", "Pre")
    assert synced["id"] == pre_id


def test_sync_refreshes_profile_fields(sqlite_db):
    accounts.sync_user("google-sub-3", "old@mail.com", "Old Name")
    accounts.sync_user("google-sub-3", "new@mail.com", "New Name")
    from server.db_models import User

    with db.session_scope() as session:
        user = session.query(User).filter_by(google_sub="google-sub-3").one()
        assert user.email == "new@mail.com"
        assert user.display_name == "New Name"


def test_record_adaptation_dedupes_per_user_and_result(sqlite_db):
    user = accounts.sync_user("google-sub-4", "u@m.com", None)
    accounts.record_adaptation(user["id"], "result-abc", "Hindi")
    accounts.record_adaptation(user["id"], "result-abc", "Hindi")
    from server.db_models import Adaptation

    with db.session_scope() as session:
        assert session.query(Adaptation).count() == 1


def test_list_adaptations_joins_display_fields_from_the_cached_result(sqlite_db):
    user = accounts.sync_user("google-sub-5", "u@m.com", None)
    cache.set(
        "result-xyz",
        {"hook": "Holding on is loyalty.", "sourceLanguage": "Hindi", "targetLanguage": "English"},
        source_text="some lyrics",
        target_language="English",
        source_language="Hindi",
    )
    accounts.record_adaptation(user["id"], "result-xyz", "Hindi")

    history = accounts.list_adaptations(user["id"])
    assert len(history) == 1
    entry = history[0]
    assert entry["resultId"] == "result-xyz"
    assert entry["hook"] == "Holding on is loyalty."
    assert entry["sourceLanguage"] == "Hindi"
    assert entry["targetLanguage"] == "English"
    assert entry["isFavorite"] is False


def test_history_survives_a_vanished_cached_result(sqlite_db):
    user = accounts.sync_user("google-sub-6", "u@m.com", None)
    accounts.record_adaptation(user["id"], "result-gone", "Korean")
    history = accounts.list_adaptations(user["id"])
    assert len(history) == 1
    assert history[0]["hook"] is None
    assert history[0]["sourceLanguage"] == "Korean"


def test_no_database_means_accounts_decline_not_crash(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert accounts.sync_user("sub", "e@m.com", None) is None
    assert accounts.list_adaptations("any-id") == []
    accounts.record_adaptation("any-id", "result", None)  # no-op, no raise


# ---------------------------------------------------------------------------
# Endpoint gating — the trust model
# ---------------------------------------------------------------------------


def test_sync_endpoint_is_503_when_secret_unconfigured(client, monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "")
    response = client.post("/api/users/sync", json={"google_sub": "s"})
    assert response.status_code == 503


def test_sync_endpoint_rejects_a_wrong_secret(client, monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    response = client.post(
        "/api/users/sync",
        json={"google_sub": "s"},
        headers={"X-Aura-Internal-Secret": "wrong"},
    )
    assert response.status_code == 401


def test_me_adaptations_requires_the_user_header(client, monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    response = client.get(
        "/api/me/adaptations", headers={"X-Aura-Internal-Secret": "right"}
    )
    assert response.status_code == 400


def test_forwarded_user_id_is_ignored_without_the_secret(client, monkeypatch, sqlite_db):
    """The security property: a browser hitting the API directly with a
    forged X-Aura-User-Id must NOT get history written for that user."""
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("google-sub-7", "u@m.com", None)
    cache.set("cached-song", {"hook": "x"}, source_text="la la la")

    response = client.post(
        "/api/adapt",
        json={"text": "la la la"},
        headers={"X-Aura-User-Id": user["id"]},  # no secret
    )
    assert response.status_code == 200
    assert accounts.list_adaptations(user["id"]) == []


def test_cache_hit_with_valid_secret_records_history(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("google-sub-8", "u@m.com", None)
    cache.set("cached-song-2", {"hook": "y"}, source_text="do re mi")

    response = client.post(
        "/api/adapt",
        json={"text": "do re mi"},
        headers={"X-Aura-User-Id": user["id"], "X-Aura-Internal-Secret": "right"},
    )
    assert response.status_code == 200
    history = accounts.list_adaptations(user["id"])
    assert len(history) == 1
