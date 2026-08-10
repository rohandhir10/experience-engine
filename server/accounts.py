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
(CASTIA_INTERNAL_API_SECRET) known only to the Next.js server, which is
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
            user = User(
                google_sub=google_sub,
                email=email,
                display_name=display_name,
                email_verified=True,
            )
            session.add(user)
        else:
            # Refresh mutable profile fields on every sign-in — email and
            # display name can legitimately change on Google's side.
            if email:
                user.email = email
            if display_name:
                user.display_name = display_name
            # Google re-verifies the address on every sign-in, including
            # one that's adopting a row created by the password flow
            # (the email match above) - so this is the one place a
            # not-yet-verified password account can legitimately become
            # verified without ever clicking a link.
            user.email_verified = True
        session.commit()
        return {"id": str(user.id), "plan": user.plan}


def record_adaptation(
    user_id: str,
    result_id: str,
    source_language: str | None,
    medium: str = "music",
) -> None:
    """One history row per (user, result). A resubmission of the same song
    by the same user is a repeat view, not a new history entry — the
    version-history concept (db_models.Adaptation.song_key/version) is for
    deliberate reruns after engine changes, which nothing exposes yet.

    `medium` defaults to "music" (the only caller before comics existed);
    server/main.py's comics endpoint passes "webtoons" explicitly. Not
    part of the dedup key below — a result_id is already namespaced by
    its own content-id function per medium (server/cache.py's
    content_id vs. comics_content_id), so a collision across mediums
    isn't a real scenario this needs to defend against.

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
                medium=medium,
            )
        )
        session.commit()


def save_adaptation(user_id: str, result_id: str) -> bool:
    """Ensures a history row exists for a result the user is looking at
    but may never have adapted themselves — someone else's shared /s/<id>
    link. Idempotent, and returns False for a result that isn't in the
    cache at all, so this can't be used to fill the history table with
    rows pointing at ids that were never computed.

    Called on the result page when the user takes a save-type action
    (starring it, filing it into a collection), never on mere page view:
    opening a link someone sent you is not a decision to keep it.
    """
    if not _use_db():
        return False

    from . import db
    from .db_models import CachedResult

    with db.session_scope() as session:
        cached = session.get(CachedResult, result_id)
        if cached is None:
            return False
        source_language = (cached.result_json or {}).get("sourceLanguage")
    record_adaptation(user_id, result_id, source_language)
    return True


def get_adaptation(user_id: str, result_id: str) -> dict | None:
    """One history entry (favorite state + collection membership) for the
    result page's save controls, or None if this user has no history row
    for it. Same shape as one element of list_adaptations."""
    if not _use_db():
        return None

    import uuid as _uuid

    from . import db
    from .db_models import Adaptation, CachedResult, CollectionAdaptation

    with db.session_scope() as session:
        row = (
            session.query(Adaptation, CachedResult)
            .outerjoin(CachedResult, Adaptation.result_id == CachedResult.id)
            .filter(
                Adaptation.user_id == _uuid.UUID(user_id),
                Adaptation.result_id == result_id,
            )
            .one_or_none()
        )
        if row is None:
            return None
        adaptation, cached = row
        collection_ids = [
            str(coll_id)
            for (coll_id,) in session.query(CollectionAdaptation.collection_id)
            .filter(CollectionAdaptation.adaptation_id == adaptation.id)
            .all()
        ]
        return _entry_dict(adaptation, cached, collection_ids)


def _entry_dict(adaptation, cached, collection_ids: list[str]) -> dict:
    """The wire shape for one history entry, shared by list_adaptations
    and get_adaptation so the two can't drift into disagreeing about what
    a history entry looks like."""
    result_json = cached.result_json if cached is not None else None
    return {
        "resultId": adaptation.result_id,
        "createdAt": adaptation.created_at.isoformat(),
        "isFavorite": adaptation.is_favorite,
        "medium": adaptation.medium,
        "hook": (result_json or {}).get("hook"),
        "sourceLanguage": (result_json or {}).get("sourceLanguage")
        or adaptation.source_language,
        "targetLanguage": (result_json or {}).get("targetLanguage"),
        "collectionIds": collection_ids,
    }


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
    medium: str | None = None,
) -> list[dict]:
    """Newest-first history for one user, joined against cached_results
    for display fields (hook line, languages). A history row whose cached
    result has vanished still appears — with nulls — rather than
    silently disappearing from the user's history.

    favorites_only, collection_id, and medium all filter in SQL rather
    than trimming the returned list, so `limit` means "50 favorites" (or
    "50 webtoons"), not "however many of the 50 newest adaptations
    happened to match". `medium=None` (the default) returns both -
    dashboard history is one combined timeline, not two lists a caller
    has to merge itself; a caller wanting just one medium passes it
    explicitly.

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
        if medium is not None:
            query = query.filter(Adaptation.medium == medium)
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

        return [
            _entry_dict(adaptation, cached, membership.get(adaptation.id, []))
            for adaptation, cached in rows
        ]


# --- Account deletion and data export ---------------------------------
#
# web/app/privacy states GDPR/CCPA rights (access, erasure) as real
# practice. Until these existed there was no endpoint behind that claim
# at all - the promise was the only implementation. These two functions
# are what make it true.


def export_account_data(user_id: str) -> dict | None:
    """Everything this account owns, as plain JSON - the "right of
    access" half.

    Includes the adapted RESULTS, not just the history rows pointing at
    them: a export listing result ids the user can't read would satisfy
    the letter of an access request and none of its point. Credential
    material is deliberately excluded - password_hash and api key hashes
    are not the user's data to receive, they're the secrets protecting
    it, and reproducing them in a file that gets emailed around would
    make an export a credential-leak vector. API keys are listed by
    name/prefix so the user can see what exists without the key itself
    (which was only ever shown once, at creation - see ApiKey's model
    docstring).

    Returns None when there's no database (nothing to export) or no such
    user, which the caller distinguishes from an empty-but-real account.
    """
    if not _use_db():
        return None

    import uuid as _uuid

    from . import db
    from .db_models import (
        Adaptation,
        ApiKey,
        CachedResult,
        CharacterBibleEntry,
        Collection,
        CollectionAdaptation,
        CreditTransaction,
        User,
    )

    with db.session_scope() as session:
        uid = _uuid.UUID(user_id)
        user = session.get(User, uid)
        if user is None:
            return None

        adaptations = session.query(Adaptation).filter_by(user_id=uid).all()
        result_ids = {a.result_id for a in adaptations}
        cached = {
            row.id: row
            for row in session.query(CachedResult).filter(CachedResult.id.in_(result_ids)).all()
        } if result_ids else {}

        collections = session.query(Collection).filter_by(user_id=uid).all()
        collection_ids = [c.id for c in collections]
        memberships: dict[str, list[str]] = {}
        if collection_ids:
            for row in session.query(CollectionAdaptation).filter(
                CollectionAdaptation.collection_id.in_(collection_ids)
            ).all():
                memberships.setdefault(str(row.collection_id), []).append(str(row.adaptation_id))

        return {
            "account": {
                "id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "email_verified": user.email_verified,
                "plan": user.plan,
                "credits": user.credits,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "adaptations": [
                {
                    "id": str(a.id),
                    "result_id": a.result_id,
                    "medium": a.medium,
                    "source_language": a.source_language,
                    "song_key": a.song_key,
                    "version": a.version,
                    "verified": a.verified,
                    "is_favorite": a.is_favorite,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    # The actual adapted text, not just a pointer to it.
                    "result": cached[a.result_id].result_json if a.result_id in cached else None,
                }
                for a in adaptations
            ],
            "collections": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "adaptation_ids": memberships.get(str(c.id), []),
                }
                for c in collections
            ],
            "credit_transactions": [
                {
                    "amount": t.amount,
                    "reason": t.reason,
                    "reference": t.reference,
                    "balance_after": t.balance_after,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in session.query(CreditTransaction).filter_by(user_id=uid).all()
            ],
            # Names and prefixes only - never key_hash. See the docstring.
            "api_keys": [
                {
                    "name": k.name,
                    "key_prefix": k.key_prefix,
                    "created_at": k.created_at.isoformat() if k.created_at else None,
                    "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                    "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None,
                }
                for k in session.query(ApiKey).filter_by(user_id=uid).all()
            ],
            "character_bibles": [
                {
                    "series_name": e.series_name,
                    "character_name": e.character_name,
                    "voice_description": e.voice_description,
                    "honorific_register": e.honorific_register,
                    "relationships": e.relationships,
                    "updated_at": e.updated_at.isoformat() if e.updated_at else None,
                }
                for e in session.query(CharacterBibleEntry).filter_by(user_id=uid).all()
            ],
        }


def delete_account(user_id: str) -> bool:
    """Erases the account and everything belonging to it. Irreversible -
    the caller is responsible for confirming intent before calling.

    Deletion order is explicit and child-first rather than relying on ORM
    cascades: several of these relationships have no cascade configured
    at all, and a foreign key that only fails in production (where a real
    Postgres enforces it) is exactly the kind of bug a local sqlite test
    can miss.

    CachedResult needs the care. Those rows are content-addressed and
    SHARED - two users who adapted the same song point at one row - so
    deleting every result this user touched would destroy other people's
    history. But leaving all of them behind would mean an "erasure" that
    keeps the user's own submitted lyrics forever whenever they were the
    only person who ever submitted them. So: delete exactly those results
    that no REMAINING adaptation references. A row still referenced by
    somebody else survives (it's their data too); a row nobody else ever
    referenced goes, because at that point it was only ever this user's.

    Returns False when there's no database or no such user - never raises
    for "already gone", so a retried deletion is safe.
    """
    if not _use_db():
        return False

    import uuid as _uuid

    from . import db
    from .db_models import (
        Adaptation,
        ApiKey,
        ApiKeyUsage,
        CachedResult,
        CharacterBibleEntry,
        Collection,
        CollectionAdaptation,
        CreditTransaction,
        EmailVerificationToken,
        User,
    )

    with db.session_scope() as session:
        uid = _uuid.UUID(user_id)
        user = session.get(User, uid)
        if user is None:
            return False

        adaptation_ids = [
            row.id for row in session.query(Adaptation.id).filter_by(user_id=uid).all()
        ]
        touched_result_ids = {
            row.result_id
            for row in session.query(Adaptation.result_id).filter_by(user_id=uid).all()
        }
        collection_ids = [
            row.id for row in session.query(Collection.id).filter_by(user_id=uid).all()
        ]
        api_key_ids = [row.id for row in session.query(ApiKey.id).filter_by(user_id=uid).all()]

        # Join rows first - they reference both collections and
        # adaptations, so they have to go before either side. Cleared via
        # BOTH sides: a membership row can point at this user's
        # adaptation from a collection that is not theirs.
        if collection_ids:
            session.query(CollectionAdaptation).filter(
                CollectionAdaptation.collection_id.in_(collection_ids)
            ).delete(synchronize_session=False)
        if adaptation_ids:
            session.query(CollectionAdaptation).filter(
                CollectionAdaptation.adaptation_id.in_(adaptation_ids)
            ).delete(synchronize_session=False)

        if api_key_ids:
            session.query(ApiKeyUsage).filter(
                ApiKeyUsage.api_key_id.in_(api_key_ids)
            ).delete(synchronize_session=False)

        for model in (Adaptation, Collection, ApiKey, CreditTransaction,
                      EmailVerificationToken, CharacterBibleEntry):
            session.query(model).filter_by(user_id=uid).delete(synchronize_session=False)

        session.delete(user)
        # Flush before the orphan scan so the deletes above are visible to
        # the query below within this transaction - otherwise every result
        # still looks referenced by the rows we just removed.
        session.flush()

        if touched_result_ids:
            still_referenced = {
                row.result_id
                for row in session.query(Adaptation.result_id)
                .filter(Adaptation.result_id.in_(touched_result_ids))
                .all()
            }
            orphaned = touched_result_ids - still_referenced
            if orphaned:
                session.query(CachedResult).filter(
                    CachedResult.id.in_(orphaned)
                ).delete(synchronize_session=False)

        session.commit()
        return True
