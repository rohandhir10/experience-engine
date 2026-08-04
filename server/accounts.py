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


# ---------------------------------------------------------------------------
# Collections
#
# The authorization rule for everything below: a collection is only ever
# reachable through a query scoped by user_id, exactly like set_favorite.
# Membership writes are the one place that needs TWO such lookups - the
# collection AND the adaptation must each independently belong to the
# caller. Checking only the collection would let someone file another
# user's adaptation into their own collection; checking only the
# adaptation would let them file their own into someone else's.
# ---------------------------------------------------------------------------


def create_collection(user_id: str, name: str) -> dict | None:
    """Names are not required to be unique - two collections called
    "Ghazals" are the user's business, and a uniqueness constraint here
    would fail a rename in a way that's annoying rather than protective.
    """
    if not _use_db():
        return None

    import uuid as _uuid

    from . import db
    from .db_models import Collection

    with db.session_scope() as session:
        collection = Collection(user_id=_uuid.UUID(user_id), name=name)
        session.add(collection)
        session.commit()
        return {"id": str(collection.id), "name": collection.name, "count": 0}


def list_collections(user_id: str) -> list[dict]:
    """Newest-first, each with its adaptation count. The count comes from
    a grouped join rather than len(collection.adaptations) so this stays
    one query instead of one-per-collection.
    """
    if not _use_db():
        return []

    import uuid as _uuid

    from sqlalchemy import func

    from . import db
    from .db_models import Collection, CollectionAdaptation

    with db.session_scope() as session:
        rows = (
            session.query(
                Collection, func.count(CollectionAdaptation.adaptation_id)
            )
            .outerjoin(
                CollectionAdaptation,
                Collection.id == CollectionAdaptation.collection_id,
            )
            .filter(Collection.user_id == _uuid.UUID(user_id))
            .group_by(Collection.id)
            .order_by(Collection.created_at.desc())
            .all()
        )
        return [
            {
                "id": str(collection.id),
                "name": collection.name,
                "count": count,
                "createdAt": collection.created_at.isoformat(),
            }
            for collection, count in rows
        ]


def rename_collection(user_id: str, collection_id: str, name: str) -> bool:
    if not _use_db():
        return False

    import uuid as _uuid

    from . import db
    from .db_models import Collection

    with db.session_scope() as session:
        collection = (
            session.query(Collection)
            .filter_by(id=_uuid.UUID(collection_id), user_id=_uuid.UUID(user_id))
            .one_or_none()
        )
        if collection is None:
            return False
        collection.name = name
        session.commit()
        return True


def delete_collection(user_id: str, collection_id: str) -> bool:
    """Deletes the collection and its membership rows. The adaptations
    themselves are untouched — a collection is a grouping, not ownership,
    so emptying a shelf never destroys the books on it.
    """
    if not _use_db():
        return False

    import uuid as _uuid

    from . import db
    from .db_models import Collection, CollectionAdaptation

    with db.session_scope() as session:
        collection = (
            session.query(Collection)
            .filter_by(id=_uuid.UUID(collection_id), user_id=_uuid.UUID(user_id))
            .one_or_none()
        )
        if collection is None:
            return False
        # Explicit rather than relying on the relationship's cascade —
        # the join rows are the thing that would silently orphan, and
        # being explicit here means this stays correct even if the
        # relationship config changes.
        session.query(CollectionAdaptation).filter_by(
            collection_id=collection.id
        ).delete()
        session.delete(collection)
        session.commit()
        return True


def set_collection_membership(
    user_id: str, collection_id: str, result_id: str, member: bool
) -> bool:
    """Adds/removes one adaptation to/from one collection. Returns False
    unless BOTH the collection and the adaptation belong to this user —
    see the module-section comment above for why one check isn't enough.
    Adding something already in the collection (or removing something
    that isn't) succeeds: the caller asked for a state, and that state
    now holds.
    """
    if not _use_db():
        return False

    import uuid as _uuid

    from . import db
    from .db_models import Adaptation, Collection, CollectionAdaptation

    uid = _uuid.UUID(user_id)
    with db.session_scope() as session:
        collection = (
            session.query(Collection)
            .filter_by(id=_uuid.UUID(collection_id), user_id=uid)
            .one_or_none()
        )
        if collection is None:
            return False
        adaptation = (
            session.query(Adaptation)
            .filter_by(user_id=uid, result_id=result_id)
            .one_or_none()
        )
        if adaptation is None:
            return False

        existing = (
            session.query(CollectionAdaptation)
            .filter_by(collection_id=collection.id, adaptation_id=adaptation.id)
            .one_or_none()
        )
        if member and existing is None:
            session.add(
                CollectionAdaptation(
                    collection_id=collection.id, adaptation_id=adaptation.id
                )
            )
        elif not member and existing is not None:
            session.delete(existing)
        session.commit()
        return True


def list_adaptations(
    user_id: str,
    limit: int = 50,
    favorites_only: bool = False,
    collection_id: str | None = None,
) -> list[dict]:
    """Newest-first history for one user, joined against cached_results
    for display fields (hook line, languages). A history row whose cached
    result has vanished still appears — with nulls — rather than
    silently disappearing from the user's history.

    favorites_only and collection_id both filter in SQL rather than
    trimming the returned list, so `limit` means "50 favorites", not
    "however many of the 50 newest adaptations happened to be favorited".

    collection_id is additionally scoped by user_id via the join, so
    passing someone else's collection id returns an empty list rather
    than their contents.
    """
    if not _use_db():
        return []

    import uuid as _uuid

    from . import db
    from .db_models import Adaptation, CachedResult, Collection, CollectionAdaptation

    uid = _uuid.UUID(user_id)
    with db.session_scope() as session:
        query = (
            session.query(Adaptation, CachedResult)
            .outerjoin(CachedResult, Adaptation.result_id == CachedResult.id)
            .filter(Adaptation.user_id == uid)
        )
        if favorites_only:
            query = query.filter(Adaptation.is_favorite.is_(True))
        if collection_id is not None:
            query = (
                query.join(
                    CollectionAdaptation,
                    CollectionAdaptation.adaptation_id == Adaptation.id,
                )
                .join(Collection, Collection.id == CollectionAdaptation.collection_id)
                .filter(
                    Collection.id == _uuid.UUID(collection_id),
                    # Redundant with the Adaptation.user_id filter above
                    # for well-formed data, but this is what makes
                    # "someone else's collection id" return empty rather
                    # than leaking, independent of that.
                    Collection.user_id == uid,
                )
            )
        rows = query.order_by(Adaptation.created_at.desc()).limit(limit).all()

        # Which collections each returned adaptation belongs to, so the
        # UI's "add to collection" menu opens already knowing its own
        # state. One grouped query for the whole page rather than one per
        # row. No user_id filter needed here: these adaptation ids came
        # out of a query already scoped to this user, so a join row
        # pointing at one of them is necessarily theirs.
        from collections import defaultdict

        membership: dict = defaultdict(list)
        adaptation_ids = [adaptation.id for adaptation, _ in rows]
        if adaptation_ids:
            join_rows = (
                session.query(
                    CollectionAdaptation.adaptation_id,
                    CollectionAdaptation.collection_id,
                )
                .filter(CollectionAdaptation.adaptation_id.in_(adaptation_ids))
                .all()
            )
            for adaptation_id, coll_id in join_rows:
                membership[adaptation_id].append(str(coll_id))

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
                    "collectionIds": membership.get(adaptation.id, []),
                }
            )
        return history
