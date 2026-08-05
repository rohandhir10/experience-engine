"""Add paddle_processed_events table.

Idempotency guard for server/paddle.py's webhook handler - see
db_models.PaddleProcessedEvent's docstring for why an atomic INSERT
(not a SELECT-then-grant) is the only version of this check that's
actually race-free against Paddle redelivering the same event.

Guarded with a table-existence check for the same reason 0002-0005
needed one: a fresh database already gets this table from
0001_baseline's create_all (current model definitions, read at
runtime), so this only does real work against Railway's actual,
already-deployed database.

Revision ID: 0006_add_paddle_processed_events
Revises: 0005_add_credits
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_add_paddle_processed_events"
down_revision = "0005_add_credits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    if "paddle_processed_events" not in existing_tables:
        op.create_table(
            "paddle_processed_events",
            sa.Column("event_id", sa.String(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("paddle_processed_events")
