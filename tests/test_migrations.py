"""migrate_to_head() must succeed from BOTH starting points it claims to
support (0001_baseline.py's own docstring): a genuinely fresh database,
and one that already has the pre-migration-system schema deployed.
Neither was actually exercised before this test existed - a real bug
(0002 crashing with "duplicate column: medium" on a fresh database) was
only caught by actually running the migration, not by assuming the
baseline's checkfirst=True made every later migration automatically
safe. See 0002_add_adaptation_medium.py and 0003_add_api_keys.py's
updated docstrings for why each needs its own existence guard.

Every test below except test_migrate_to_head_succeeds_on_real_postgres
runs against SQLite - fast, no external service needed, and fine for
checking table/column shape. But SQLite has NO real column-length
enforcement (its "VARCHAR(32)" is a type hint, not a constraint), which
is exactly why a real bug slipped through here: Alembic's own
alembic_version.version_num column defaults to VARCHAR(32), and
0010_add_genre_calibration_samples's revision id is 34 characters -
`alembic upgrade head` against a real Postgres database (this project's
actual production database on Railway) failed hard with
StringDataRightTruncation, entirely invisible to every test in this
file that only ever ran against SQLite. Found and fixed (0010's own
upgrade() now widens the column first) by actually standing up a local
Postgres and running the real migration chain against it - the same
"don't trust a mock, run the real thing" discipline
test_migrate_to_head_succeeds_on_a_preexisting_pre_migration_database
above already established for SQLite's two starting-point scenarios.
"""
from __future__ import annotations

import os
import sqlite3

import pytest

import server.db as db

# Opt-in, not required for the suite to pass - this repo's whole testing
# discipline (see every other file here) is "no external services
# needed," and that should stay true for the default `pytest` run. Set
# CASTIA_TEST_POSTGRES_URL to a real, disposable Postgres database (e.g.
# a local `createdb castia_test`) to actually exercise this - the one
# meaningful way to catch a Postgres-only bug like the one this test
# guards against, since SQLite structurally cannot reproduce it.
_TEST_POSTGRES_URL = os.environ.get("CASTIA_TEST_POSTGRES_URL")


@pytest.mark.skipif(
    not _TEST_POSTGRES_URL,
    reason="CASTIA_TEST_POSTGRES_URL not set - this test needs a real, disposable Postgres database",
)
def test_migrate_to_head_succeeds_on_real_postgres(monkeypatch):
    """The regression test for the alembic_version.version_num overflow:
    SQLite can't reproduce it (see this module's docstring), so this is
    the only test in the suite that would have actually caught it -
    confirmed by reverting 0010's fix locally and watching this fail
    with the real StringDataRightTruncation error before re-applying it.
    """
    monkeypatch.setenv("DATABASE_URL", _TEST_POSTGRES_URL)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)

    db.migrate_to_head()  # must not raise

    from sqlalchemy import inspect

    insp = inspect(db.get_engine())
    tables = set(insp.get_table_names())
    assert {
        "adaptations", "api_keys", "api_key_usage", "monthly_quota_usage",
        "credit_transactions", "paddle_processed_events", "character_bible_entries",
        "genre_calibration_samples",
    } <= tables

    with db.get_engine().connect() as conn:
        from sqlalchemy import text

        version_column = conn.execute(
            text(
                "SELECT character_maximum_length FROM information_schema.columns "
                "WHERE table_name = 'alembic_version' AND column_name = 'version_num'"
            )
        ).scalar()
        assert version_column is not None and version_column >= 255


def test_migrate_to_head_succeeds_on_a_fresh_database(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)

    db.migrate_to_head()  # must not raise

    from sqlalchemy import inspect

    insp = inspect(db.get_engine())
    tables = set(insp.get_table_names())
    assert {
        "adaptations", "api_keys", "api_key_usage", "monthly_quota_usage",
        "credit_transactions", "paddle_processed_events", "character_bible_entries",
        "genre_calibration_samples",
    } <= tables
    assert "medium" in {c["name"] for c in insp.get_columns("adaptations")}
    assert "credits" in {c["name"] for c in insp.get_columns("users")}


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
    # 0004/0005 run in this same chain (the DB is stuck before any of
    # 0002-0005 ran) - the real scenario they target, distinct from the
    # fresh-database case above where baseline's create_all already
    # includes them.
    assert "monthly_quota_usage" in insp.get_table_names()
    assert {c["name"] for c in insp.get_columns("monthly_quota_usage")} == {
        "month",
        "ip",
        "count",
    }
    assert "credits" in {c["name"] for c in insp.get_columns("users")}
    assert "credit_transactions" in insp.get_table_names()
    assert {c["name"] for c in insp.get_columns("credit_transactions")} == {
        "id",
        "user_id",
        "amount",
        "reason",
        "reference",
        "balance_after",
        "created_at",
    }
    assert "paddle_processed_events" in insp.get_table_names()
    assert {c["name"] for c in insp.get_columns("paddle_processed_events")} == {
        "event_id",
        "created_at",
    }
    # 0009 runs in this same chain too - the real "stuck before this table
    # ever existed" scenario, distinct from the fresh-database case above.
    assert "character_bible_entries" in insp.get_table_names()
    assert {c["name"] for c in insp.get_columns("character_bible_entries")} == {
        "id", "user_id", "series_name", "series_name_key", "character_name",
        "character_name_key", "voice_description", "honorific_register",
        "relationships", "updated_at", "created_at",
    }
    # 0010 runs in this same chain too, same reasoning as 0009 above.
    assert "genre_calibration_samples" in insp.get_table_names()
    assert {c["name"] for c in insp.get_columns("genre_calibration_samples")} == {
        "id", "result_id", "genre_feel", "genre_bucket", "source_language",
        "target_language", "mean_rhyme_density", "rhyme_density_section_count",
        "phoneme_repetition_similarity", "created_at",
    }
