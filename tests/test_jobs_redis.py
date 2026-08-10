"""server/jobs.py's Redis backend (REDIS_URL set) - takes priority over
both the Postgres and in-memory backends tests/test_server_jobs.py and
tests/test_comics_adapt_jobs.py already exercise. Uses fakeredis (a real
redis-py-compatible in-memory server, not a mock of jobs.py's own code)
so this runs the actual jobs.redis()/json.dumps/loads path, not a stand-in
for it.
"""
from __future__ import annotations

import fakeredis
import pytest

from server import jobs


@pytest.fixture(autouse=True)
def _redis_backend(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://fake:6379/0")
    fake = fakeredis.FakeStrictRedis(decode_responses=True)
    monkeypatch.setattr(jobs, "_redis_client", None)
    monkeypatch.setattr(jobs, "_redis", lambda: fake)
    return fake


def test_create_then_get_returns_a_pending_job():
    jobs.create("job-1")
    assert jobs.get("job-1") == {
        "status": "pending",
        "result": None,
        "error": None,
        "progress": None,
    }


def test_unknown_job_id_returns_none():
    assert jobs.get("never-created") is None


def test_set_progress_updates_progress_without_touching_result_or_error():
    jobs.create("job-2")
    jobs.set_running("job-2")
    jobs.set_progress("job-2", {"completed": 1, "total": 3, "message": "Section 1/3: done"})

    state = jobs.get("job-2")
    assert state["status"] == "running"
    assert state["progress"] == {"completed": 1, "total": 3, "message": "Section 1/3: done"}
    assert state["result"] is None
    assert state["error"] is None


def test_set_done_stores_the_result():
    jobs.create("job-3")
    jobs.set_done("job-3", {"hook": "test"})

    assert jobs.get("job-3") == {
        "status": "done",
        "result": {"hook": "test"},
        "error": None,
        "progress": None,
    }


def test_set_error_stores_the_error():
    jobs.create("job-4")
    jobs.set_error("job-4", "The engine hit a problem. Try again in a moment.")

    state = jobs.get("job-4")
    assert state["status"] == "error"
    assert state["error"] == "The engine hit a problem. Try again in a moment."


def test_update_on_an_unknown_job_id_is_a_silent_no_op():
    """Same contract as the Postgres/in-memory backends - a poll or write
    against an id that was never created (or already expired) doesn't
    raise, it just has nothing to do."""
    jobs.set_done("ghost-job", {"hook": "test"})
    assert jobs.get("ghost-job") is None


def test_create_sets_a_ttl_on_the_key(_redis_backend):
    jobs.create("job-5")
    ttl = _redis_backend.ttl(jobs._redis_key("job-5"))
    assert 0 < ttl <= jobs._JOB_TTL_SECONDS


def test_writes_refresh_the_ttl(_redis_backend):
    """A job still running shouldn't expire out from under a slow
    chapter just because its key is over an hour old - every write
    resets the clock, not just create()."""
    jobs.create("job-6")
    key = jobs._redis_key("job-6")
    _redis_backend.expire(key, 5)  # simulate time having passed
    assert _redis_backend.ttl(key) <= 5

    jobs.set_progress("job-6", {"completed": 1, "total": 2, "message": "..."})
    assert _redis_backend.ttl(key) > 5


def test_redis_takes_priority_over_database_url(monkeypatch, _redis_backend):
    """REDIS_URL set alongside DATABASE_URL must still use Redis - that's
    the whole point of Redis being the preferred backend, not an
    alternative one. A DB call here would fail loudly (no real Postgres/
    sqlite wired up in this test), which is exactly the signal that
    _use_db()'s branch was wrongly reached."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://this-must-never-be-used")

    jobs.create("job-7")
    assert jobs.get("job-7")["status"] == "pending"
