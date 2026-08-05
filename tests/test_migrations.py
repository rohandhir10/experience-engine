"""migrate_to_head() must succeed from BOTH starting points it claims to
support (0001_baseline.py's own docstring): a genuinely fresh database,
and one that already has the pre-migration-system schema deployed.
Neither was actually exercised before this test existed - a real bug
(0002 crashing with "duplicate column: medium" on a fresh database) was
only caught by actually running the migration, not by assuming the
baseline's checkfirst=True made every later migration automatically
safe. See 0002_add_adaptation_medium.py and 0003_add_api_keys.py's
updated docstrings for why each needs its own existence guard.
"""
from __future__ import annotations

import sqlite3

import server.db as db


def test_migrate_to_head_succeeds_on_a_fresh_database(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)

    db.migrate_to_head()  # must not raise

    from sqlalchemy import inspect

    insp = inspect(db.get_engine())
    tables = set(insp.get_table_names())
    assert {"adaptations", "api_keys", "api_key_usage", "monthly_quota_usage"} <= tables
    assert "medium" in {c["name"] for c in insp.get_columns("adaptations")}


def test_migrate_to_head_succeeds_on_a_preexisting_pre_migration_database(tmp_path, monkeypatch):
    """Simulates Railway's real deployed database: tables created via the
    old create_all() path before this migration system existed, and
    genuinely missing the medium column / api_keys tables - the actual
    scenario 0002/0003 are supposed to upgrade, as opposed to a fresh
    database where the baseline's checkfirst=True already includes them.
    """
    db_path = tmp_path / "existing.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT, google_sub TEXT, "
        "display_name TEXT, plan TEXT, created_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE adaptations (id TEXT PRIMARY KEY, user_id TEXT, result_id TEXT, "
        "source_language TEXT, song_key TEXT, version INTEGER, verified BOOLEAN, "
        "is_favorite BOOLEAN, created_at TEXT)"
    )
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    conn.execute("INSERT INTO alembic_version VALUES ('0001_baseline')")
    conn.commit()
    conn.close()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)

    db.migrate_to_head()  # must not raise

    from sqlalchemy import inspect

    insp = inspect(db.get_engine())
    assert "medium" in {c["name"] for c in insp.get_columns("adaptations")}
    assert "api_keys" in insp.get_table_names()
    # 0004 runs in this same chain (the DB is stuck before 0002/0003/0004
    # all ran) - the real scenario it targets, distinct from the fresh-
    # database case above where baseline's create_all already includes it.
    assert "monthly_quota_usage" in insp.get_table_names()
    assert {c["name"] for c in insp.get_columns("monthly_quota_usage")} == {
        "month",
        "ip",
        "count",
    }
