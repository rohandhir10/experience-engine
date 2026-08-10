"""Real distributed job queue (RQ, Redis-backed) - gated on REDIS_URL,
same convention as DATABASE_URL gating Postgres throughout server/*.py.

When REDIS_URL is unset (local dev, the test suite), server/main.py's
adapt_start()/comics_adapt_start() fall back to the original in-process
threading.Thread + _run_slots semaphore path unchanged - this module is
never imported into that path at all, so neither redis nor rq needs to
be running for local dev or tests.

When REDIS_URL IS set, adapt_start()/comics_adapt_start() enqueue
server.main._run_job/_run_comics_job onto this queue instead of spawning
a thread - the exact same functions, same arguments, same jobs.py status
writes, just invoked by a separate worker process (server/worker.py,
run as its own Railway service: `python -m server.worker`) instead of a
background thread inside the web process. This is what actually removes
the single-container concurrency ceiling MAX_CONCURRENT_RUNS was always
a "starting guess" for (server/main.py's own comment on it): concurrency
becomes however many worker processes/replicas Railway runs, not a fixed
in-process semaphore, and a worker container crashing or redeploying
only drops whatever that one container was running, not every job in
the whole service the way an in-process thread leak could.

`job_timeout` on enqueue() is RQ's own hard ceiling on a job, enforced
by the worker at the OS level (it can actually kill a job process that
overruns it) - a more robust version of the same problem
SLOT_ACQUIRE_TIMEOUT_SECONDS works around for the threading fallback:
a job that's truly stuck can't hold a worker slot forever.
"""
from __future__ import annotations

import os

QUEUE_NAME = "castia"

_redis_conn = None
_queue = None


def use_queue() -> bool:
    return bool(os.environ.get("REDIS_URL"))


def _connection():
    global _redis_conn
    if _redis_conn is None:
        import redis

        _redis_conn = redis.from_url(os.environ["REDIS_URL"])
    return _redis_conn


def get_queue():
    """Lazy singleton, same pattern as server/db.py's get_engine() -
    constructed on first real use, not at import time, so importing this
    module never requires REDIS_URL to already be set."""
    global _queue
    if _queue is None:
        from rq import Queue

        _queue = Queue(QUEUE_NAME, connection=_connection())
    return _queue
