"""Add monthly_quota_usage table.

The daily free-tier cap (daily_quota_usage, CASTIA_DAILY_LIMIT) resets
every day forever with no total ceiling - a persistent free IP had no
bound on cumulative monthly spend at all. This table backs the new
CASTIA_MONTHLY_LIMIT (server/quota.py::check_and_increment_monthly),
the real cost ceiling; the daily cap is now an anti-burst limit on top
of it, not the only control.

Guarded with a table-existence check for the same reason 0002 and 0003
needed one (see those migrations' docstrings): on a genuinely fresh
database, 0001_baseline's create_all already includes this table (it's
a permanent part of db_models.py by the time baseline runs), so a plain
create_table would crash with "table already exists" there - while
being exactly what's needed on Railway's real, already-deployed
database, where this table is genuinely new.

Revision ID: 0004_add_monthly_quota_usage
Revises: 0003_add_api_keys
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_add_monthly_quota_usage"
down_revision = "0003_add_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    if "monthly_quota_usage" not in existing_tables:
        op.create_table(
            "monthly_quota_usage",
            sa.Column("month", sa.String(), primary_key=True),
            sa.Column("ip", sa.String(), primary_key=True),
            sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    op.drop_table("monthly_quota_usage")
