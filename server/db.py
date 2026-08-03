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

from sqlalchemy import create_engine
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


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_database_url(), pool_pre_ping=True)
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

    with get_engine().begin() as conn:
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
