"""User accounts + per-user adaptation history.

Identity itself lives in Auth.js (NextAuth) on the Next.js side — Google
OAuth, JWT session strategy, no session table anywhere. This module is
the Python side of that split: one `users` row per Google account
(upserted at sign-in via /api/users/sync) and one `adaptations` history
row per (user, result) pair. The JWT strategy is what lets us keep a
single user store: Auth.js never needs its own users/accounts/sessions
tables (the adapter-shape problem server/db.py's docstring warned
about), and the Python side stays the sole owner of user rows.

Trust model: these functions are called from endpoints gated by
`require_internal_secret` (server/main.py) — a shared secret
(AURA_INTERNAL_API_SECRET) known only to the Next.js server, which is
the party that actually verified the Google sign-in. A user id arriving
in a header is only ever honored alongside that secret; nothing here is
callable by a browser directly.

Everything degrades to a no-op/empty result when DATABASE_URL is unset
(local dev without Postgres, most tests) — same convention as
server/cache.py: accounts genuinely need shared storage, so there is no
in-memory pretend-mode that would fake durability the feature doesn't
have.
"""
from __future__ import annotations

import os


def _use_db() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def sync_user(google_sub: str, email: str | None, display_name: str | None) -> dict | None:
    """Upsert a user at sign-in time. Match order: google_sub first (the
    stable identifier), then email (adopts a row that was pre-created
    knowing only the email, attaching the sub to it). Returns
    {"id", "plan"} for the Auth.js jwt callback to stash in the token,
    or None when no database is configured.
    """
    if not _use_db():
        return None

    from . import db
    from .db_models import User

    with db.session_scope() as session:
        user = session.query(User).filter_by(google_sub=google_sub).one_or_none()
        if user is None and email:
            user = session.query(User).filter_by(email=email).one_or_none()
            if user is not None:
                user.google_sub = google_sub
        if user is None:
            user = User(google_sub=google_sub, email=email, display_name=display_name)
            session.add(user)
        else:
            # Refresh mutable profile fields on every sign-in — email and
            # display name can legitimately change on Google's side.
            if email:
                user.email = email
            if display_name:
                user.display_name = display_name
        session.commit()
        return {"id": str(user.id), "plan": user.plan}


def record_adaptation(user_id: str, result_id: str, source_language: str | None) -> None:
    """One history row per (user, result). A resubmission of the same song
    by the same user is a repeat view, not a new history entry — the
    version-history concept (db_models.Adaptation.song_key/version) is for
    deliberate reruns after engine changes, which nothing exposes yet.

    Deliberately swallows nothing: an invalid user_id raises (the caller
    gated it behind the internal secret, so a bad id is a bug, not user
    input).
    """
    if not _use_db():
        return

    import uuid as _uuid

    from . import db
    from .db_models import Adaptation

    with db.session_scope() as session:
        uid = _uuid.UUID(user_id)
        existing = (
            session.query(Adaptation)
            .filter_by(user_id=uid, result_id=result_id)
            .one_or_none()
        )
        if existing is not None:
            return
        session.add(
            Adaptation(
                user_id=uid,
                result_id=result_id,
                source_language=source_language,
                song_key=result_id,
            )
        )
        session.commit()


def set_favorite(user_id: str, result_id: str, is_favorite: bool) -> bool:
    """Toggles the favorite flag on one history row. Returns False when
    the user has no history row for that result — which is also the
    authorization boundary: the user_id is part of the lookup, so one
    user can never flip another user's row, and a request for a result
    they've never adapted is indistinguishable from one that doesn't
    exist. Returns False (not None) when no database is configured, so
    callers surface the same "couldn't do it" path either way.
    """
    if not _use_db():
        return False

    import uuid as _uuid

    from . import db
    from .db_models import Adaptation

    with db.session_scope() as session:
        row = (
            session.query(Adaptation)
            .filter_by(user_id=_uuid.UUID(user_id), result_id=result_id)
            .one_or_none()
        )
        if row is None:
            return False
        row.is_favorite = is_favorite
        session.commit()
        return True


def list_adaptations(
    user_id: str, limit: int = 50, favorites_only: bool = False
) -> list[dict]:
    """Newest-first history for one user, joined against cached_results
    for display fields (hook line, languages). A history row whose cached
    result has vanished still appears — with nulls — rather than
    silently disappearing from the user's history.

    favorites_only filters in SQL rather than trimming the returned list,
    so `limit` means "50 favorites", not "however many of the 50 newest
    adaptations happened to be favorited".
    """
    if not _use_db():
        return []

    import uuid as _uuid

    from . import db
    from .db_models import Adaptation, CachedResult

    with db.session_scope() as session:
        query = (
            session.query(Adaptation, CachedResult)
            .outerjoin(CachedResult, Adaptation.result_id == CachedResult.id)
            .filter(Adaptation.user_id == _uuid.UUID(user_id))
        )
        if favorites_only:
            query = query.filter(Adaptation.is_favorite.is_(True))
        rows = query.order_by(Adaptation.created_at.desc()).limit(limit).all()
        history: list[dict] = []
        for adaptation, cached in rows:
            result_json = cached.result_json if cached is not None else None
            history.append(
                {
                    "resultId": adaptation.result_id,
                    "createdAt": adaptation.created_at.isoformat(),
                    "isFavorite": adaptation.is_favorite,
                    "hook": (result_json or {}).get("hook"),
                    "sourceLanguage": (result_json or {}).get("sourceLanguage")
                    or adaptation.source_language,
                    "targetLanguage": (result_json or {}).get("targetLanguage"),
                }
            )
        return history
