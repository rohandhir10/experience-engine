"""server/task_queue.py - the REDIS_URL-gated RQ path server/main.py's
adapt_start()/comics_adapt_start() enqueue onto instead of spawning a
background thread. Runs RQ with `is_async=False` against a fakeredis
connection, so `queue.enqueue(...)` executes the job inline, in-process,
synchronously - no real Redis server or separate worker process needed
to verify the actual enqueue -> _run_job/_run_comics_job -> jobs.py
status chain end to end.
"""
from __future__ import annotations

import time
from collections import defaultdict

import fakeredis
import pytest
from fastapi.testclient import TestClient
from rq import Queue

import server.main as main
from server import jobs, quota, task_queue

SONG_BODY = {"text": "line one\n\nline two", "target_language": "English"}
COMICS_BODY = {
    "source_language": "Korean",
    "target_language": "English",
    "panels": [{"id": "p1", "text": "hello there"}],
}


@pytest.fixture(autouse=True)
def _reset_module_state(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(jobs, "_jobs", {})
    monkeypatch.setattr(quota, "_memory_counts", defaultdict(int))
    monkeypatch.setattr(main, "DAILY_LIMIT", 0)
    monkeypatch.setattr(main, "MONTHLY_LIMIT", 0)


@pytest.fixture
def fake_queue(monkeypatch):
    """Wires both jobs.py's Redis status backend and task_queue.py's RQ
    queue onto the SAME fakeredis instance with a synchronous
    (is_async=False) Queue - enqueue() runs the job immediately, inline,
    rather than needing a real separate worker process for this test."""
    monkeypatch.setenv("REDIS_URL", "redis://fake:6379/0")
    fake = fakeredis.FakeStrictRedis(decode_responses=True)
    monkeypatch.setattr(jobs, "_redis_client", None)
    monkeypatch.setattr(jobs, "_redis", lambda: fake)

    fake_raw = fakeredis.FakeStrictRedis()  # RQ wants raw bytes, not decode_responses=True
    queue = Queue(task_queue.QUEUE_NAME, connection=fake_raw, is_async=False)
    monkeypatch.setattr(task_queue, "_queue", queue)
    monkeypatch.setattr(task_queue, "get_queue", lambda: queue)
    return queue


@pytest.fixture
def client():
    return TestClient(main.app)


def test_use_queue_reflects_redis_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert task_queue.use_queue() is False
    monkeypatch.setenv("REDIS_URL", "redis://fake:6379/0")
    assert task_queue.use_queue() is True


def test_song_job_runs_via_the_queue_not_a_thread(client, monkeypatch, fake_queue):
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)
    monkeypatch.setattr(main.cache, "find_similar", lambda *a, **k: None)

    def fake_run_adaptation(*a, **k):
        return {"id": "x", "hook": "test", "sourceLanguage": "unspecified", "sections": [], "original": []}

    monkeypatch.setattr(main, "_run_adaptation", fake_run_adaptation)

    def _fail_if_thread_spawned(*a, **k):
        raise AssertionError("should have enqueued onto the RQ queue, not spawned a thread")

    monkeypatch.setattr(main.threading, "Thread", _fail_if_thread_spawned)

    response = client.post("/api/adapt/start", json=SONG_BODY)
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    # is_async=False already ran the job synchronously inside the POST
    # above - no polling loop needed, the result is there immediately.
    status = client.get(f"/api/adapt/jobs/{job_id}").json()
    assert status["status"] == "done"
    assert status["result"]["hook"] == "test"


def test_comics_job_runs_via_the_queue_not_a_thread(client, monkeypatch, fake_queue):
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)

    def fake_run_comics_adaptation(*a, **k):
        return {"chapter_dna": {}, "panels": [{"id": "p1", "literal": "hi", "adapted_text": "hi", "why": "n/a"}]}

    monkeypatch.setattr(main, "_run_comics_adaptation", fake_run_comics_adaptation)

    def _fail_if_thread_spawned(*a, **k):
        raise AssertionError("should have enqueued onto the RQ queue, not spawned a thread")

    monkeypatch.setattr(main.threading, "Thread", _fail_if_thread_spawned)

    response = client.post("/api/comics/adapt/start", json=COMICS_BODY)
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = client.get(f"/api/comics/adapt/jobs/{job_id}").json()
    assert status["status"] == "done"
    assert status["result"]["panels"][0]["adapted_text"] == "hi"


def test_song_job_error_propagates_through_the_queue(client, monkeypatch, fake_queue):
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)
    monkeypatch.setattr(main.cache, "find_similar", lambda *a, **k: None)

    def _raise(*a, **k):
        raise RuntimeError("OPENAI_API_KEY not set")

    monkeypatch.setattr(main, "_run_adaptation", _raise)

    response = client.post("/api/adapt/start", json=SONG_BODY)
    job_id = response.json()["job_id"]

    status = client.get(f"/api/adapt/jobs/{job_id}").json()
    assert status["status"] == "error"
    # Generic, not the raw configuration message - see
    # tests/test_server_jobs.py::test_job_reports_a_configuration_error_generically
    # for why. What matters HERE is that an error propagates through the
    # queue at all, which it still does.
    assert "OPENAI_API_KEY" not in status["error"]
    assert status["error"] == "This song couldn't be adapted right now. Try again in a moment."


def test_falls_back_to_a_thread_when_redis_url_is_unset(client, monkeypatch):
    """The default/local-dev/test path - no REDIS_URL, no fakeredis
    fixture applied - must still spawn a real background thread, not
    silently do nothing."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr(main.cache, "get", lambda result_id: None)
    monkeypatch.setattr(main.cache, "find_similar", lambda *a, **k: None)
    monkeypatch.setattr(
        main, "_run_adaptation",
        lambda *a, **k: {"id": "x", "hook": "test", "sourceLanguage": "unspecified", "sections": [], "original": []},
    )

    response = client.post("/api/adapt/start", json=SONG_BODY)
    job_id = response.json()["job_id"]

    deadline = time.monotonic() + 5.0
    status = {"status": "pending"}
    while time.monotonic() < deadline and status["status"] not in ("done", "error"):
        status = client.get(f"/api/adapt/jobs/{job_id}").json()
        time.sleep(0.01)

    assert status["status"] == "done"
