"""Add adaptations.medium ("music" | "webtoons").

The first real, frozen migration after the baseline (0001_baseline.py's
docstring committed to this being true going forward) - comics chapters
now get their own `Adaptation` history rows (server/main.py's
comics_adapt_endpoint), and every existing row predates that, so a
server-side default of "music" is a correct backfill, not a guess: no
adaptation row could have meant anything else before this column
existed.

Revision ID: 0002_add_adaptation_medium
Revises: 0001_baseline
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_add_adaptation_medium"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "adaptations",
        sa.Column("medium", sa.String(), nullable=False, server_default="music"),
    )


def downgrade() -> None:
    op.drop_column("adaptations", "medium")
