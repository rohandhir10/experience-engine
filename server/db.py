"""Postgres wiring for server/db_models.py.

DATABASE_URL is read from the environment — on Railway, that's the
Postgres plugin's connection string, referenced as an env var on this
service (Railway doesn't attach a plugin to a service automatically).

No auth provider is chosen yet (Clerk vs. NextAuth/Auth.js are both still
open), so this deliberately does not include a sessions/tokens table —
Clerk hosts identity itself and needs none, while NextAuth's Postgres
adapter expects its own exact table shapes. Building a custom sessions
table now would very likely be replaced wholesale by whichever is picked,
so the users table is the only thing that's genuinely provider-agnostic
today. Revisit once that decision is made.

Tables are created with `Base.metadata.create_all()` at startup rather
than via Alembic migrations — there's no real data yet, so a schema
change costs nothing right now. Introduce a real migration tool before
this stops being true (i.e. before any production row exists that a
raw `create_all` diff could silently fail to alter).
"""
from __future__ import annotations

import os
import zlib
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. On Railway, add a variable on this "
            "service referencing the Postgres plugin's connection string."
        )
    # Railway (and Heroku-style platforms) commonly hand out
    # postgres://... — SQLAlchemy's psycopg3 dialect requires the
    # postgresql+psycopg:// form.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


_engine = None
_SessionLocal: sessionmaker | None = None



# Explicit rather than SQLAlchemy's bare defaults (pool_size=5,
# max_overflow=10) so the actual ceiling is visible and tunable here
# instead of implied. Headroom for /api/adapt/start's background job
# threads (server/main.py's MAX_CONCURRENT_RUNS) each holding a
# connection concurrently, plus normal request traffic — not a measured
# number, a documented starting point.
#
# This is PER PROCESS, and the Dockerfile now runs CASTIA_WEB_CONCURRENCY
# (default 2) independent worker processes, each with its own engine and
# therefore its own pool — real total connections from this one service
# are CASTIA_WEB_CONCURRENCY × (POOL_SIZE + MAX_OVERFLOW), not just this
# number on its own. Also bounded by whatever Railway's managed Postgres
# plan actually allows (commonly ~20-100 connections on hobby/starter
# tiers): raising POOL_SIZE, MAX_OVERFLOW, or CASTIA_WEB_CONCURRENCY past
# that combined ceiling just moves the failure from "pool exhausted" to
# "Postgres refused the connection," so check the plan's actual limit —
# and multiply it out against the worker count — before tuning any of
# the three up for real concurrent traffic.
POOL_SIZE = int(os.environ.get("CASTIA_DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.environ.get("CASTIA_DB_MAX_OVERFLOW", "10"))


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            _database_url(),
            pool_pre_ping=True,
            pool_size=POOL_SIZE,
            max_overflow=MAX_OVERFLOW,
        )
    return _engine


def get_sessionmaker() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def create_all() -> None:
    from . import db_models  # noqa: F401 - registers models on Base.metadata
    Base.metadata.create_all(bind=get_engine())
    _patch_known_schema_drift()


# Arbitrary, fixed advisory-lock key for migrate_to_head() below -
# derived from a stable string via crc32 (not Python's built-in hash(),
# which is randomized per-process and would defeat the point of every
# process agreeing on the same key). The actual number doesn't matter;
# only that every process computes the same one, forever.
_MIGRATION_LOCK_KEY = zlib.crc32(b"castia:migrate_to_head")


def migrate_to_head() -> None:
    """Runs `alembic upgrade head` programmatically — the startup schema
    path, replacing the bare create_all()+hand-patch pattern this module's
    docstring (and _patch_known_schema_drift's, twice) said was overdue
    for replacement.

    The baseline revision (server/migrations/versions/0001_baseline.py)
    is checkfirst-create_all, so this is safe on both a fresh database
    and the already-deployed one — see that file's docstring. The drift
    patch still runs afterwards during the transition: it's idempotent,
    and it's what guarantees the hand-added columns exist on databases
    created before the models declared them.

    Wrapped in a Postgres session-scoped advisory lock (CASTIA_WEB_CONCURRENCY,
    see the Dockerfile) runs more than one worker PROCESS per container,
    and every worker independently calls this on its own startup. Each
    migration's own guard is a check-then-create ("does this table
    exist? if not, create it") - safe against re-running on an
    already-migrated database, but NOT safe against two processes
    checking at the same instant, both seeing "not created yet," and
    racing to CREATE the same table. Confirmed empirically (not just in
    theory) to be worse than a clean crash: with this lock removed and 5
    threads calling this function concurrently against a freshly wiped
    real Postgres database (tests/test_migrations.py's
    test_migrate_to_head_is_safe_under_concurrent_workers, which fails
    fast with this lock in place), the run didn't error out - it hung
    indefinitely, past a 120-second timeout, with zero output. A DDL
    conflict that raises is at least visible; one that leaves a
    connection idle-in-transaction holding a lock forever just makes the
    whole container look stuck on startup. The advisory lock (Postgres-
    only - sqlite has no equivalent, and nothing in this test suite
    exercises concurrent workers against sqlite anyway) makes every
    concurrent caller queue up and run this one at a time: by the time a
    waiting worker acquires the lock, the schema is already at head, so
    its own turn is a fast, correct no-op instead of a race.
    """
    from alembic import command
    from alembic.config import Config

    def _run() -> None:
        cfg = Config(str(Path(__file__).parent / "alembic.ini"))
        command.upgrade(cfg, "head")
        _patch_known_schema_drift()

    engine = get_engine()
    if engine.dialect.name != "postgresql":
        _run()
        return

    with engine.connect() as conn:
        conn.execute(text("SELECT pg_advisory_lock(:key)"), {"key": _MIGRATION_LOCK_KEY})
        try:
            _run()
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": _MIGRATION_LOCK_KEY})


def _patch_known_schema_drift() -> None:
    """`create_all()` only creates TABLES that don't exist yet - it never
    ALTERs a table that's already there, which is exactly the risk this
    module's docstring warns about. CachedResult picked up
    target_language/source_language after `cached_results` already existed
    in a deployed database (server/cache.py's language-scoped fuzzy-match
    work), so those columns were silently missing in production until a
    real request hit `column cached_results.target_language does not
    exist`.

    This is a one-off, targeted backfill, not a migration framework - IF
    NOT EXISTS makes it idempotent (safe to run on every startup, forever,
    with no effect once every environment has the columns).

    This docstring originally said "introduce Alembic before this needs
    to happen a second time." It happened a second time (cache_version,
    below, for server/cache.py's cache-invalidation fix) before that
    happened. Noted honestly rather than quietly deleting the claim -
    patching individual columns by hand is proving it does NOT scale
    past one, and Alembic is overdue, not just "worth considering."
    """
    from sqlalchemy import text

    engine = get_engine()
    if engine.dialect.name != "postgresql":
        # ADD COLUMN IF NOT EXISTS is Postgres syntax; on sqlite (local
        # smoke tests against a file DB) the models already carry these
        # columns and there's no pre-existing deployed table to patch.
        return

    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE cached_results ADD COLUMN IF NOT EXISTS "
            "target_language VARCHAR DEFAULT 'English'"
        ))
        conn.execute(text(
            "ALTER TABLE cached_results ADD COLUMN IF NOT EXISTS "
            "source_language VARCHAR DEFAULT 'unspecified'"
        ))
        conn.execute(text(
            "UPDATE cached_results SET target_language = 'English' "
            "WHERE target_language IS NULL"
        ))
        conn.execute(text(
            "UPDATE cached_results SET source_language = 'unspecified' "
            "WHERE source_language IS NULL"
        ))
        conn.execute(text(
            "ALTER TABLE cached_results ADD COLUMN IF NOT EXISTS "
            "cache_version VARCHAR DEFAULT ''"
        ))
        # Deliberately NOT backfilled to the current CACHE_VERSION - an
        # empty string is exactly what a pre-existing row should show:
        # "computed before this concept existed," which correctly makes
        # it a version mismatch (not a false match) the next time
        # find_similar() runs.


def session_scope() -> Session:
    return get_sessionmaker()()
