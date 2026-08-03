"""Postgres schema for the account/dashboard features. See server/db.py's
module docstring for why there's no sessions/tokens table yet.

Adaptation is deliberately separate from server/cache.py's content-address
cache: cache.py stores one computed result per unique source text, shared
across whoever submits it; Adaptation is a per-user history row that
*points at* a result_id, so two different users pasting the same lyrics
each get their own history entry (own created_at, own favorite flag, own
collections) without duplicating the underlying computed result.

`song_key` + `version` exist now, ahead of the rerun feature that would
actually populate more than version 1, because retrofitting a version
concept onto rows that already exist is real migration work — adding the
columns while the table is still empty costs nothing. A rerun of the same
song_key should insert a new row with version incremented, never mutate a
past version in place, so old adaptations stay comparable against new
ones (the point of version history at all).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

PLANS = ("free", "creator", "studio", "enterprise")


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    adaptations: Mapped[list["Adaptation"]] = relationship(back_populates="user")
    collections: Mapped[list["Collection"]] = relationship(back_populates="user")


class Adaptation(Base):
    __tablename__ = "adaptations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    # server/cache.py's content-addressed id — the actual computed result
    # (source, sections, judge notes) lives there, not duplicated here.
    result_id: Mapped[str] = mapped_column(String, nullable=False)
    # No title field: the engine doesn't extract a song title today, and
    # guessing one from the lyrics would be fabricated metadata.
    source_language: Mapped[str | None] = mapped_column(String, nullable=True)
    # Groups reruns of "the same song" together; defaults to its own
    # result_id so a first-time adaptation is version 1 of itself.
    song_key: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    # Whether engine/verify.py reported zero error-severity findings for
    # this run (server/main.py already computes this per-request; it just
    # isn't persisted anywhere yet) - a real, measured signal, not a
    # fabricated "Verified" badge.
    verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="adaptations")
    collections: Mapped[list["Collection"]] = relationship(
        secondary="collection_adaptations", back_populates="adaptations"
    )


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="collections")
    adaptations: Mapped[list["Adaptation"]] = relationship(
        secondary="collection_adaptations", back_populates="collections"
    )


class CachedResult(Base):
    """The actual computed engine output, keyed by server/cache.py's
    content-addressed id — one row per unique song, shared across
    whichever users submitted it, regardless of how many Adaptation
    history rows point at it.

    `normalized_text` is a more aggressive normalization than the id's
    own hash (case-folded, punctuation stripped, whitespace collapsed) so
    server/cache.py can do a similarity scan for near-identical pastes
    (typos, re-formatted line breaks) that the exact hash would miss —
    see cache.py's find_similar for the actual matching logic and why
    it's a plain Python scan rather than a database extension.
    """

    __tablename__ = "cached_results"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    # A near-identical paste only counts as "the same song" if it was also
    # asked for in the same source AND target language - two rows can
    # otherwise share near-identical normalized_text (an English source
    # adapted into Hindi vs. a Korean source adapted into Hindi) while
    # being completely different, non-interchangeable results.
    target_language: Mapped[str] = mapped_column(String, default="English")
    source_language: Mapped[str] = mapped_column(String, default="unspecified")
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CollectionAdaptation(Base):
    """Many-to-many join: a collection groups adaptations, and one
    adaptation can sit in more than one collection (e.g. both "Hindi Rock"
    and a genre-crossing playlist)."""

    __tablename__ = "collection_adaptations"

    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collections.id"), primary_key=True
    )
    adaptation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("adaptations.id"), primary_key=True
    )
