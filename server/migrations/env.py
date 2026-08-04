"""Alembic environment for server/db_models.py.

Reuses server/db.py for both the metadata and the engine, so there is
exactly one definition of "the schema" (Base.metadata) and one place
that knows how to parse DATABASE_URL (including the postgres:// scheme
rewrite Railway requires).
"""
from __future__ import annotations

import sys
from pathlib import Path

from alembic import context

# Running `alembic -c server/alembic.ini ...` from the repo root already
# has the root on sys.path; running from anywhere else (or from inside
# server/) may not. Adding it explicitly costs nothing when redundant.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server import db_models  # noqa: F401 — registers every model on Base.metadata
from server.db import Base, _database_url, get_engine

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """--sql mode: emit the migration as SQL without a live connection."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = get_engine()
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
