"""Entry point for the worker service - a separate Railway service from
the web one (server/main.py's uvicorn process), running:

    python -m server.worker

Pulls jobs off the queue server/task_queue.py's adapt_start()/
comics_adapt_start() enqueue onto (server.main._run_job/_run_comics_job)
and runs them - the same functions the in-process threading fallback
already calls when REDIS_URL isn't set, just invoked here by an RQ
worker process instead of a background thread inside the web process.

Needs the exact same environment the web service does - OPENAI_API_KEY,
ANTHROPIC_API_KEY, DATABASE_URL, REDIS_URL, GOOGLE_CLOUD_VISION_API_KEY
(or the credentials-JSON variant), CASTIA_INTERNAL_API_SECRET - since it
imports server.main to get at _run_job/_run_comics_job and runs the
exact same engine code path. Scale by running more than one Railway
replica of this service; each replica is an independent RQ worker
process pulling from the same shared queue, no coordination needed
beyond both pointing at the same REDIS_URL.

REDIS_URL must be set for this to mean anything - if it isn't, nothing
is ever enqueued onto this queue in the first place (server/task_queue.py's
use_queue() gates that on the web service's side), so a worker started
without it would just sit connected to nothing, forever idle. Fails
loudly on startup instead, since a silently-idle worker service looks
identical to "everything's fine" from the outside.
"""
from __future__ import annotations

import os
import sys


def main() -> None:
    if not os.environ.get("REDIS_URL"):
        print(
            "REDIS_URL is not set - this worker has nothing to connect to. "
            "Set REDIS_URL (same value as the web service) before starting it.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    # Imported here, not at module level - importing server.main (which
    # imports the full engine/ tree) before confirming REDIS_URL is set
    # would make the startup-failure message above take several seconds
    # to appear instead of being immediate.
    from rq import Worker

    from . import task_queue

    # server.main is never referenced by name below, but importing it
    # here is required: RQ resolves an enqueued job's function by dotted
    # path ("server.main._run_job") at run time, in whichever process
    # picks the job up - if this process never imported server.main
    # itself, that lookup fails the first time a job actually arrives.
    from . import main  # noqa: F401

    worker = Worker([task_queue.get_queue()], connection=task_queue._connection())
    worker.work()


if __name__ == "__main__":
    main()
