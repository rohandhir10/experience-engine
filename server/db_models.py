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
    # Only set for the email/password sign-up path (server/password_auth.py)
    # - a PBKDF2-HMAC-SHA256 hash, never the plaintext password. Null for
    # a Google-only account, which has no password of its own.
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    # True the moment a Google account syncs (Google already verified that
    # address) or once an email/password account clicks its verification
    # link (server/password_auth.py::verify_email_token). False is the
    # real, meaningful "can't be trusted yet" state for a brand-new
    # password signup - see EmailVerificationToken below.
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # A plain string, not a separate plans table — four tiers, no per-plan
    # relational data yet beyond the name itself.
    plan: Mapped[str] = mapped_column(String, default="free")
    # The real balance, in the same credit unit /pricing quotes (web/app/
    # pricing/page.tsx's SONG_CREDITS/PAGE_CREDITS). Defaults to 0, not
    # some free grant - there is no free tier in the paid model this
    # backs (docs/CAPABILITY_MATRIX.md), so a new account starts owing
    # nothing and holding nothing, same as it will the day Paddle is
    # live. Never written directly outside server/credits.py's atomic
    # deduct/grant functions - see that module for why a plain
    # read-modify-write here would reintroduce the double-spend race.
    credits: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    adaptations: Mapped[list["Adaptation"]] = relationship(back_populates="user")
    collections: Mapped[list["Collection"]] = relationship(back_populates="user")
    credit_transactions: Mapped[list["CreditTransaction"]] = relationship(
        back_populates="user", order_by="CreditTransaction.created_at.desc()"
    )


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
    # "music" | "webtoons" - added once comics results started being
    # recorded too (server/main.py::comics_adapt_endpoint). Every row
    # before this column existed is unambiguously music, hence the
    # default rather than a nullable/backfill dance - see
    # migrations/versions/0002_add_adaptation_medium.py.
    medium: Mapped[str] = mapped_column(String, default="music", server_default="music")
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
    # server/cache.py::CACHE_VERSION at the time this row was computed.
    # find_similar() only reuses rows matching the CURRENT version, so a
    # row computed under stale prompt/pipeline logic gets regenerated
    # instead of silently resurfacing old output via a fuzzy (not exact
    # id) match. Defaults to "" precisely so pre-existing rows (from
    # before this column existed) never equal a real CACHE_VERSION value.
    cache_version: Mapped[str] = mapped_column(String, default="")
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AdaptationJob(Base):
    """Status for one /api/adapt/start background engine run
    (server/jobs.py). Backed by Postgres (rather than the in-memory dict
    this replaced) specifically so job status is visible to whichever
    process/instance a poll happens to land on - a job started on one
    Railway worker and polled via a request routed to a different one is
    exactly the failure an in-memory dict can't survive, and moving to a
    shared table is what actually removes that ceiling on running more
    than one instance/worker. Falls back to an in-memory dict when
    DATABASE_URL isn't set (local dev, tests) - see server/jobs.py.
    """

    __tablename__ = "adaptation_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|running|done|error
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class DailyQuotaUsage(Base):
    """Per-(day, ip) run count backing server.main's daily submission cap
    (CASTIA_DAILY_LIMIT) - an anti-burst limit only. See
    MonthlyQuotaUsage below for the actual cost ceiling; this table alone
    never bounded cumulative spend, since it resets every day forever.
    Same reasoning as AdaptationJob above: an in-memory dict can't be
    checked-and-incremented consistently across more than one process, so
    a burst split across instances could blow past the intended per-IP
    limit. Falls back to an in-memory dict when DATABASE_URL isn't set -
    see server/quota.py.
    """

    __tablename__ = "daily_quota_usage"

    day: Mapped[str] = mapped_column(String, primary_key=True)  # ISO date, e.g. "2026-08-03"
    ip: Mapped[str] = mapped_column(String, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class MonthlyQuotaUsage(Base):
    """Per-(month, ip) run count - the real free-tier cost ceiling.

    DailyQuotaUsage alone let a single free IP accumulate unbounded
    monthly spend (10/day forever, no total). This is the same shape one
    level up: a calendar-month key instead of a day key, checked
    alongside the daily cap in server.main::_check_quota
    (CASTIA_MONTHLY_LIMIT), same atomic-UPSERT reasoning as
    DailyQuotaUsage above.
    """

    __tablename__ = "monthly_quota_usage"

    month: Mapped[str] = mapped_column(String, primary_key=True)  # e.g. "2026-08"
    ip: Mapped[str] = mapped_column(String, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


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


class ApiKey(Base):
    """A key for the public API (server/api_keys.py), separate from the
    browser-facing account model: a signed-in user can hold several keys
    (e.g. one per project), each independently revocable. Only `key_hash`
    is ever stored — the raw key is returned to the user exactly once, at
    creation time, the same one-time-reveal convention every real API-key
    product uses (GitHub PATs, Stripe secret keys), so a leaked database
    can't be turned into working credentials.

    `key_prefix` exists purely for the dashboard's key list to be
    recognizable (e.g. "sk_live_a1b2...") without ever re-deriving or
    storing the full raw key — same reasoning GitHub/Stripe show a
    prefix, not the full token, once a key has been created.
    """

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # NULL = active. Never deleted outright - a revoked key stays as a
    # record of "this credential existed and was cut off here", same
    # audit-trail reasoning as soft-delete elsewhere in real API products.
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship()


class ApiKeyUsage(Base):
    """Per-(day, api_key) request count backing server/api_keys.py's rate
    limit - same atomic-UPSERT-under-concurrency reasoning as
    DailyQuotaUsage above, keyed by api_key_id instead of ip since a
    third-party API caller is identified by its key, not a browser's
    source IP (which a server-to-server caller doesn't meaningfully have
    one of anyway)."""

    __tablename__ = "api_key_usage"

    day: Mapped[str] = mapped_column(String, primary_key=True)
    api_key_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_keys.id"), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class CreditTransaction(Base):
    """Append-only credit ledger row - server/credits.py is the only
    writer, one row per grant (a Paddle purchase/subscription renewal,
    server/paddle.py's webhook handler) or debit (one per adaptation,
    server/main.py's adapt endpoints; a positive-amount refund row when
    the engine/GPU call that debit paid for fails).

    `balance_after` is a denormalized snapshot of User.credits
    immediately following this transaction, written in the same atomic
    UPDATE that changed it (server/credits.py) - lets the billing
    dashboard render a running-balance history without recomputing a sum
    over every prior row, and doubles as an audit trail: if this column's
    value ever disagrees with the live sum of amounts up to it, that is
    itself a real ledger bug to investigate, not something recomputation
    should silently paper over.
    """

    __tablename__ = "credit_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    # Positive = credited (purchase, subscription renewal, refund).
    # Negative = debited (one adaptation's cost).
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    # "purchase" | "subscription_renewal" | "adaptation" | "refund" - a
    # plain string, not an enum table, matching User.plan's own reasoning
    # (a handful of values, no relational data of their own yet).
    reason: Mapped[str] = mapped_column(String, nullable=False)
    # Paddle's transaction id for a grant, or the adaptation result_id
    # for a debit/refund - what this row is "about", for support/
    # debugging. Free text, not a foreign key: the two reference
    # different tables depending on `reason`, and a nullable/polymorphic
    # FK here is more machinery than a support lookup needs.
    reference: Mapped[str | None] = mapped_column(String, nullable=True)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="credit_transactions")


class PaddleProcessedEvent(Base):
    """Idempotency guard for server/paddle.py's webhook handler - Paddle
    documents that the same event can be delivered more than once (retry
    on a slow/ambiguous response), and this product's own atomic-insert
    convention (DailyQuotaUsage, MonthlyQuotaUsage above) is exactly the
    right tool: an INSERT that fails on a duplicate primary key is a
    race-free "have I seen this before" check, unlike a SELECT-then-
    grant, which two concurrent deliveries of the same webhook could
    both pass before either commits - crediting the same purchase twice.
    event_id is Paddle's own id for the notification, globally unique by
    their own design, so it's the primary key directly rather than a
    separate surrogate one.
    """

    __tablename__ = "paddle_processed_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class EmailVerificationToken(Base):
    """One row per outstanding "verify your email" link
    (server/password_auth.py). Only the SHA-256 hash of the actual token
    is stored - same reasoning as ApiKey.key_hash (server/api_keys.py):
    a database read alone should never be enough to mint a valid link.
    A fast hash is fine here (unlike a password) because the token itself
    is 32 random bytes of entropy, not a low-entropy human-chosen secret.

    Single-use: verify_email_token sets used_at and the row is never
    reused after that, even if the same link is clicked twice. Expired
    (now > expires_at) or already-used tokens are rejected identically -
    the token is simply no longer good, and the caller doesn't need to
    know which.
    """

    __tablename__ = "email_verification_tokens"

    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
