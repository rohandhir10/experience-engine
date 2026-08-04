"""Add api_keys and api_key_usage tables.

New tables for server/api_keys.py's public API. Guarded with a
table-existence check for the same reason 0002 needed one (see that
migration's updated docstring): 0001_baseline's create_all builds every
table from CURRENT model definitions, so on a genuinely fresh database
these two tables already come out of the baseline (ApiKey/ApiKeyUsage
are permanent parts of db_models.py by the time this migration runs),
and a plain create_table would crash with "table already exists"
there - while still being exactly what's needed on Railway's real,
already-deployed database, where these tables are genuinely new.

Revision ID: 0003_add_api_keys
Revises: 0002_add_adaptation_medium
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_add_api_keys"
down_revision = "0002_add_adaptation_medium"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    if "api_keys" not in existing_tables:
        op.create_table(
            "api_keys",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("key_hash", sa.String(), nullable=False, unique=True),
            sa.Column("key_prefix", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "api_key_usage" not in existing_tables:
        op.create_table(
            "api_key_usage",
            sa.Column("day", sa.String(), primary_key=True),
            sa.Column("api_key_id", sa.Uuid(), sa.ForeignKey("api_keys.id"), primary_key=True),
            sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    op.drop_table("api_key_usage")
    op.drop_table("api_keys")
