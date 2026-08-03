"""The one table that's genuinely provider-agnostic before an auth
provider is chosen — see server/db.py's module docstring for why
sessions/tokens aren't modeled yet.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

PLANS = ("free", "creator", "studio", "enterprise")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Nullable until an auth provider is wired: a row can exist keyed only
    # by google_sub (Google-first, per the stated auth plan) before an
    # email is known, or vice versa for an eventual email-based flow.
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    # A plain string, not a separate plans table — four tiers, no per-plan
    # relational data yet beyond the name itself.
    plan: Mapped[str] = mapped_column(String, default="free")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
