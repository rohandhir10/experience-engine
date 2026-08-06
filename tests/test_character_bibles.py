"""server/character_bibles.py against a real (sqlite file) database — the
persistence half of cross-chapter character voice memory. See
tests/test_comics_adapt.py for merge_character_bible/character_bible_updates
(the pure, engine-side half) and tests/test_server.py's bible-wiring tests
for how _run_comics_adaptation calls into this module.
"""
from __future__ import annotations

import pytest

import server.db as db
from server import character_bibles


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/character_bibles_test.db"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)
    db.create_all()
    yield url
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)


def _make_user() -> str:
    from server import accounts

    return accounts.sync_user("google-sub-1", "a@b.com", "A")["id"]


def test_get_bible_is_empty_for_a_series_never_seen(sqlite_db):
    user_id = _make_user()
    assert character_bibles.get_bible(user_id, "Some Series") == {}


def test_save_then_get_round_trips_a_character(sqlite_db):
    user_id = _make_user()
    character_bibles.save_bible(
        user_id, "Solo Leveling",
        {
            "guard captain": {
                "name": "Guard Captain",
                "voice_description": "Terse, deferential.",
                "honorific_register": "formal",
                "relationships": ["reports to the Princess"],
            }
        },
    )

    bible = character_bibles.get_bible(user_id, "Solo Leveling")

    assert bible == {
        "guard captain": {
            "voice_description": "Terse, deferential.",
            "honorific_register": "formal",
            "relationships": ["reports to the Princess"],
        }
    }


def test_get_bible_matches_series_name_case_insensitively(sqlite_db):
    user_id = _make_user()
    character_bibles.save_bible(
        user_id, "Solo Leveling",
        {"guard captain": {"name": "Guard Captain", "voice_description": "x", "honorific_register": "x"}},
    )

    assert character_bibles.get_bible(user_id, "  SOLO LEVELING  ") != {}


def test_save_bible_upserts_an_existing_character_rather_than_duplicating(sqlite_db):
    user_id = _make_user()
    character_bibles.save_bible(
        user_id, "Solo Leveling",
        {"guard captain": {"name": "Guard Captain", "voice_description": "v1", "honorific_register": "formal"}},
    )
    character_bibles.save_bible(
        user_id, "Solo Leveling",
        {"guard captain": {"name": "Guard Captain", "voice_description": "v2 (updated)", "honorific_register": "casual"}},
    )

    bible = character_bibles.get_bible(user_id, "Solo Leveling")

    assert len(bible) == 1
    assert bible["guard captain"]["voice_description"] == "v2 (updated)"
    assert bible["guard captain"]["honorific_register"] == "casual"


def test_save_bible_keeps_two_series_for_the_same_user_separate(sqlite_db):
    user_id = _make_user()
    character_bibles.save_bible(
        user_id, "Series A",
        {"hero": {"name": "Hero", "voice_description": "series A hero", "honorific_register": "x"}},
    )
    character_bibles.save_bible(
        user_id, "Series B",
        {"hero": {"name": "Hero", "voice_description": "series B hero", "honorific_register": "x"}},
    )

    assert character_bibles.get_bible(user_id, "Series A")["hero"]["voice_description"] == "series A hero"
    assert character_bibles.get_bible(user_id, "Series B")["hero"]["voice_description"] == "series B hero"


def test_save_bible_keeps_two_users_own_series_of_the_same_name_separate(sqlite_db):
    from server import accounts

    user_a = _make_user()
    user_b = accounts.sync_user("google-sub-2", "b@c.com", "B")["id"]

    character_bibles.save_bible(
        user_a, "Solo Leveling",
        {"hero": {"name": "Hero", "voice_description": "user A's take", "honorific_register": "x"}},
    )
    character_bibles.save_bible(
        user_b, "Solo Leveling",
        {"hero": {"name": "Hero", "voice_description": "user B's take", "honorific_register": "x"}},
    )

    assert character_bibles.get_bible(user_a, "Solo Leveling")["hero"]["voice_description"] == "user A's take"
    assert character_bibles.get_bible(user_b, "Solo Leveling")["hero"]["voice_description"] == "user B's take"


def test_save_bible_adds_a_new_character_without_disturbing_an_existing_one(sqlite_db):
    user_id = _make_user()
    character_bibles.save_bible(
        user_id, "Solo Leveling",
        {"hero": {"name": "Hero", "voice_description": "hero voice", "honorific_register": "x"}},
    )
    character_bibles.save_bible(
        user_id, "Solo Leveling",
        {"villain": {"name": "Villain", "voice_description": "villain voice", "honorific_register": "x"}},
    )

    bible = character_bibles.get_bible(user_id, "Solo Leveling")

    assert set(bible.keys()) == {"hero", "villain"}
    assert bible["hero"]["voice_description"] == "hero voice"


def test_get_bible_is_empty_without_a_database_configured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert character_bibles.get_bible("some-user", "Some Series") == {}


def test_save_bible_is_a_noop_without_a_database_configured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Must not raise even though no database is configured at all.
    character_bibles.save_bible(
        "some-user", "Some Series",
        {"hero": {"name": "Hero", "voice_description": "x", "honorific_register": "x"}},
    )


def test_get_bible_is_empty_for_a_blank_series_name(sqlite_db):
    user_id = _make_user()
    assert character_bibles.get_bible(user_id, "   ") == {}


def test_save_bible_is_a_noop_for_a_blank_series_name(sqlite_db):
    user_id = _make_user()
    character_bibles.save_bible(
        user_id, "   ",
        {"hero": {"name": "Hero", "voice_description": "x", "honorific_register": "x"}},
    )
    assert character_bibles.get_bible(user_id, "   ") == {}


def test_save_bible_is_a_noop_for_empty_updates(sqlite_db):
    user_id = _make_user()
    character_bibles.save_bible(user_id, "Solo Leveling", {})
    assert character_bibles.get_bible(user_id, "Solo Leveling") == {}
