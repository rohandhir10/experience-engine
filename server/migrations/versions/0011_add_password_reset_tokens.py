"""Add password_reset_tokens.

Same shape as 0007_add_password_auth's email_verification_tokens table -
see server/db_models.py::PasswordResetToken's docstring for the full
reasoning (hashed token as primary key, single-use via used_at).

Guarded with an existence check for the same reason 0002-0010 needed one:
a fresh database already gets this table from 0001_baseline's create_all
(current model definitions, read at runtime), so this only does real
work against Railway's actual, already-deployed database.

Revision ID: 0011_add_password_reset_tokens
Revises: 0010_add_genre_calibration_samples
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_add_password_reset_tokens"
down_revision = "0010_add_genre_calibration_samples"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())
    if "password_reset_tokens" in existing_tables:
        return

    op.create_table(
        "password_reset_tokens",
        sa.Column("token_hash", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
