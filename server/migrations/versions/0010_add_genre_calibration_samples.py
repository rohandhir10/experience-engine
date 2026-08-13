"""Add genre_calibration_samples.

Starts accumulating the genre-labeled corpus docs/CAPABILITY_MATRIX.md's
"Genre-aware calibration" deferred gap has been blocked on since Phase 3 -
one row per real song adaptation, written best-effort by
server/genre_corpus.py::record_calibration_sample right after verify.py
runs. See server/db_models.py::GenreCalibrationSample's docstring for
the full reasoning, including why genre_bucket is a coarse keyword
classification rather than reusing Song DNA's free-text genre_feel
directly. This migration only creates the table - nothing here
calibrates anything yet.

Guarded with an existence check for the same reason 0002-0009 needed
one: a fresh database already gets this table from 0001_baseline's
create_all (current model definitions, read at runtime), so this only
does real work against Railway's actual, already-deployed database.

This revision's own id is also the fix for a separate, real bug it
exposed: Alembic's own bookkeeping table (`alembic_version`) defaults
`version_num` to `VARCHAR(32)`, and this revision's descriptive id -
34 characters, following the same naming convention every earlier
migration in this project used - is the first one to overflow it.
`tests/test_migrations.py` only ever runs migrations against SQLite,
which has no real column-length enforcement at all (its "VARCHAR(32)"
is a type hint, not a constraint), so this was completely invisible
there; running `alembic upgrade head` against a real local Postgres
(this project's actual production database on Railway) fails hard with
`StringDataRightTruncation` the moment this revision's own version gets
written - confirmed by actually standing up a local Postgres and running
it, not assumed from reading the code. See `upgrade()` below for the
widening fix, applied once and permanently (the column stays wide for
every future revision too, not just this one).

Revision ID: 0010_add_genre_calibration_samples
Revises: 0009_add_character_bibles
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_add_genre_calibration_samples"
down_revision = "0009_add_character_bibles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Must run BEFORE anything else, and unconditionally (not inside the
    # existence-check branch below) - it's Alembic's own end-of-step
    # bookkeeping write to alembic_version, not this migration's table
    # creation, that fails without it. SQLite doesn't need this (no real
    # length enforcement, and ALTER COLUMN TYPE isn't its syntax anyway).
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)")

    existing_tables = set(sa.inspect(bind).get_table_names())
    if "genre_calibration_samples" in existing_tables:
        return

    op.create_table(
        "genre_calibration_samples",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("result_id", sa.String(), nullable=False),
        sa.Column("genre_feel", sa.Text(), nullable=False),
        sa.Column("genre_bucket", sa.String(), nullable=False),
        sa.Column("source_language", sa.String(), nullable=False),
        sa.Column("target_language", sa.String(), nullable=False),
        sa.Column("mean_rhyme_density", sa.Float(), nullable=True),
        sa.Column("rhyme_density_section_count", sa.Integer(), nullable=False),
        sa.Column("phoneme_repetition_similarity", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("genre_calibration_samples")
