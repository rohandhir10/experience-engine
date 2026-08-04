"""Add adaptations.medium ("music" | "webtoons").

The first real, frozen migration after the baseline (0001_baseline.py's
docstring committed to this being true going forward) - comics chapters
now get their own `Adaptation` history rows (server/main.py's
comics_adapt_endpoint), and every existing row predates that, so a
server-side default of "music" is a correct backfill, not a guess: no
adaptation row could have meant anything else before this column
existed.

Guarded with a column-existence check (not just `IF NOT EXISTS`, which
isn't portable to every backend this project's test suite runs against
- sqlite) because 0001_baseline's create_all(checkfirst=True) builds
every table from CURRENT model definitions, not the schema as it stood
when 0001 was authored - on a truly fresh database, `adaptations`
already comes out of the baseline WITH `medium` included, since
Adaptation.medium is now a permanent part of the model. Without this
guard, this migration would crash with "duplicate column" on any fresh
database, even though it works fine against Railway's real, already-
deployed one (that table predates this migration system entirely, so
checkfirst skips it there and this migration is genuinely the one
adding the column). Discovered by actually running migrate_to_head()
against a fresh database rather than assuming it worked.

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
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("adaptations")}
    if "medium" not in columns:
        op.add_column(
            "adaptations",
            sa.Column("medium", sa.String(), nullable=False, server_default="music"),
        )


def downgrade() -> None:
    op.drop_column("adaptations", "medium")
