"""Status storage for /api/adapt/start's background engine runs.

Three backends, in priority order:

- REDIS_URL set -> Redis (a JSON blob per job, native TTL via `EX`).
  This is the real fix for polling at any real scale: a status poll
  becomes a single Redis GET instead of a Postgres row read, off the
  SQLAlchemy connection pool entirely (server/db.py's pool_size=10 +
  max_overflow=10 was never going to keep up with hundreds of pollers/
  second hitting Postgres directly). Also what server/task_queue.py's
  RQ workers write to - a poll landing on the FastAPI process and a
  worker updating status from a totally different process/container
  both just talk to the same Redis instance, no coordination needed.
- Else DATABASE_URL set -> Postgres (server/db_models.py::AdaptationJob).
  Kept as the pre-Redis behavior for a deployment that has Postgres but
  not yet Redis configured - still correct, just the thing REDIS_URL
  exists to move off of under real concurrent polling.
- Else -> an in-memory dict, since there's exactly one process (local
  dev, the test suite) and nothing to share state with.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Literal

Status = Literal["pending", "running", "done", "error"]

# Bounds memory/row growth from jobs nobody ever polls again. Redis uses
# this as a native key TTL (refreshed on every write); the Postgres and
# in-memory backends prune opportunistically on each new job's creation,
# the same tradeoff the original in-memory-only version made.
_JOB_TTL_SECONDS = 3600

_redis_client = None


def _use_redis() -> bool:
    return bool(os.environ.get("REDIS_URL"))


def _redis():
    global _redis_client
    if _redis_client is None:
        import redis

        _redis_client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    return _redis_client


def _redis_key(job_id: str) -> str:
    return f"castia:job:{job_id}"


@dataclass
class _MemoryJob:
    status: Status = "pending"
    result: dict | None = None
    error: str | None = None
    # See set_progress's docstring - only ever meaningful while
    # status="running", and only for a caller that actually reports it
    # (comics chapter jobs; a song job never calls set_progress).
    progress: dict | None = None
    created_at: float = field(default_factory=time.monotonic)


_jobs: dict[str, _MemoryJob] = {}
_jobs_lock = threading.Lock()


def _use_db() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def create(job_id: str) -> None:
    if _use_redis():
        payload = {"status": "pending", "result": None, "error": None, "progress": None}
        _redis().set(_redis_key(job_id), json.dumps(payload), ex=_JOB_TTL_SECONDS)
        return

    if _use_db():
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import delete

        from . import db
        from .db_models import AdaptationJob

        with db.session_scope() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=_JOB_TTL_SECONDS)
            session.execute(delete(AdaptationJob).where(AdaptationJob.created_at < cutoff))
            session.add(AdaptationJob(id=job_id))
            session.commit()
        return

    with _jobs_lock:
        cutoff = time.monotonic() - _JOB_TTL_SECONDS
        for stale_id in [jid for jid, job in _jobs.items() if job.created_at < cutoff]:
            del _jobs[stale_id]
        _jobs[job_id] = _MemoryJob()


def set_running(job_id: str) -> None:
    _update(job_id, status="running")


def set_progress(job_id: str, progress: dict) -> None:
    """Overwrites the job's in-flight progress snapshot wholesale (never
    merged - see AdaptationJob.progress_json's docstring). Does NOT touch
    status; the caller is expected to have already called set_running.
    Safe to call often - each call is one row update (or one dict
    write), not a growing log."""
    _update(job_id, status="running", progress=progress)


def set_done(job_id: str, result: dict) -> None:
    _update(job_id, status="done", result=result)


def set_error(job_id: str, error: str) -> None:
    _update(job_id, status="error", error=error)


def _update(
    job_id: str,
    *,
    status: Status,
    result: dict | None = None,
    error: str | None = None,
    progress: dict | None = None,
) -> None:
    if _use_redis():
        client = _redis()
        key = _redis_key(job_id)
        raw = client.get(key)
        if raw is None:
            return
        data = json.loads(raw)
        data["status"] = status
        if result is not None:
            data["result"] = result
        if error is not None:
            data["error"] = error
        if progress is not None:
            data["progress"] = progress
        # Refresh the TTL on every write, not just create() - a job still
        # actively running shouldn't expire out from under a slow chapter
        # just because its key is over an hour old.
        client.set(key, json.dumps(data), ex=_JOB_TTL_SECONDS)
        return

    if _use_db():
        from . import db
        from .db_models import AdaptationJob

        with db.session_scope() as session:
            row = session.get(AdaptationJob, job_id)
            if row is None:
                return
            row.status = status
            if result is not None:
                row.result_json = result
            if error is not None:
                row.error = error
            if progress is not None:
                row.progress_json = progress
            session.commit()
        return

    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.status = status
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        if progress is not None:
            job.progress = progress


def get(job_id: str) -> dict | None:
    """Returns {"status", "result", "error", "progress"}, or None if the
    job is unknown (never created, or pruned past its TTL). `progress` is
    None until (and unless) a caller reports one via set_progress."""
    if _use_redis():
        raw = _redis().get(_redis_key(job_id))
        if raw is None:
            return None
        return json.loads(raw)

    if _use_db():
        from . import db
        from .db_models import AdaptationJob

        with db.session_scope() as session:
            row = session.get(AdaptationJob, job_id)
            if row is None:
                return None
            return {
                "status": row.status,
                "result": row.result_json,
                "error": row.error,
                "progress": row.progress_json,
            }

    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return {
            "status": job.status,
            "result": job.result,
            "error": job.error,
            "progress": job.progress,
        }
