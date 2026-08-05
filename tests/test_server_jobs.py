"""Tests for the async job endpoints (/api/adapt/start, /api/adapt/jobs/{id})
- server/main.py's fix for a real multi-section song's engine run (minutes,
several sequential LLM calls per section) exceeding a serverless function's
timeout (Vercel's 60s Hobby-plan ceiling, web/app/api/adapt/route.ts).

Mocks server.main._run_adaptation entirely (no real LLM calls, no real
engine run) - this verifies the job lifecycle, threading, routing, and
error propagation /api/adapt/start adds, not adaptation quality, which
tests/test_writers_room_v1.py and friends already cover.
"""
from __future__ import annotations

import time
from collections import defaultdict

import pytest
from fastapi.testclient import TestClient

import server.main as main
from engine.llm_client import LLMError
from server import jobs, quota

VALID_BODY = {"text": "line one\n\nline two", "target_language": "English"}


@pytest.fixture(autouse=True)
def _reset_module_state(monkeypatch):
    # jobs/quota are in-memory (no DATABASE_URL in the test environment) -
    # reset their module-level dicts per test so runs don't leak across
    # tests (or hit the quota). MONTHLY_LIMIT is zeroed rather than just
    # resetting _memory_monthly_counts (quota.py's real cost ceiling,
    # separate from the daily anti-burst one, is never reset by this
    # file's own dict-reset above) - a bug that stayed invisible only
    # because this file alone never made enough real quota-consuming
    # calls in one session to trip MONTHLY_LIMIT's real default; the same
    # convention tests/test_server.py's _no_quota_limit fixture already
    # uses for exactly this reason.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(jobs, "_jobs", {})
    monkeypatch.setattr(quota, "_memory_counts", defaultdict(int))
    monkeypatch.setattr(main, "DAILY_LIMIT", 0)
    monkeypatch.setattr(main, "MONTHLY_LIMIT", 0)


@pytest.fixture
def client():
    return TestClient(main.app)


def _poll_until_settled(client: TestClient, job_id: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/adapt/jobs/{job_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.01)
    raise AssertionError(f"job {job_id} never settled within {timeout}s")


def test_adapt_start_returns_cached_result_without_creating_a_job(client, monkeypatch):
    canned = {"sections": []}
    monkeypatch.setattr(main.cache, "get", lambda result_id: canned)

    response = client.post("/api/adapt/start", json=VALID_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "done", "job_id": None, "result": canned}
    assert jobs._jobs == {}


def test_adapt_start_returns_fuzzy_match_without_creating_a_job(client, monkeypatch):
    canned = {"sections": ["matched"]}
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)
    monkeypatch.setattr(
        main.cache, "find_similar", lambda *a, **k: ("other-id", canned, 0.97)
    )
    monkeypatch.setattr(main.cache, "set", lambda *a, **k: None)

    response = client.post("/api/adapt/start", json=VALID_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "done", "job_id": None, "result": canned}
    assert jobs._jobs == {}


def test_adapt_start_runs_engine_in_background_and_job_completes(client, monkeypatch):
    canned = {"sections": ["a full result"]}
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)
    monkeypatch.setattr(main.cache, "find_similar", lambda *a, **k: None)
    monkeypatch.setattr(main, "_run_adaptation", lambda *a, **k: canned)

    response = client.post("/api/adapt/start", json=VALID_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["job_id"]
    assert body["result"] is None

    settled = _poll_until_settled(client, body["job_id"])
    assert settled == {"status": "done", "result": canned, "error": None, "progress": None}


def test_job_reports_llm_error_as_a_friendly_message(client, monkeypatch):
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)
    monkeypatch.setattr(main.cache, "find_similar", lambda *a, **k: None)

    def _raise(*a, **k):
        raise LLMError("upstream exploded")

    monkeypatch.setattr(main, "_run_adaptation", _raise)

    response = client.post("/api/adapt/start", json=VALID_BODY)
    job_id = response.json()["job_id"]

    settled = _poll_until_settled(client, job_id)
    assert settled["status"] == "error"
    assert "Try again" in settled["error"]
    # The raw exception text never reaches the client - same discipline
    # as /api/adapt's own except LLMError branch.
    assert "upstream exploded" not in settled["error"]


def test_job_reports_runtime_error_verbatim(client, monkeypatch):
    """RuntimeError is a configuration failure (e.g. a missing API key) -
    /api/adapt surfaces its message directly rather than a generic one,
    and the job path preserves that."""
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)
    monkeypatch.setattr(main.cache, "find_similar", lambda *a, **k: None)

    def _raise(*a, **k):
        raise RuntimeError("OPENAI_API_KEY not set")

    monkeypatch.setattr(main, "_run_adaptation", _raise)

    response = client.post("/api/adapt/start", json=VALID_BODY)
    job_id = response.json()["job_id"]

    settled = _poll_until_settled(client, job_id)
    assert settled == {
        "status": "error",
        "result": None,
        "error": "OPENAI_API_KEY not set",
        "progress": None,
    }


def test_job_reports_unexpected_exception_without_hanging_forever(client, monkeypatch):
    """A background thread's uncaught exception is otherwise invisible to
    whoever's polling - this is the catch-all that turns it into an
    "error" status instead of a job stuck on "pending"/"running" forever."""
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)
    monkeypatch.setattr(main.cache, "find_similar", lambda *a, **k: None)

    def _raise(*a, **k):
        raise ValueError("something nobody anticipated")

    monkeypatch.setattr(main, "_run_adaptation", _raise)

    response = client.post("/api/adapt/start", json=VALID_BODY)
    job_id = response.json()["job_id"]

    settled = _poll_until_settled(client, job_id)
    assert settled["status"] == "error"
    assert settled["error"]


def test_unknown_job_id_is_a_404(client):
    response = client.get("/api/adapt/jobs/does-not-exist")
    assert response.status_code == 404


def test_adapt_start_validates_input_same_as_adapt(client):
    response = client.post("/api/adapt/start", json={"text": "   "})
    assert response.status_code == 400


def test_adapt_start_respects_the_quota(client, monkeypatch):
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)
    monkeypatch.setattr(main.cache, "find_similar", lambda *a, **k: None)
    monkeypatch.setattr(main, "DAILY_LIMIT", 1)
    monkeypatch.setattr(main, "_run_adaptation", lambda *a, **k: {"sections": []})

    first = client.post("/api/adapt/start", json=VALID_BODY)
    assert first.status_code == 200

    second = client.post(
        "/api/adapt/start", json={"text": "different lyrics entirely"}
    )
    assert second.status_code == 429
