"""Add adaptation_jobs.progress_json.

Lets a background job (server/jobs.py) report incremental status while
status="running" - which panel a comics chapter job is on and its
results-so-far (server/main.py's /api/comics/adapt/start) - instead of
only ever going pending -> running -> done with nothing in between for
the frontend to show. Nullable and unused by a song job, which has
nothing incremental to report today.

Guarded with a column-existence check for the same reason 0002-0007
needed one: a fresh database already gets this column from
0001_baseline's create_all (current model definitions, read at
runtime), so this only does real work against Railway's actual,
already-deployed database.

Revision ID: 0008_add_job_progress
Revises: 0007_add_password_auth
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_add_job_progress"
down_revision = "0007_add_password_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # adaptation_jobs itself may not exist yet on a database stuck before
    # 0001_baseline's create_all ever ran for it (mirrors the same
    # existence-guard reasoning 0002-0007 needed for their own tables) -
    # nothing to add a column to in that case; a later create_all would
    # bring the table in with progress_json already part of it, read from
    # the current model.
    if "adaptation_jobs" not in inspector.get_table_names():
        return

    columns = {c["name"] for c in inspector.get_columns("adaptation_jobs")}
    if "progress_json" not in columns:
        op.add_column("adaptation_jobs", sa.Column("progress_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("adaptation_jobs", "progress_json")
