"""accounts.delete_account / accounts.export_account_data against a real
(sqlite file) database - same fixture convention as tests/test_credits.py
and tests/test_accounts.py, so these exercise the actual DELETE ordering
and the orphan scan rather than mocks.

web/app/privacy states GDPR/CCPA access and erasure as real practice.
Until these existed there was no endpoint behind that claim - the promise
was the only implementation. The tests that matter most here are the ones
that prove erasure is thorough (nothing left in any table) AND that it
stops at the boundary of other people's data (a shared, content-addressed
result that somebody else still points at must survive).
"""
from __future__ import annotations

import uuid

import pytest

import server.db as db
from server import accounts


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/deletion_test.db"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)
    db.create_all()
    yield url
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)


def _make_user(email: str = "a@example.com") -> str:
    from server.db_models import User

    with db.session_scope() as session:
        user = User(email=email, display_name="Test", credits=50)
        session.add(user)
        session.commit()
        return str(user.id)


def _make_cached_result(result_id: str) -> None:
    from server.db_models import CachedResult

    with db.session_scope() as session:
        session.add(
            CachedResult(
                id=result_id,
                normalized_text="some lyrics",
                result_json={"sections": [{"final_line": "a real adapted line"}]},
            )
        )
        session.commit()


def _make_adaptation(user_id: str, result_id: str) -> str:
    from server.db_models import Adaptation

    with db.session_scope() as session:
        row = Adaptation(
            user_id=uuid.UUID(user_id), result_id=result_id, song_key=result_id, medium="music"
        )
        session.add(row)
        session.commit()
        return str(row.id)


def _count(model) -> int:
    with db.session_scope() as session:
        return session.query(model).count()


# --- Erasure is thorough ----------------------------------------------


def test_deletes_the_user_and_every_row_belonging_to_them(sqlite_db):
    from server.db_models import (
        Adaptation, ApiKey, ApiKeyUsage, CharacterBibleEntry, Collection,
        CollectionAdaptation, CreditTransaction, EmailVerificationToken, User,
    )
    from datetime import datetime, timedelta, timezone

    user_id = _make_user()
    _make_cached_result("res-1")
    adaptation_id = _make_adaptation(user_id, "res-1")

    with db.session_scope() as session:
        uid = uuid.UUID(user_id)
        collection = Collection(user_id=uid, name="Favourites")
        session.add(collection)
        session.flush()
        session.add(
            CollectionAdaptation(
                collection_id=collection.id, adaptation_id=uuid.UUID(adaptation_id)
            )
        )
        key = ApiKey(user_id=uid, name="k", key_hash="h", key_prefix="sk_live_ab")
        session.add(key)
        session.flush()
        session.add(ApiKeyUsage(day="2026-08-10", api_key_id=key.id, count=3))
        session.add(
            CreditTransaction(user_id=uid, amount=-10, reason="adaptation", balance_after=40)
        )
        session.add(
            EmailVerificationToken(
                token_hash="th", user_id=uid,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        session.add(
            CharacterBibleEntry(
                user_id=uid, series_name="S", series_name_key="s",
                character_name="C", character_name_key="c",
            )
        )
        session.commit()

    assert accounts.delete_account(user_id) is True

    for model in (User, Adaptation, Collection, CollectionAdaptation, ApiKey,
                  ApiKeyUsage, CreditTransaction, EmailVerificationToken,
                  CharacterBibleEntry):
        assert _count(model) == 0, f"{model.__name__} rows survived deletion"


def test_returns_false_for_an_account_that_does_not_exist(sqlite_db):
    """A retried deletion must be safe, not an error."""
    assert accounts.delete_account(str(uuid.uuid4())) is False


def test_is_a_no_op_without_a_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert accounts.delete_account(str(uuid.uuid4())) is False


# --- ...but stops at other people's data ------------------------------


def test_a_shared_cached_result_survives_when_someone_else_still_points_at_it(sqlite_db):
    """The boundary that makes this safe to ship: results are
    content-addressed and SHARED, so erasing every result this user
    touched would destroy another user's history."""
    from server.db_models import CachedResult

    alice = _make_user("alice@example.com")
    bob = _make_user("bob@example.com")
    _make_cached_result("shared-result")
    _make_adaptation(alice, "shared-result")
    _make_adaptation(bob, "shared-result")

    assert accounts.delete_account(alice) is True

    # Bob's history still resolves.
    with db.session_scope() as session:
        assert session.get(CachedResult, "shared-result") is not None
    assert accounts.export_account_data(bob)["adaptations"][0]["result"] is not None


def test_a_result_only_this_user_ever_submitted_is_really_erased(sqlite_db):
    """The other half: leaving these behind would be an "erasure" that
    silently keeps the user's own submitted lyrics forever."""
    from server.db_models import CachedResult

    user_id = _make_user()
    _make_cached_result("only-mine")
    _make_adaptation(user_id, "only-mine")

    assert accounts.delete_account(user_id) is True

    with db.session_scope() as session:
        assert session.get(CachedResult, "only-mine") is None


def test_deleting_one_account_leaves_the_other_account_entirely_intact(sqlite_db):
    from server.db_models import Adaptation, User

    alice = _make_user("alice@example.com")
    bob = _make_user("bob@example.com")
    _make_cached_result("alice-only")
    _make_cached_result("bob-only")
    _make_adaptation(alice, "alice-only")
    _make_adaptation(bob, "bob-only")

    assert accounts.delete_account(alice) is True

    assert _count(User) == 1
    assert _count(Adaptation) == 1
    bob_data = accounts.export_account_data(bob)
    assert bob_data["account"]["email"] == "bob@example.com"
    assert len(bob_data["adaptations"]) == 1


def test_a_membership_row_pointing_at_this_users_adaptation_is_cleared(sqlite_db):
    """A join row can reference this user's adaptation from a collection
    that is not theirs - clearing only by collection would leave it
    behind, dangling at a deleted adaptation."""
    from server.db_models import Collection, CollectionAdaptation

    alice = _make_user("alice@example.com")
    bob = _make_user("bob@example.com")
    _make_cached_result("res-1")
    alice_adaptation = _make_adaptation(alice, "res-1")

    with db.session_scope() as session:
        bobs_collection = Collection(user_id=uuid.UUID(bob), name="Bob's shelf")
        session.add(bobs_collection)
        session.flush()
        session.add(
            CollectionAdaptation(
                collection_id=bobs_collection.id,
                adaptation_id=uuid.UUID(alice_adaptation),
            )
        )
        session.commit()

    assert accounts.delete_account(alice) is True

    assert _count(CollectionAdaptation) == 0
    assert _count(Collection) == 1  # Bob's shelf itself is untouched


# --- Export -----------------------------------------------------------


def test_export_includes_the_actual_adapted_text_not_just_ids(sqlite_db):
    """An export listing result ids the user can't read would satisfy the
    letter of an access request and none of its point."""
    user_id = _make_user()
    _make_cached_result("res-1")
    _make_adaptation(user_id, "res-1")

    data = accounts.export_account_data(user_id)
    assert data["adaptations"][0]["result"]["sections"][0]["final_line"] == "a real adapted line"


def test_export_never_includes_credential_material(sqlite_db):
    """Password and API-key hashes are the secrets protecting the user's
    data, not data the user should receive - an export that carried them
    would be a credential-leak vector."""
    import json

    from server.db_models import ApiKey, User

    user_id = _make_user()
    with db.session_scope() as session:
        session.get(User, uuid.UUID(user_id)).password_hash = "pbkdf2$super$secret$hash"
        session.add(
            ApiKey(
                user_id=uuid.UUID(user_id), name="k",
                key_hash="THE_SECRET_KEY_HASH", key_prefix="sk_live_ab",
            )
        )
        session.commit()

    dumped = json.dumps(accounts.export_account_data(user_id))
    assert "pbkdf2$super$secret$hash" not in dumped
    assert "THE_SECRET_KEY_HASH" not in dumped
    assert "password_hash" not in dumped
    # ...but the key is still *listed*, so the user can see what exists.
    assert "sk_live_ab" in dumped


def test_export_returns_none_for_an_unknown_account(sqlite_db):
    assert accounts.export_account_data(str(uuid.uuid4())) is None


def test_export_returns_none_without_a_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert accounts.export_account_data(str(uuid.uuid4())) is None


def test_export_of_a_brand_new_account_is_empty_but_real(sqlite_db):
    """Distinguishable from "no such account" - an account that simply
    hasn't done anything yet still exports its own record."""
    user_id = _make_user()
    data = accounts.export_account_data(user_id)
    assert data is not None
    assert data["account"]["email"] == "a@example.com"
    assert data["adaptations"] == []
    assert data["collections"] == []


def test_export_is_json_serializable(sqlite_db):
    """It's returned straight out of a FastAPI endpoint - a stray
    datetime or UUID would 500 at response time, not here."""
    import json

    user_id = _make_user()
    _make_cached_result("res-1")
    _make_adaptation(user_id, "res-1")
    json.dumps(accounts.export_account_data(user_id))
