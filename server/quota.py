"""Per-(period, ip) submission caps backing CASTIA_DAILY_LIMIT and
CASTIA_MONTHLY_LIMIT.

The daily cap alone was never a real cost ceiling: it resets every day,
forever, with nothing bounding the total across a month. A free IP
hitting the daily cap every day has no ceiling on cumulative spend at
all - found to matter in practice, not hypothetically, once real per-
request cost was worked out (docs/CAPABILITY_MATRIX.md). The monthly cap
here is the actual ceiling; the daily one is just an anti-burst limit on
top of it.

Same backend split as server/jobs.py/cache.py for both: DATABASE_URL set
-> Postgres (server/db_models.py::DailyQuotaUsage/MonthlyQuotaUsage) via
an atomic INSERT ... ON CONFLICT DO UPDATE, so a burst of requests split
across more than one process/instance can't each independently believe
they're the first request of the period for that IP - a plain
SELECT-then-UPDATE can't give that guarantee under real concurrency. Not
set (local dev, the test suite) -> an in-memory dict, single process
only, exactly like before this module existed.
"""
from __future__ import annotations

import os
import threading
from collections import defaultdict
from datetime import date

_memory_counts: dict[tuple[str, str], int] = defaultdict(int)
_memory_monthly_counts: dict[tuple[str, str], int] = defaultdict(int)
_memory_lock = threading.Lock()


def _use_db() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def _check_and_increment(
    ip: str,
    limit: int,
    period_value: str,
    memory_counts: dict[tuple[str, str], int],
    model_name: str,
    period_column: str,
) -> bool:
    """Shared implementation for the daily and monthly caps - identical
    shape (period_value, ip, count) either way, differing only in which
    table/column holds the period. `model_name` is looked up on
    server.db_models lazily (not imported at module level) so this module
    stays importable without SQLAlchemy installed when DATABASE_URL isn't
    set, matching the rest of this file's local-dev/test convenience.
    """
    if limit <= 0:
        return True

    if _use_db():
        from sqlalchemy.dialects.postgresql import insert

        from . import db, db_models

        model = getattr(db_models, model_name)
        count_col = model.count

        with db.session_scope() as session:
            # Increment-then-check, not check-then-increment: the atomic
            # UPSERT is what makes this race-free across concurrent
            # requests/processes. A blocked request still bumps the
            # stored count past the limit on repeat attempts, which is
            # harmless (it's an internal counter, never shown to users)
            # and doesn't change the 429 decision either way.
            stmt = (
                insert(model)
                .values(**{period_column: period_value, "ip": ip, "count": 1})
                .on_conflict_do_update(
                    index_elements=[period_column, "ip"],
                    set_={"count": count_col + 1},
                )
                .returning(count_col)
            )
            new_count = session.execute(stmt).scalar_one()
            session.commit()
        return new_count <= limit

    with _memory_lock:
        key = (period_value, ip)
        if memory_counts[key] >= limit:
            return False
        memory_counts[key] += 1
        return True


def _bucket_key(ip: str, scope: str) -> str:
    """The stored key for one caller's counter within one scope.

    Different kinds of work need independently-sized ceilings against the
    same caller: one chapter adaptation is a handful of expensive
    Writers' Room runs, while OCR-ing that same chapter is dozens of
    cheap per-panel Vision calls. Counting both into one bucket would
    mean either the adaptation cap is uselessly high or normal per-panel
    work trips it immediately.

    Namespacing the key rather than adding a `scope` column keeps the
    existing atomic-UPSERT exactly as-is on both backends and needs no
    migration. An empty scope produces the bare ip, byte-identical to
    what this module stored before scopes existed - so pre-existing rows
    and the default (adaptation) callers are completely unaffected.
    """
    return f"{scope}:{ip}" if scope else ip


def check_and_increment(ip: str, daily_limit: int, scope: str = "") -> bool:
    """Returns True if this request is allowed (and counts it against
    today's total for this ip), False if ip has already reached
    daily_limit today. daily_limit <= 0 disables the quota entirely,
    without touching either backend — matches the pre-existing
    CASTIA_DAILY_LIMIT=0 convention. An anti-burst limit only - see
    check_and_increment_monthly for the actual cost ceiling.

    `scope` selects an independent counter for this ip - see _bucket_key.
    """
    today = date.today().isoformat()
    return _check_and_increment(
        _bucket_key(ip, scope), daily_limit, today, _memory_counts, "DailyQuotaUsage", "day"
    )


def check_and_increment_monthly(ip: str, monthly_limit: int, scope: str = "") -> bool:
    """Same as check_and_increment, keyed by calendar month instead of
    day - this is the real ceiling on cumulative free-tier spend per IP.
    monthly_limit <= 0 disables it, same convention as the daily cap.
    """
    this_month = date.today().strftime("%Y-%m")
    return _check_and_increment(
        _bucket_key(ip, scope), monthly_limit, this_month, _memory_monthly_counts,
        "MonthlyQuotaUsage", "month",
    )
