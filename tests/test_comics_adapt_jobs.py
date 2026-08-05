"""Tests for the async comics job endpoints (/api/comics/adapt/start,
/api/comics/adapt/jobs/{id}) - the same fix /api/adapt/start already
applies for songs (tests/test_server_jobs.py), now extended to comics so
a many-panel chapter can run past MAX_COMICS_PANELS's old timeout-driven
ceiling without hitting a request timeout.

Mocks server.main._run_comics_adaptation entirely (no real LLM calls, no
real engine run) - this verifies the job lifecycle, threading, routing,
and error propagation this endpoint adds, not adaptation quality, which
tests/test_server.py's comics_adapt_endpoint tests and engine-level tests
already cover.
"""
from __future__ import annotations

import time
from collections import defaultdict

import pytest
from fastapi.testclient import TestClient

import server.main as main
from engine.llm_client import LLMError
from server import jobs, quota

VALID_BODY = {
    "source_language": "Korean",
    "target_language": "English",
    "panels": [{"id": "p1", "text": "hello there"}, {"id": "p2", "text": "general kenobi"}],
}


@pytest.fixture(autouse=True)
def _reset_module_state(monkeypatch):
    # See tests/test_server_jobs.py's identical fixture for why
    # MONTHLY_LIMIT is zeroed too, not just _memory_counts reset - the
    # real cost-ceiling counter (quota._memory_monthly_counts) is a
    # module-level global shared across every test file in the session,
    # never reset by any per-test dict swap.
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
        response = client.get(f"/api/comics/adapt/jobs/{job_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.01)
    raise AssertionError(f"job {job_id} never settled within {timeout}s")


def test_comics_adapt_start_returns_cached_result_without_creating_a_job(client, monkeypatch):
    canned = {"chapter_dna": {}, "panels": []}
    monkeypatch.setattr(main.cache, "get", lambda result_id: canned)

    response = client.post("/api/comics/adapt/start", json=VALID_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["job_id"] is None
    assert body["result"]["id"]
    assert body["result"]["chapter_dna"] == {}
    assert jobs._jobs == {}


def test_comics_adapt_start_runs_engine_in_background_and_job_completes(client, monkeypatch):
    canned = {"chapter_dna": {"artistic_thesis": "x"}, "panels": [{"id": "p1"}]}
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)
    monkeypatch.setattr(main, "_run_comics_adaptation", lambda *a, **k: canned)

    response = client.post("/api/comics/adapt/start", json=VALID_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["job_id"]
    assert body["result"] is None

    settled = _poll_until_settled(client, body["job_id"])
    assert settled["status"] == "done"
    assert settled["result"]["chapter_dna"] == {"artistic_thesis": "x"}
    assert settled["result"]["panels"] == [{"id": "p1"}]
    assert settled["result"]["id"]


def test_comics_job_reports_llm_error_as_a_friendly_message(client, monkeypatch):
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)

    def _raise(*a, **k):
        raise LLMError("upstream exploded")

    monkeypatch.setattr(main, "_run_comics_adaptation", _raise)

    response = client.post("/api/comics/adapt/start", json=VALID_BODY)
    job_id = response.json()["job_id"]

    settled = _poll_until_settled(client, job_id)
    assert settled["status"] == "error"
    assert "Try again" in settled["error"]
    assert "upstream exploded" not in settled["error"]


def test_comics_job_reports_runtime_error_verbatim(client, monkeypatch):
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)

    def _raise(*a, **k):
        raise RuntimeError("OPENAI_API_KEY not set")

    monkeypatch.setattr(main, "_run_comics_adaptation", _raise)

    response = client.post("/api/comics/adapt/start", json=VALID_BODY)
    job_id = response.json()["job_id"]

    settled = _poll_until_settled(client, job_id)
    assert settled == {"status": "error", "result": None, "error": "OPENAI_API_KEY not set"}


def test_unknown_comics_job_id_is_a_404(client):
    response = client.get("/api/comics/adapt/jobs/does-not-exist")
    assert response.status_code == 404


def test_comics_adapt_start_rejects_all_empty_panels(client):
    response = client.post(
        "/api/comics/adapt/start",
        json={"source_language": "Korean", "target_language": "English", "panels": [{"id": "p1", "text": "   "}]},
    )
    assert response.status_code == 400


def test_comics_adapt_start_rejects_a_chapter_over_the_panel_cap(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_COMICS_PANELS", 1)
    response = client.post("/api/comics/adapt/start", json=VALID_BODY)
    assert response.status_code == 413


def test_comics_adapt_start_respects_the_quota(client, monkeypatch):
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)
    monkeypatch.setattr(main, "DAILY_LIMIT", 1)
    monkeypatch.setattr(main, "_run_comics_adaptation", lambda *a, **k: {"chapter_dna": {}, "panels": []})

    first = client.post("/api/comics/adapt/start", json=VALID_BODY)
    assert first.status_code == 200

    second = client.post(
        "/api/comics/adapt/start",
        json={**VALID_BODY, "panels": [{"id": "p3", "text": "a different chapter entirely"}]},
    )
    assert second.status_code == 429


def test_comics_adapt_start_deducts_and_refunds_credits_for_a_signed_in_user(client, monkeypatch):
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)
    deducted = {}
    refunded = {}
    monkeypatch.setattr(
        main.credits, "deduct", lambda user_id, amount, reason, reference: deducted.update(amount=amount) or True
    )
    monkeypatch.setattr(
        main.credits, "refund", lambda user_id, amount, reference: refunded.update(amount=amount)
    )
    monkeypatch.setattr(main, "_authed_user_id", lambda request: "user-1")

    def _raise(*a, **k):
        raise LLMError("boom")

    monkeypatch.setattr(main, "_run_comics_adaptation", _raise)

    response = client.post("/api/comics/adapt/start", json=VALID_BODY)
    job_id = response.json()["job_id"]
    _poll_until_settled(client, job_id)

    assert deducted["amount"] == main.CREDITS_PER_PANEL * 2
    assert refunded["amount"] == main.CREDITS_PER_PANEL * 2
