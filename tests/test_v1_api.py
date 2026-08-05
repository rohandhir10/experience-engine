"""Tests for the public /v1/* API (server/main.py's "Public API (v1)"
section) and the /api/me/api-keys dashboard endpoints backing it. Real
sqlite database (API keys can't exist without one), same convention as
tests/test_accounts.py; engine calls are monkeypatched, same convention
as tests/test_server.py - no real HTTP server, no real LLM calls.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import server.db as db
import server.main as main
from server import accounts, api_keys


class _FakeRequest:
    """Stands in for FastAPI's Request - only what _client_ip and
    _require_api_key read."""

    def __init__(self, headers: dict | None = None):
        self.headers = headers or {}
        self.client = None


class _FakeClient:
    call_log: list = []

    def complete_json(self, *args, **kwargs):
        raise AssertionError("the real client should never be called")


class _FakeEngineResult:
    def __init__(self, sections=None, source_sections=None):
        self._sections = sections or []
        self._source_sections = source_sections or []

    def to_dict(self) -> dict:
        return {"sections": self._sections, "source_sections": self._source_sections}


class _FakeRuling:
    def __init__(self, final_line):
        self.final_line = final_line
        self.priority_tradeoffs_made = "test tradeoff"


class _FakeSectionResult:
    def __init__(self, section, final_line):
        self.section = section
        self.ruling = _FakeRuling(final_line)


def _fake_chapter_dna(**overrides):
    from engine.models import ChapterDNA

    defaults = dict(
        artistic_thesis="test thesis",
        genre_feel="drama",
        tone="tense",
        ongoing_plot_context="test context",
        characters=[],
    )
    defaults.update(overrides)
    return ChapterDNA(**defaults)


def _patch_song_engine(monkeypatch):
    def fake_run_engine(song, client=None, room_version="v1", apply_corrective_pass=False):
        return _FakeEngineResult()

    def fake_to_experience_result(client, result, result_id, explain_why_client=None):
        return {
            "id": result_id,
            "hook": "test hook",
            "sourceLanguage": "unspecified",
            "sections": [],
            "original": [],
        }

    monkeypatch.setattr(main, "run_engine", fake_run_engine)
    monkeypatch.setattr(main, "to_experience_result", fake_to_experience_result)
    monkeypatch.setattr(main, "create_default_client", lambda model=None: _FakeClient())


def _patch_comics_engine(monkeypatch):
    monkeypatch.setattr(main, "generate_chapter_dna", lambda chapter, client: _fake_chapter_dna())
    monkeypatch.setattr(
        main,
        "adapt_chapter",
        lambda chapter, dna, client: [
            _FakeSectionResult(b.id, f"adapted {b.id}") for b in chapter.bubbles
        ],
    )
    monkeypatch.setattr(main, "_translator_text", lambda result: f"literal {result.section}")
    monkeypatch.setattr(
        main, "_explain_why", lambda client, thesis, literal, adapted, tradeoffs: "why text"
    )
    monkeypatch.setattr(main, "create_default_client", lambda: object())


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/v1_api_test.db"
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


@pytest.fixture(autouse=True)
def _isolated_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(main.cache, "CACHE_DIR", tmp_path / "cache")


@pytest.fixture(autouse=True)
def _no_ip_quota(monkeypatch):
    """The per-IP browser quota is a separate dimension from the
    per-API-key limit this file is actually testing - keep it out of
    the way here the same way test_server.py does for its own tests."""
    monkeypatch.setattr(main, "DAILY_LIMIT", 0)


def _new_key(sqlite_db, sub="v1-user"):
    user_id = accounts.sync_user(sub, f"{sub}@m.com", None)["id"]
    # A real account now needs real credits to adapt anything at all
    # (server/credits.py) - a fresh user starts at 0, correctly, since
    # there's no free tier in this pricing model. This file is testing
    # API-key auth/rate-limiting, not credit sufficiency, so it grants
    # plenty upfront rather than letting every test incidentally exercise
    # the 402 path too.
    from server import credits

    credits.grant(user_id, 1000, reason="purchase", reference="test-grant")
    created = api_keys.generate_key(user_id, "test key")
    return user_id, created["key"], created["id"]


# ---------------------------------------------------------------------------
# /v1/adapt
# ---------------------------------------------------------------------------


def test_v1_adapt_succeeds_with_a_valid_key(sqlite_db, monkeypatch):
    _patch_song_engine(monkeypatch)
    user_id, raw_key, _ = _new_key(sqlite_db)

    request = main.AdaptRequest(text="line one\nline two")
    result = main.v1_adapt(request, _FakeRequest({"authorization": f"Bearer {raw_key}"}))

    assert result["id"]


def test_v1_adapt_records_history_under_the_keys_owner(sqlite_db, monkeypatch):
    _patch_song_engine(monkeypatch)
    user_id, raw_key, _ = _new_key(sqlite_db)

    request = main.AdaptRequest(text="a real v1 line\nsecond line")
    result = main.v1_adapt(request, _FakeRequest({"authorization": f"Bearer {raw_key}"}))

    history = accounts.list_adaptations(user_id)
    assert [entry["resultId"] for entry in history] == [result["id"]]
    assert history[0]["medium"] == "music"


def test_v1_adapt_rejects_a_missing_authorization_header(sqlite_db):
    request = main.AdaptRequest(text="line one\nline two")
    with pytest.raises(main.HTTPException) as exc_info:
        main.v1_adapt(request, _FakeRequest())
    assert exc_info.value.status_code == 401


def test_v1_adapt_rejects_an_unknown_key(sqlite_db):
    request = main.AdaptRequest(text="line one\nline two")
    with pytest.raises(main.HTTPException) as exc_info:
        main.v1_adapt(request, _FakeRequest({"authorization": "Bearer castia_sk_not-real"}))
    assert exc_info.value.status_code == 401


def test_v1_adapt_rejects_a_revoked_key(sqlite_db):
    user_id, raw_key, key_id = _new_key(sqlite_db)
    api_keys.revoke_key(user_id, key_id)

    request = main.AdaptRequest(text="line one\nline two")
    with pytest.raises(main.HTTPException) as exc_info:
        main.v1_adapt(request, _FakeRequest({"authorization": f"Bearer {raw_key}"}))
    assert exc_info.value.status_code == 401


def test_v1_adapt_enforces_the_per_key_daily_limit(sqlite_db, monkeypatch):
    _patch_song_engine(monkeypatch)
    monkeypatch.setattr(main, "API_DAILY_LIMIT", 1)
    _, raw_key, _ = _new_key(sqlite_db)
    headers = {"authorization": f"Bearer {raw_key}"}

    first = main.v1_adapt(main.AdaptRequest(text="one\ntwo"), _FakeRequest(headers))
    assert first["id"]

    with pytest.raises(main.HTTPException) as exc_info:
        main.v1_adapt(main.AdaptRequest(text="three\nfour"), _FakeRequest(headers))
    assert exc_info.value.status_code == 429


def test_v1_adapt_ignores_the_per_ip_browser_quota(sqlite_db, monkeypatch):
    """The per-IP CASTIA_DAILY_LIMIT is for the anonymous browser flow -
    an API-key caller is gated by its own per-key limit instead, even
    if the browser quota for that same IP is fully exhausted."""
    _patch_song_engine(monkeypatch)
    monkeypatch.setattr(main, "DAILY_LIMIT", 1)
    _, raw_key, _ = _new_key(sqlite_db)
    headers = {"authorization": f"Bearer {raw_key}"}

    # Exhaust the per-IP browser quota directly.
    from server import quota

    assert quota.check_and_increment("testclient", daily_limit=1) is True
    assert quota.check_and_increment("testclient", daily_limit=1) is False

    # The v1 caller still succeeds - a different gate entirely.
    result = main.v1_adapt(main.AdaptRequest(text="one\ntwo"), _FakeRequest(headers))
    assert result["id"]


# ---------------------------------------------------------------------------
# /v1/comics/adapt
# ---------------------------------------------------------------------------


def test_v1_comics_adapt_succeeds_with_a_valid_key(sqlite_db, monkeypatch):
    _patch_comics_engine(monkeypatch)
    user_id, raw_key, _ = _new_key(sqlite_db, sub="v1-comics-user")

    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[main.ComicsPanelText(id="panel-1", text="hello")],
    )
    result = main.v1_comics_adapt(request, _FakeRequest({"authorization": f"Bearer {raw_key}"}))

    assert result["id"]
    assert result["panels"][0]["id"] == "panel-1"

    history = accounts.list_adaptations(user_id)
    assert history[0]["medium"] == "webtoons"


def test_v1_comics_adapt_rejects_an_invalid_key(sqlite_db):
    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[main.ComicsPanelText(id="panel-1", text="hello")],
    )
    with pytest.raises(main.HTTPException) as exc_info:
        main.v1_comics_adapt(request, _FakeRequest({"authorization": "Bearer nope"}))
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# /api/me/api-keys (dashboard management)
# ---------------------------------------------------------------------------


def test_api_key_endpoints_round_trip(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("key-dash-1", "u@m.com", None)
    headers = {"X-Castia-User-Id": user["id"], "X-Castia-Internal-Secret": "right"}

    created = client.post("/api/me/api-keys", json={"name": "Production"}, headers=headers)
    assert created.status_code == 200
    body = created.json()
    assert body["key"].startswith("castia_sk_")
    key_id = body["id"]

    listed = client.get("/api/me/api-keys", headers=headers)
    assert listed.status_code == 200
    [entry] = listed.json()["apiKeys"]
    assert entry["id"] == key_id
    assert "key" not in entry
    assert entry["revokedAt"] is None

    revoked = client.delete(f"/api/me/api-keys/{key_id}", headers=headers)
    assert revoked.status_code == 200

    after = client.get("/api/me/api-keys", headers=headers)
    assert after.json()["apiKeys"][0]["revokedAt"] is not None


def test_revoking_a_key_via_the_dashboard_actually_blocks_v1_calls(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("key-dash-2", "u@m.com", None)
    headers = {"X-Castia-User-Id": user["id"], "X-Castia-Internal-Secret": "right"}

    created = client.post("/api/me/api-keys", json={"name": "To be revoked"}, headers=headers)
    raw_key = created.json()["key"]
    key_id = created.json()["id"]

    client.delete(f"/api/me/api-keys/{key_id}", headers=headers)

    request = main.AdaptRequest(text="line one\nline two")
    with pytest.raises(main.HTTPException) as exc_info:
        main.v1_adapt(request, _FakeRequest({"authorization": f"Bearer {raw_key}"}))
    assert exc_info.value.status_code == 401


def test_api_key_endpoints_require_the_internal_secret(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    response = client.get(
        "/api/me/api-keys", headers={"X-Castia-User-Id": "someone", "X-Castia-Internal-Secret": "wrong"}
    )
    assert response.status_code == 401


def test_revoking_someone_elses_key_is_a_404(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    owner = accounts.sync_user("key-owner", "u@m.com", None)
    other = accounts.sync_user("key-other", "u2@m.com", None)
    owner_headers = {"X-Castia-User-Id": owner["id"], "X-Castia-Internal-Secret": "right"}
    other_headers = {"X-Castia-User-Id": other["id"], "X-Castia-Internal-Secret": "right"}

    created = client.post("/api/me/api-keys", json={"name": "owner's"}, headers=owner_headers)
    key_id = created.json()["id"]

    response = client.delete(f"/api/me/api-keys/{key_id}", headers=other_headers)
    assert response.status_code == 404
