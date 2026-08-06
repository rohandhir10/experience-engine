"""Add character_bible_entries.

Persists a character's voice_description/honorific_register/relationships
per (user, series_name, character_name), so a comics chapter can start
from what a PREVIOUS chapter of the same series already established
instead of Chapter DNA re-deriving a character's voice from scratch
every single chapter (engine/comics_adapt.py::merge_character_bible
reads this before a chapter runs; character_bible_updates writes it back
after). See server/db_models.py::CharacterBibleEntry's docstring for the
full reasoning, including why series identity here is just a free-text
name rather than a dedicated series table - there is no series concept
anywhere else in this product yet, and this is the simplest thing that
actually works.

Guarded with an existence check for the same reason 0002-0008 needed one:
a fresh database already gets this table from 0001_baseline's create_all
(current model definitions, read at runtime), so this only does real
work against Railway's actual, already-deployed database.

Revision ID: 0009_add_character_bibles
Revises: 0008_add_job_progress
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_add_character_bibles"
down_revision = "0008_add_job_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())
    if "character_bible_entries" in existing_tables:
        return

    op.create_table(
        "character_bible_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("series_name", sa.String(), nullable=False),
        sa.Column("series_name_key", sa.String(), nullable=False),
        sa.Column("character_name", sa.String(), nullable=False),
        sa.Column("character_name_key", sa.String(), nullable=False),
        sa.Column("voice_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("honorific_register", sa.Text(), nullable=False, server_default=""),
        sa.Column("relationships", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id", "series_name_key", "character_name_key",
            name="uq_character_bible_entry",
        ),
    )


def downgrade() -> None:
    op.drop_table("character_bible_entries")
