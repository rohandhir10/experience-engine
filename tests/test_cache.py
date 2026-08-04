"""server/cache.py covers two backends: file-based (no DATABASE_URL, the
local-dev/test default) and Postgres-backed (DATABASE_URL set). The
DB-backed tests monkeypatch server.db's engine to sqlite in-memory rather
than requiring a real Postgres — cache.py doesn't use any Postgres-only
feature, so this exercises the real code path.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server import cache, db
from server import db_models  # noqa: F401 - registers models on Base.metadata


def test_fuzzy_key_ignores_case_punctuation_and_whitespace():
    a = cache.fuzzy_key("Hello,   World!\nHow are you?")
    b = cache.fuzzy_key("hello world how are you")
    assert a == b


def test_file_backend_roundtrip(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "cache")

    result_id = cache.content_id("line one\nline two")
    assert cache.get(result_id) is None

    cache.set(result_id, {"hook": "test"}, source_text="line one\nline two")
    assert cache.get(result_id) == {"hook": "test"}


def test_file_backend_never_reports_a_fuzzy_match(monkeypatch, tmp_path):
    """Cross-user fuzzy reuse doesn't apply locally — an exact hash
    already covers every real repeat when there's one user."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "cache")

    result_id = cache.content_id("line one\nline two")
    cache.set(result_id, {"hook": "test"}, source_text="line one\nline two")

    assert cache.find_similar("line one\nline two") is None


@pytest.fixture
def sqlite_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    db.Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, expire_on_commit=False)

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")  # only need it to be truthy
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    monkeypatch.setattr(db, "get_sessionmaker", lambda: session_local)
    return engine


def test_db_backend_roundtrip(sqlite_db):
    result_id = cache.content_id("line one\nline two")
    assert cache.get(result_id) is None

    cache.set(result_id, {"hook": "test"}, source_text="line one\nline two")
    assert cache.get(result_id) == {"hook": "test"}


def test_db_backend_finds_a_near_identical_paste(sqlite_db):
    original_id = cache.content_id("Hello, World!\nHow are you?")
    cache.set(original_id, {"hook": "original"}, source_text="Hello, World!\nHow are you?")

    # Same words, different punctuation/casing/line breaks - not an exact
    # hash match, but should be recognized as the same song.
    match = cache.find_similar("hello world.\nhow are you")
    assert match is not None
    matched_id, matched_result, similarity = match
    assert matched_id == original_id
    assert matched_result == {"hook": "original"}
    assert similarity >= cache.SIMILARITY_THRESHOLD


def test_db_backend_does_not_match_a_different_song(sqlite_db):
    original_id = cache.content_id("Hello, World!\nHow are you?")
    cache.set(original_id, {"hook": "original"}, source_text="Hello, World!\nHow are you?")

    assert cache.find_similar("A completely different song about the ocean at night") is None


def test_content_id_differs_by_source_language_once_declared():
    unspecified = cache.content_id("line one", target_language="Korean")
    hindi_source = cache.content_id("line one", target_language="Korean", source_language="Hindi")
    japanese_source = cache.content_id(
        "line one", target_language="Korean", source_language="Japanese"
    )
    assert len({unspecified, hindi_source, japanese_source}) == 3


def test_content_id_unaffected_by_source_language_when_english_target_and_unspecified_source():
    """Every id computed before source_language existed must still resolve
    the same way - "English" target + "unspecified" source is the default
    for both fields, so it must not perturb the hash at all."""
    assert cache.content_id("line one") == cache.content_id(
        "line one", target_language="English", source_language="unspecified"
    )


def test_content_id_changes_when_cache_version_bumps(monkeypatch):
    """The whole point: a prompt/pipeline fix should make previously
    cached text miss the cache and regenerate, without needing a manual
    per-song clear."""
    monkeypatch.setattr(cache, "CACHE_VERSION", "1")
    v1 = cache.content_id("line one\nline two")
    monkeypatch.setattr(cache, "CACHE_VERSION", "2")
    v2 = cache.content_id("line one\nline two")
    assert v1 != v2


def test_db_backend_find_similar_ignores_a_stale_cache_version(sqlite_db, monkeypatch):
    """A row written under an old CACHE_VERSION must not be resurfaced by
    find_similar's fuzzy scan after a version bump - that scan doesn't go
    through content_id() at all, so it's the one path that could quietly
    keep serving pre-fix output forever without this check."""
    monkeypatch.setattr(cache, "CACHE_VERSION", "1")
    result_id = cache.content_id("Hello, World!\nHow are you?")
    cache.set(result_id, {"hook": "stale"}, source_text="Hello, World!\nHow are you?")

    monkeypatch.setattr(cache, "CACHE_VERSION", "2")
    assert cache.find_similar("hello world.\nhow are you") is None


def test_db_backend_find_similar_still_matches_the_current_version(sqlite_db):
    result_id = cache.content_id("Hello, World!\nHow are you?")
    cache.set(result_id, {"hook": "fresh"}, source_text="Hello, World!\nHow are you?")

    match = cache.find_similar("hello world.\nhow are you")
    assert match is not None
    assert match[1] == {"hook": "fresh"}


def test_db_backend_find_similar_respects_source_language(sqlite_db):
    """Hindi -> Korean and Japanese -> Korean of near-identical text must
    not be treated as the same cached result."""
    hindi_id = cache.content_id("Hello World", target_language="Korean", source_language="Hindi")
    cache.set(
        hindi_id,
        {"hook": "from hindi"},
        source_text="Hello World",
        target_language="Korean",
        source_language="Hindi",
    )

    match = cache.find_similar(
        "hello world", target_language="Korean", source_language="Japanese"
    )
    assert match is None


def test_comics_content_id_differs_by_panel_order():
    """A chapter's panels adapted in one order vs. another are, correctly,
    different results - reading order matters for context, not just
    which text strings appear."""
    forward = cache.comics_content_id(
        ["first panel", "second panel"], target_language="English", source_language="Korean"
    )
    reversed_ = cache.comics_content_id(
        ["second panel", "first panel"], target_language="English", source_language="Korean"
    )
    assert forward != reversed_


def test_comics_content_id_differs_by_language_pair():
    korean_source = cache.comics_content_id(
        ["hello"], target_language="English", source_language="Korean"
    )
    japanese_source = cache.comics_content_id(
        ["hello"], target_language="English", source_language="Japanese"
    )
    assert korean_source != japanese_source


def test_comics_content_id_is_deterministic():
    first = cache.comics_content_id(
        ["panel one", "panel two"], target_language="English", source_language="Korean"
    )
    second = cache.comics_content_id(
        ["panel one", "panel two"], target_language="English", source_language="Korean"
    )
    assert first == second


def test_comics_content_id_never_collides_with_a_song_content_id():
    """Both ids ultimately live in the same flat cache.get()/set() id
    space (server/cache.py has no separate table per medium) - the
    literal "comics" tag folded into comics_content_id's hash is what
    guarantees a chapter and a song can never collide even if their
    normalized text happened to be identical."""
    same_text = "hello world"
    song_id = cache.content_id(same_text, target_language="English", source_language="Korean")
    comics_id = cache.comics_content_id(
        [same_text], target_language="English", source_language="Korean"
    )
    assert song_id != comics_id
