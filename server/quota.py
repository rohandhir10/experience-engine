"""Per-(day, ip) daily submission cap backing CASTIA_DAILY_LIMIT.

Same backend split as server/jobs.py/cache.py: DATABASE_URL set ->
Postgres (server/db_models.py::DailyQuotaUsage) via an atomic
INSERT ... ON CONFLICT DO UPDATE, so a burst of requests split across
more than one process/instance can't each independently believe they're
the first request of the day for that IP — a plain SELECT-then-UPDATE
can't give that guarantee under real concurrency. Not set (local dev,
the test suite) -> an in-memory dict, single process only, exactly like
before this module existed.
"""
from __future__ import annotations

import os
import threading
from collections import defaultdict
from datetime import date

_memory_counts: dict[tuple[str, str], int] = defaultdict(int)
_memory_lock = threading.Lock()


def _use_db() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def check_and_increment(ip: str, daily_limit: int) -> bool:
    """Returns True if this request is allowed (and counts it against
    today's total for this ip), False if ip has already reached
    daily_limit today. daily_limit <= 0 disables the quota entirely,
    without touching either backend — matches the pre-existing
    CASTIA_DAILY_LIMIT=0 convention.
    """
    if daily_limit <= 0:
        return True

    today = date.today().isoformat()

    if _use_db():
        from sqlalchemy.dialects.postgresql import insert

        from . import db
        from .db_models import DailyQuotaUsage

        with db.session_scope() as session:
            # Increment-then-check, not check-then-increment: the atomic
            # UPSERT is what makes this race-free across concurrent
            # requests/processes. A blocked request still bumps the
            # stored count past daily_limit on repeat attempts, which is
            # harmless (it's an internal counter, never shown to users)
            # and doesn't change the 429 decision either way.
            stmt = (
                insert(DailyQuotaUsage)
                .values(day=today, ip=ip, count=1)
                .on_conflict_do_update(
                    index_elements=["day", "ip"],
                    set_={"count": DailyQuotaUsage.count + 1},
                )
                .returning(DailyQuotaUsage.count)
            )
            new_count = session.execute(stmt).scalar_one()
            session.commit()
        return new_count <= daily_limit

    with _memory_lock:
        key = (today, ip)
        if _memory_counts[key] >= daily_limit:
            return False
        _memory_counts[key] += 1
        return True
