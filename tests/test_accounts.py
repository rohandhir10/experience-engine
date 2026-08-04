"""Accounts + per-user history, run against a real (sqlite file) database
via DATABASE_URL — these exercise the actual DB code paths in
server/accounts.py, not mocks. Postgres-specific behavior (the quota
UPSERT) is out of scope here, same disclosure as tests/test_quota.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import server.db as db
import server.main as main
from server import accounts, cache


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    """Point DATABASE_URL at a fresh sqlite file and reset server/db.py's
    cached engine/sessionmaker so it actually binds to it (get_engine
    caches globally — without the reset, the first test to run would pin
    every later test to its own URL)."""
    url = f"sqlite:///{tmp_path}/accounts_test.db"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)
    db.create_all()
    yield url
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)


@pytest.fixture()
def client():
    return TestClient(main.app)


# ---------------------------------------------------------------------------
# accounts.py against the real schema
# ---------------------------------------------------------------------------


def test_sync_creates_a_user_and_is_idempotent(sqlite_db):
    first = accounts.sync_user("google-sub-1", "a@b.com", "A")
    again = accounts.sync_user("google-sub-1", "a@b.com", "A")
    assert first["plan"] == "free"
    assert first["id"] == again["id"]


def test_sync_adopts_a_preexisting_email_only_row(sqlite_db):
    from server.db_models import User

    with db.session_scope() as session:
        session.add(User(email="pre@existing.com"))
        session.commit()
        pre_id = str(session.query(User).one().id)

    synced = accounts.sync_user("google-sub-2", "pre@existing.com", "Pre")
    assert synced["id"] == pre_id


def test_sync_refreshes_profile_fields(sqlite_db):
    accounts.sync_user("google-sub-3", "old@mail.com", "Old Name")
    accounts.sync_user("google-sub-3", "new@mail.com", "New Name")
    from server.db_models import User

    with db.session_scope() as session:
        user = session.query(User).filter_by(google_sub="google-sub-3").one()
        assert user.email == "new@mail.com"
        assert user.display_name == "New Name"


def test_record_adaptation_dedupes_per_user_and_result(sqlite_db):
    user = accounts.sync_user("google-sub-4", "u@m.com", None)
    accounts.record_adaptation(user["id"], "result-abc", "Hindi")
    accounts.record_adaptation(user["id"], "result-abc", "Hindi")
    from server.db_models import Adaptation

    with db.session_scope() as session:
        assert session.query(Adaptation).count() == 1


def test_list_adaptations_joins_display_fields_from_the_cached_result(sqlite_db):
    user = accounts.sync_user("google-sub-5", "u@m.com", None)
    cache.set(
        "result-xyz",
        {"hook": "Holding on is loyalty.", "sourceLanguage": "Hindi", "targetLanguage": "English"},
        source_text="some lyrics",
        target_language="English",
        source_language="Hindi",
    )
    accounts.record_adaptation(user["id"], "result-xyz", "Hindi")

    history = accounts.list_adaptations(user["id"])
    assert len(history) == 1
    entry = history[0]
    assert entry["resultId"] == "result-xyz"
    assert entry["hook"] == "Holding on is loyalty."
    assert entry["sourceLanguage"] == "Hindi"
    assert entry["targetLanguage"] == "English"
    assert entry["isFavorite"] is False


def test_history_survives_a_vanished_cached_result(sqlite_db):
    user = accounts.sync_user("google-sub-6", "u@m.com", None)
    accounts.record_adaptation(user["id"], "result-gone", "Korean")
    history = accounts.list_adaptations(user["id"])
    assert len(history) == 1
    assert history[0]["hook"] is None
    assert history[0]["sourceLanguage"] == "Korean"


def test_no_database_means_accounts_decline_not_crash(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert accounts.sync_user("sub", "e@m.com", None) is None
    assert accounts.list_adaptations("any-id") == []
    assert accounts.set_favorite("any-id", "result", True) is False
    accounts.record_adaptation("any-id", "result", None)  # no-op, no raise


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------


def test_favorite_can_be_set_and_cleared(sqlite_db):
    user = accounts.sync_user("fav-1", "u@m.com", None)
    accounts.record_adaptation(user["id"], "song-1", "Hindi")

    assert accounts.set_favorite(user["id"], "song-1", True) is True
    assert accounts.list_adaptations(user["id"])[0]["isFavorite"] is True

    assert accounts.set_favorite(user["id"], "song-1", False) is True
    assert accounts.list_adaptations(user["id"])[0]["isFavorite"] is False


def test_favoriting_a_song_not_in_your_history_fails(sqlite_db):
    user = accounts.sync_user("fav-2", "u@m.com", None)
    assert accounts.set_favorite(user["id"], "never-adapted", True) is False


def test_one_user_cannot_favorite_another_users_row(sqlite_db):
    """The authorization boundary: set_favorite scopes its lookup by
    user_id, so B flipping A's row is indistinguishable from flipping a
    row that doesn't exist — it fails, and A's row is untouched."""
    a = accounts.sync_user("fav-a", "a@m.com", None)
    b = accounts.sync_user("fav-b", "b@m.com", None)
    accounts.record_adaptation(a["id"], "shared-song", "Hindi")

    assert accounts.set_favorite(b["id"], "shared-song", True) is False
    assert accounts.list_adaptations(a["id"])[0]["isFavorite"] is False


def test_favorites_only_filters_the_listing(sqlite_db):
    user = accounts.sync_user("fav-3", "u@m.com", None)
    accounts.record_adaptation(user["id"], "song-a", "Hindi")
    accounts.record_adaptation(user["id"], "song-b", "Korean")
    accounts.set_favorite(user["id"], "song-b", True)

    favorites = accounts.list_adaptations(user["id"], favorites_only=True)
    assert [entry["resultId"] for entry in favorites] == ["song-b"]
    assert len(accounts.list_adaptations(user["id"])) == 2


def test_favorite_endpoint_404s_for_a_song_not_in_history(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("fav-4", "u@m.com", None)
    response = client.post(
        "/api/me/adaptations/nope/favorite",
        json={"is_favorite": True},
        headers={"X-Aura-User-Id": user["id"], "X-Aura-Internal-Secret": "right"},
    )
    assert response.status_code == 404


def test_favorite_endpoint_requires_the_internal_secret(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("fav-5", "u@m.com", None)
    accounts.record_adaptation(user["id"], "song-c", "Hindi")

    response = client.post(
        "/api/me/adaptations/song-c/favorite",
        json={"is_favorite": True},
        headers={"X-Aura-User-Id": user["id"]},  # no secret
    )
    assert response.status_code == 401
    assert accounts.list_adaptations(user["id"])[0]["isFavorite"] is False


def test_collections_crud_round_trip(sqlite_db):
    user = accounts.sync_user("col-1", "u@m.com", None)
    created = accounts.create_collection(user["id"], "Ghazals")
    assert created["name"] == "Ghazals"
    assert created["count"] == 0

    assert accounts.rename_collection(user["id"], created["id"], "Qawwali") is True
    listed = accounts.list_collections(user["id"])
    assert [c["name"] for c in listed] == ["Qawwali"]

    assert accounts.delete_collection(user["id"], created["id"]) is True
    assert accounts.list_collections(user["id"]) == []


def test_collection_membership_and_counts(sqlite_db):
    user = accounts.sync_user("col-2", "u@m.com", None)
    collection = accounts.create_collection(user["id"], "Hindi Rock")
    accounts.record_adaptation(user["id"], "song-1", "Hindi")
    accounts.record_adaptation(user["id"], "song-2", "Hindi")

    assert accounts.set_collection_membership(
        user["id"], collection["id"], "song-1", True
    ) is True
    assert accounts.list_collections(user["id"])[0]["count"] == 1

    in_collection = accounts.list_adaptations(user["id"], collection_id=collection["id"])
    assert [e["resultId"] for e in in_collection] == ["song-1"]
    # The full history is unaffected by collection membership.
    assert len(accounts.list_adaptations(user["id"])) == 2


def test_membership_writes_are_idempotent(sqlite_db):
    """Adding twice (or removing something that was never in) is a
    success — the caller asked for a state and that state now holds."""
    user = accounts.sync_user("col-3", "u@m.com", None)
    collection = accounts.create_collection(user["id"], "C")
    accounts.record_adaptation(user["id"], "song-1", "Hindi")

    assert accounts.set_collection_membership(user["id"], collection["id"], "song-1", True)
    assert accounts.set_collection_membership(user["id"], collection["id"], "song-1", True)
    assert accounts.list_collections(user["id"])[0]["count"] == 1

    assert accounts.set_collection_membership(user["id"], collection["id"], "song-1", False)
    assert accounts.set_collection_membership(user["id"], collection["id"], "song-1", False)
    assert accounts.list_collections(user["id"])[0]["count"] == 0


def test_cannot_file_another_users_adaptation_into_your_collection(sqlite_db):
    """The two-sided ownership check. A owns the song, B owns the
    collection — B must not be able to file A's song into it. Checking
    only the collection's owner would allow exactly this."""
    a = accounts.sync_user("col-a", "a@m.com", None)
    b = accounts.sync_user("col-b", "b@m.com", None)
    accounts.record_adaptation(a["id"], "a-song", "Hindi")
    b_collection = accounts.create_collection(b["id"], "B's shelf")

    assert accounts.set_collection_membership(
        b["id"], b_collection["id"], "a-song", True
    ) is False
    assert accounts.list_collections(b["id"])[0]["count"] == 0


def test_cannot_file_your_adaptation_into_another_users_collection(sqlite_db):
    """The other half. B owns the song, A owns the collection — B must
    not be able to add to A's collection. Checking only the adaptation's
    owner would allow this one."""
    a = accounts.sync_user("col-c", "a@m.com", None)
    b = accounts.sync_user("col-d", "b@m.com", None)
    a_collection = accounts.create_collection(a["id"], "A's shelf")
    accounts.record_adaptation(b["id"], "b-song", "Korean")

    assert accounts.set_collection_membership(
        b["id"], a_collection["id"], "b-song", True
    ) is False
    assert accounts.list_collections(a["id"])[0]["count"] == 0


def test_cannot_rename_or_delete_another_users_collection(sqlite_db):
    a = accounts.sync_user("col-e", "a@m.com", None)
    b = accounts.sync_user("col-f", "b@m.com", None)
    a_collection = accounts.create_collection(a["id"], "Original")

    assert accounts.rename_collection(b["id"], a_collection["id"], "Hacked") is False
    assert accounts.delete_collection(b["id"], a_collection["id"]) is False
    assert accounts.list_collections(a["id"])[0]["name"] == "Original"


def test_listing_another_users_collection_returns_empty(sqlite_db):
    a = accounts.sync_user("col-g", "a@m.com", None)
    b = accounts.sync_user("col-h", "b@m.com", None)
    a_collection = accounts.create_collection(a["id"], "A's shelf")
    accounts.record_adaptation(a["id"], "a-song", "Hindi")
    accounts.set_collection_membership(a["id"], a_collection["id"], "a-song", True)

    assert accounts.list_adaptations(b["id"], collection_id=a_collection["id"]) == []


def test_deleting_a_collection_keeps_the_adaptations(sqlite_db):
    """A collection is a grouping, not ownership — emptying the shelf
    must not destroy the books."""
    user = accounts.sync_user("col-i", "u@m.com", None)
    collection = accounts.create_collection(user["id"], "Temp")
    accounts.record_adaptation(user["id"], "kept-song", "Hindi")
    accounts.set_collection_membership(user["id"], collection["id"], "kept-song", True)

    assert accounts.delete_collection(user["id"], collection["id"]) is True
    assert [e["resultId"] for e in accounts.list_adaptations(user["id"])] == ["kept-song"]
    # And the join row is gone, not orphaned.
    from server.db_models import CollectionAdaptation

    with db.session_scope() as session:
        assert session.query(CollectionAdaptation).count() == 0


def test_no_database_means_collections_decline(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert accounts.create_collection("u", "C") is None
    assert accounts.list_collections("u") == []
    assert accounts.rename_collection("u", "c", "N") is False
    assert accounts.delete_collection("u", "c") is False
    assert accounts.set_collection_membership("u", "c", "r", True) is False


def test_collection_endpoints_round_trip(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("col-j", "u@m.com", None)
    accounts.record_adaptation(user["id"], "song-e", "Spanish")
    headers = {"X-Aura-User-Id": user["id"], "X-Aura-Internal-Secret": "right"}

    created = client.post("/api/me/collections", json={"name": "Reggaeton"}, headers=headers)
    assert created.status_code == 200
    collection_id = created.json()["id"]

    added = client.post(
        f"/api/me/collections/{collection_id}/adaptations/song-e",
        json={"member": True},
        headers=headers,
    )
    assert added.status_code == 200

    listed = client.get(
        f"/api/me/adaptations?collection_id={collection_id}", headers=headers
    )
    assert [e["resultId"] for e in listed.json()["adaptations"]] == ["song-e"]

    renamed = client.patch(
        f"/api/me/collections/{collection_id}", json={"name": "Latin"}, headers=headers
    )
    assert renamed.status_code == 200
    assert client.get("/api/me/collections", headers=headers).json()["collections"][0][
        "name"
    ] == "Latin"

    deleted = client.delete(f"/api/me/collections/{collection_id}", headers=headers)
    assert deleted.status_code == 200
    assert client.get("/api/me/collections", headers=headers).json()["collections"] == []


def test_collection_endpoints_reject_blank_names(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("col-k", "u@m.com", None)
    headers = {"X-Aura-User-Id": user["id"], "X-Aura-Internal-Secret": "right"}
    response = client.post("/api/me/collections", json={"name": "   "}, headers=headers)
    assert response.status_code == 400


def test_malformed_collection_id_is_a_404_not_a_500(client, monkeypatch, sqlite_db):
    """A garbage id must not crash on UUID parsing, and must be
    indistinguishable from a well-formed id that isn't yours."""
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("col-l", "u@m.com", None)
    headers = {"X-Aura-User-Id": user["id"], "X-Aura-Internal-Secret": "right"}

    assert client.delete("/api/me/collections/not-a-uuid", headers=headers).status_code == 404
    assert (
        client.patch(
            "/api/me/collections/not-a-uuid", json={"name": "x"}, headers=headers
        ).status_code
        == 404
    )
    assert (
        client.get("/api/me/adaptations?collection_id=not-a-uuid", headers=headers).status_code
        == 400
    )


def test_collection_endpoints_require_the_internal_secret(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("col-m", "u@m.com", None)
    response = client.post(
        "/api/me/collections", json={"name": "X"}, headers={"X-Aura-User-Id": user["id"]}
    )
    assert response.status_code == 401
    assert accounts.list_collections(user["id"]) == []


def test_favorite_endpoint_round_trip(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("fav-6", "u@m.com", None)
    accounts.record_adaptation(user["id"], "song-d", "Spanish")
    headers = {"X-Aura-User-Id": user["id"], "X-Aura-Internal-Secret": "right"}

    response = client.post(
        "/api/me/adaptations/song-d/favorite", json={"is_favorite": True}, headers=headers
    )
    assert response.status_code == 200
    assert response.json() == {"resultId": "song-d", "isFavorite": True}

    listed = client.get("/api/me/adaptations?favorites_only=true", headers=headers)
    assert [e["resultId"] for e in listed.json()["adaptations"]] == ["song-d"]


# ---------------------------------------------------------------------------
# Endpoint gating — the trust model
# ---------------------------------------------------------------------------


def test_sync_endpoint_is_503_when_secret_unconfigured(client, monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "")
    response = client.post("/api/users/sync", json={"google_sub": "s"})
    assert response.status_code == 503


def test_sync_endpoint_rejects_a_wrong_secret(client, monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    response = client.post(
        "/api/users/sync",
        json={"google_sub": "s"},
        headers={"X-Aura-Internal-Secret": "wrong"},
    )
    assert response.status_code == 401


def test_me_adaptations_requires_the_user_header(client, monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    response = client.get(
        "/api/me/adaptations", headers={"X-Aura-Internal-Secret": "right"}
    )
    assert response.status_code == 400


def test_forwarded_user_id_is_ignored_without_the_secret(client, monkeypatch, sqlite_db):
    """The security property: a browser hitting the API directly with a
    forged X-Aura-User-Id must NOT get history written for that user."""
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("google-sub-7", "u@m.com", None)
    cache.set("cached-song", {"hook": "x"}, source_text="la la la")

    response = client.post(
        "/api/adapt",
        json={"text": "la la la"},
        headers={"X-Aura-User-Id": user["id"]},  # no secret
    )
    assert response.status_code == 200
    assert accounts.list_adaptations(user["id"]) == []


def test_cache_hit_with_valid_secret_records_history(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("google-sub-8", "u@m.com", None)
    cache.set("cached-song-2", {"hook": "y"}, source_text="do re mi")

    response = client.post(
        "/api/adapt",
        json={"text": "do re mi"},
        headers={"X-Aura-User-Id": user["id"], "X-Aura-Internal-Secret": "right"},
    )
    assert response.status_code == 200
    history = accounts.list_adaptations(user["id"])
    assert len(history) == 1


def test_history_entries_report_their_collection_memberships(sqlite_db):
    """The "add to collection" menu opens already knowing its own state,
    so the listing carries membership rather than the UI firing a request
    per row."""
    user = accounts.sync_user("mem-1", "u@m.com", None)
    shelf_a = accounts.create_collection(user["id"], "A")
    shelf_b = accounts.create_collection(user["id"], "B")
    accounts.record_adaptation(user["id"], "song-1", "Hindi")
    accounts.record_adaptation(user["id"], "song-2", "Korean")
    accounts.set_collection_membership(user["id"], shelf_a["id"], "song-1", True)
    accounts.set_collection_membership(user["id"], shelf_b["id"], "song-1", True)

    by_id = {e["resultId"]: e for e in accounts.list_adaptations(user["id"])}
    assert sorted(by_id["song-1"]["collectionIds"]) == sorted(
        [shelf_a["id"], shelf_b["id"]]
    )
    assert by_id["song-2"]["collectionIds"] == []


def test_membership_ids_do_not_leak_across_users(sqlite_db):
    """Two users, same song text adapted separately: each sees only their
    own collection ids on their own history row."""
    a = accounts.sync_user("mem-a", "a@m.com", None)
    b = accounts.sync_user("mem-b", "b@m.com", None)
    a_shelf = accounts.create_collection(a["id"], "A's shelf")
    accounts.record_adaptation(a["id"], "shared-song", "Hindi")
    accounts.record_adaptation(b["id"], "shared-song", "Hindi")
    accounts.set_collection_membership(a["id"], a_shelf["id"], "shared-song", True)

    assert accounts.list_adaptations(a["id"])[0]["collectionIds"] == [a_shelf["id"]]
    assert accounts.list_adaptations(b["id"])[0]["collectionIds"] == []


# ---------------------------------------------------------------------------
# Saving a result you didn't adapt (the shared-link case on /s/<id>)
# ---------------------------------------------------------------------------


def test_save_adaptation_creates_history_for_someone_elses_link(sqlite_db):
    """B opens A's shared link and stars it. B had no history row for
    that song; saving creates one so favorites/collections have something
    to attach to."""
    a = accounts.sync_user("save-a", "a@m.com", None)
    b = accounts.sync_user("save-b", "b@m.com", None)
    cache.set(
        "shared-result",
        {"hook": "A hook.", "sourceLanguage": "Hindi", "targetLanguage": "English"},
        source_text="lyrics",
    )
    accounts.record_adaptation(a["id"], "shared-result", "Hindi")

    assert accounts.get_adaptation(b["id"], "shared-result") is None
    assert accounts.save_adaptation(b["id"], "shared-result") is True

    entry = accounts.get_adaptation(b["id"], "shared-result")
    assert entry is not None
    assert entry["hook"] == "A hook."
    assert entry["isFavorite"] is False
    # A's row is a separate row, untouched.
    assert len(accounts.list_adaptations(a["id"])) == 1


def test_save_adaptation_is_idempotent(sqlite_db):
    user = accounts.sync_user("save-c", "u@m.com", None)
    cache.set("some-result", {"hook": "H"}, source_text="lyrics")
    assert accounts.save_adaptation(user["id"], "some-result") is True
    assert accounts.save_adaptation(user["id"], "some-result") is True
    assert len(accounts.list_adaptations(user["id"])) == 1


def test_cannot_save_a_result_that_was_never_computed(sqlite_db):
    """Otherwise this would be a way to fill the history table with rows
    pointing at ids that don't exist."""
    user = accounts.sync_user("save-d", "u@m.com", None)
    assert accounts.save_adaptation(user["id"], "never-existed") is False
    assert accounts.list_adaptations(user["id"]) == []


def test_get_adaptation_reports_favorite_and_collection_state(sqlite_db):
    user = accounts.sync_user("save-e", "u@m.com", None)
    cache.set("r1", {"hook": "H"}, source_text="lyrics")
    accounts.record_adaptation(user["id"], "r1", "Hindi")
    shelf = accounts.create_collection(user["id"], "Shelf")
    accounts.set_favorite(user["id"], "r1", True)
    accounts.set_collection_membership(user["id"], shelf["id"], "r1", True)

    entry = accounts.get_adaptation(user["id"], "r1")
    assert entry["isFavorite"] is True
    assert entry["collectionIds"] == [shelf["id"]]


def test_get_adaptation_does_not_leak_another_users_row(sqlite_db):
    a = accounts.sync_user("save-f", "a@m.com", None)
    b = accounts.sync_user("save-g", "b@m.com", None)
    cache.set("r2", {"hook": "H"}, source_text="lyrics")
    accounts.record_adaptation(a["id"], "r2", "Hindi")
    assert accounts.get_adaptation(b["id"], "r2") is None


def test_save_endpoint_404s_for_an_unknown_result(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("save-h", "u@m.com", None)
    response = client.post(
        "/api/me/adaptations/nope/save",
        headers={"X-Aura-User-Id": user["id"], "X-Aura-Internal-Secret": "right"},
    )
    assert response.status_code == 404


def test_save_then_favorite_round_trip_via_endpoints(client, monkeypatch, sqlite_db):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "right")
    user = accounts.sync_user("save-i", "u@m.com", None)
    cache.set("r3", {"hook": "H"}, source_text="lyrics")
    headers = {"X-Aura-User-Id": user["id"], "X-Aura-Internal-Secret": "right"}

    assert client.get("/api/me/adaptations/r3", headers=headers).json()["saved"] is False
    assert client.post("/api/me/adaptations/r3/save", headers=headers).status_code == 200
    assert (
        client.post(
            "/api/me/adaptations/r3/favorite", json={"is_favorite": True}, headers=headers
        ).status_code
        == 200
    )
    body = client.get("/api/me/adaptations/r3", headers=headers).json()
    assert body["saved"] is True
    assert body["adaptation"]["isFavorite"] is True


def test_no_database_means_save_declines(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert accounts.save_adaptation("u", "r") is False
    assert accounts.get_adaptation("u", "r") is None
