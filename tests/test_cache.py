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
