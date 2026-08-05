"""Tests for server/jobs.py's in-memory backend (no DATABASE_URL set in
the test environment) - the DB-backed path is exercised by
tests/test_db_models.py's AdaptationJob schema tests and by manual
verification against a real Postgres instance, not here.
"""
from __future__ import annotations

import time

import pytest

from server import jobs


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    monkeypatch.setattr(jobs, "_jobs", {})
    monkeypatch.delenv("DATABASE_URL", raising=False)


def test_unknown_job_returns_none():
    assert jobs.get("does-not-exist") is None


def test_create_starts_pending_with_no_result_or_error():
    jobs.create("job-1")
    assert jobs.get("job-1") == {
        "status": "pending",
        "result": None,
        "error": None,
        "progress": None,
    }


def test_set_running_transitions_status():
    jobs.create("job-1")
    jobs.set_running("job-1")
    assert jobs.get("job-1")["status"] == "running"


def test_set_done_stores_the_result():
    jobs.create("job-1")
    jobs.set_running("job-1")
    jobs.set_done("job-1", {"sections": ["done"]})
    assert jobs.get("job-1") == {
        "status": "done",
        "result": {"sections": ["done"]},
        "error": None,
        "progress": None,
    }


def test_set_error_stores_the_message():
    jobs.create("job-1")
    jobs.set_error("job-1", "boom")
    assert jobs.get("job-1") == {
        "status": "error",
        "result": None,
        "error": "boom",
        "progress": None,
    }


def test_set_progress_stores_a_snapshot_while_running():
    jobs.create("job-1")
    jobs.set_progress("job-1", {"completed": 3, "total": 10, "message": "Panel 4/10: adapting…"})
    job = jobs.get("job-1")
    assert job["status"] == "running"
    assert job["progress"] == {"completed": 3, "total": 10, "message": "Panel 4/10: adapting…"}
    # result/error are untouched by a progress-only update.
    assert job["result"] is None
    assert job["error"] is None


def test_set_progress_overwrites_wholesale_not_merges():
    jobs.create("job-1")
    jobs.set_progress("job-1", {"completed": 1, "total": 10, "message": "first"})
    jobs.set_progress("job-1", {"completed": 2, "total": 10, "message": "second"})
    assert jobs.get("job-1")["progress"] == {"completed": 2, "total": 10, "message": "second"}


def test_set_progress_on_an_unknown_job_is_a_noop():
    jobs.set_progress("never-created", {"completed": 1, "total": 1, "message": "x"})
    assert jobs.get("never-created") is None


def test_updating_an_unknown_job_is_a_noop_not_a_crash():
    jobs.set_done("never-created", {"sections": []})
    assert jobs.get("never-created") is None


def test_stale_jobs_are_pruned_on_the_next_create(monkeypatch):
    monkeypatch.setattr(jobs, "_JOB_TTL_SECONDS", 0)
    jobs.create("old-job")
    time.sleep(0.01)
    jobs.create("new-job")
    assert jobs.get("old-job") is None
    assert jobs.get("new-job") is not None
