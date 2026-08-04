"""Baseline: the full schema as of the migration system's introduction.

Not hand-listed table by table: this delegates to Base.metadata
(checkfirst=True), which makes it correct for BOTH deployment states
that exist when it first runs:

- A fresh, empty database (local dev pointing somewhere new, a future
  second environment): every table is created, then the revision is
  recorded — identical outcome to the old create_all() startup path.
- The already-deployed Railway database, where every table already
  exists: checkfirst skips them all, and the only real effect is the
  alembic_version row. No `alembic stamp` step to remember, nothing to
  coordinate — upgrading to head is safe from either starting point.

The tradeoff, stated honestly: because this reads Base.metadata at
runtime instead of freezing the schema in the file, it describes "the
schema as of whenever it runs," not "the schema as of 2026-08." That is
wrong for a migration in general — but for a BASELINE it is exactly the
create_all() behavior this system replaces, and every change AFTER this
revision must be a real, frozen migration (autogenerate + review), never
another metadata delegation. The pre-existing hand-patched drift columns
(server/db.py::_patch_known_schema_drift) stay covered by that startup
patch for existing databases; on fresh databases create_all includes
them from the models directly.

Revision ID: 0001_baseline
Revises: None
"""
from __future__ import annotations

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from server import db_models  # noqa: F401 — registers models on Base.metadata
    from server.db import Base

    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # Never auto-drop a whole production schema. If a baseline rollback is
    # ever genuinely needed, it's a deliberate manual operation.
    raise NotImplementedError("The baseline migration does not support downgrade.")
