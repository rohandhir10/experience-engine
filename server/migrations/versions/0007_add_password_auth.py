"""Add email/password sign-up: users.password_hash, users.email_verified,
and the email_verification_tokens table.

Backfills email_verified = true for every existing row with a google_sub -
Google already verified that address at OAuth time, and treating a
pre-existing Google account as suddenly unverified the moment this
migration runs would lock real users out of features that start gating
on email_verified. Rows with no google_sub (there are none yet - password
sign-up didn't exist before this migration) get the column's real
default of false.

Guarded with existence checks for the same reason 0002-0006 needed them:
a genuinely fresh database already has both from 0001_baseline's
create_all (current model definitions, read at runtime), so this only
does real work against Railway's actual, already-deployed database.

Revision ID: 0007_add_password_auth
Revises: 0006_add_paddle_processed_events
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_add_password_auth"
down_revision = "0006_add_paddle_processed_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    columns = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "password_hash" not in columns:
        op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))
    if "email_verified" not in columns:
        op.add_column(
            "users",
            sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
        )
        op.execute("UPDATE users SET email_verified = true WHERE google_sub IS NOT NULL")

    existing_tables = set(sa.inspect(bind).get_table_names())
    if "email_verification_tokens" not in existing_tables:
        op.create_table(
            "email_verification_tokens",
            sa.Column("token_hash", sa.String(), primary_key=True),
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("email_verification_tokens")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "password_hash")
