"""server/worker.py's entry point - just the fail-fast guard (a worker
started without REDIS_URL would otherwise sit connected to nothing,
looking identical to "everything's fine" from the outside). The actual
worker.work() loop is a real blocking RQ event loop, not something a
unit test runs - tests/test_task_queue.py already exercises the real
enqueue -> _run_job/_run_comics_job -> jobs.py chain this worker would
run, via a synchronous (is_async=False) queue instead of a live worker
process.
"""
from __future__ import annotations

import pytest

from server import worker


def test_main_exits_immediately_without_redis_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        worker.main()
    assert exc_info.value.code == 1
