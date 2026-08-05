"""Add users.credits and the credit_transactions ledger table.

The pricing model (web/app/pricing/page.tsx) and the double-spend-safe
atomic deduction it needs (server/credits.py) were both designed before
either had anywhere to actually store a balance - every account has had
`credits = 0` implicitly, nowhere. This is that column, plus the
append-only transaction log server/credits.py writes to alongside it.

Backfilled to 0 for every existing row, not some default grant: there is
no free tier in this pricing model (docs/CAPABILITY_MATRIX.md, the
"kill the free tier" decision), so an account created before this
column existed owning 0 credits is exactly as correct as one created
after it - neither should have gotten anything for free.

Guarded with existence checks for the same reason 0002-0004 needed them
(see those migrations' docstrings): a genuinely fresh database already
gets both from 0001_baseline's create_all (current model definitions,
read at runtime), so this only does real work against Railway's actual,
already-deployed database, where both are genuinely new.

Revision ID: 0005_add_credits
Revises: 0004_add_monthly_quota_usage
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_add_credits"
down_revision = "0004_add_monthly_quota_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    columns = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "credits" not in columns:
        op.add_column(
            "users",
            sa.Column("credits", sa.Integer(), nullable=False, server_default="0"),
        )

    existing_tables = set(sa.inspect(bind).get_table_names())
    if "credit_transactions" not in existing_tables:
        op.create_table(
            "credit_transactions",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("reason", sa.String(), nullable=False),
            sa.Column("reference", sa.String(), nullable=True),
            sa.Column("balance_after", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("credit_transactions")
    op.drop_column("users", "credits")
