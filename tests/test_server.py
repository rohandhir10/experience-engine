"""Tests for server/main.py's request handling. No real HTTP server, no
real LLM calls — route functions are plain Python functions, called
directly with monkeypatched dependencies. server/main.py had no test
coverage before this; these are the first.
"""
from __future__ import annotations

import pytest

import server.main as main


class _FakeRequest:
    """Stands in for FastAPI's Request — only what _client_ip reads."""

    def __init__(self):
        self.headers: dict[str, str] = {}
        self.client = None


class _FakeClient:
    call_log: list = []

    def complete_json(self, *args, **kwargs):
        raise AssertionError("run_engine is monkeypatched; the real client should never be called")


class _FakeEngineResult:
    def __init__(self, sections=None, source_sections=None):
        self._sections = sections or []
        self._source_sections = source_sections or []

    def to_dict(self) -> dict:
        return {"sections": self._sections, "source_sections": self._source_sections}


@pytest.fixture(autouse=True)
def _isolated_cache(monkeypatch, tmp_path):
    """Every test gets its own empty cache dir — no shared state, no
    writing into the real repo's server/.cache during tests.
    """
    monkeypatch.setattr(main.cache, "CACHE_DIR", tmp_path / "cache")


@pytest.fixture(autouse=True)
def _no_quota_limit(monkeypatch):
    monkeypatch.setattr(main, "DAILY_LIMIT", 0)


def _patch_engine(monkeypatch, engine_result, captured: dict):
    def fake_run_engine(song, client=None, room_version="v1", apply_corrective_pass=False):
        captured["apply_corrective_pass"] = apply_corrective_pass
        captured["room_version"] = room_version
        return engine_result

    def fake_to_experience_result(client, result, result_id, explain_why_client=None):
        captured["explain_why_client_given"] = explain_why_client is not None
        return {
            "id": result_id,
            "hook": "test hook",
            "sourceLanguage": "unspecified",
            "sections": [],
            "original": [],
        }

    def fake_create_default_client(model=None):
        captured.setdefault("requested_models", []).append(model)
        return _FakeClient()

    monkeypatch.setattr(main, "run_engine", fake_run_engine)
    monkeypatch.setattr(main, "to_experience_result", fake_to_experience_result)
    monkeypatch.setattr(main, "create_default_client", fake_create_default_client)


def test_adapt_enables_the_corrective_pass(monkeypatch):
    """Wiring verify.py into the web path means more than logging — the
    already-built Phase 2 corrective pass should actually run, not just
    verify-then-shrug.
    """
    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)

    request = main.AdaptRequest(text="line one\nline two")
    main.adapt(request, _FakeRequest())

    assert captured["apply_corrective_pass"] is True


def test_adapt_requests_a_cheaper_model_for_explain_why(monkeypatch):
    """explain_why is presentation text, not adaptation reasoning — the
    one call this request makes on a deliberately cheaper model
    (engine/config.py's EXPLAIN_WHY_MODEL), via a separate client so its
    cost is still measured, just not on the main model.
    """
    from engine import config

    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)

    request = main.AdaptRequest(text="line one\nline two")
    main.adapt(request, _FakeRequest())

    # First call: the main engine client (no override). Second: explain_why's.
    assert captured["requested_models"] == [None, config.EXPLAIN_WHY_MODEL]
    assert captured["explain_why_client_given"] is True


def test_adapt_logs_clean_verification_with_no_findings(monkeypatch, caplog):
    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)

    with caplog.at_level("INFO", logger="aura.server"):
        request = main.AdaptRequest(text="line one\nline two")
        main.adapt(request, _FakeRequest())

    verify_lines = [r.message for r in caplog.records if "verify errors=" in r.message]
    assert len(verify_lines) == 1
    assert "errors=0" in verify_lines[0]


def test_adapt_rejects_an_unsupported_target_language(monkeypatch):
    request = main.AdaptRequest(text="line one\nline two", target_language="French")
    with pytest.raises(main.HTTPException) as exc_info:
        main.adapt(request, _FakeRequest())
    assert exc_info.value.status_code == 400
    assert "French" in exc_info.value.detail


def test_adapt_rejects_non_english_source_for_a_reverse_direction(monkeypatch):
    """English -> Hindi expects an English source - a mostly-Devanagari
    paste is a strong signal this is actually the *other* direction
    (Hindi -> English), which this target_language was never built for."""
    request = main.AdaptRequest(
        text="तुम लोगो की, इस दुनिया में हर कदम पे इंसा गलत",
        target_language="Hindi",
    )
    with pytest.raises(main.HTTPException) as exc_info:
        main.adapt(request, _FakeRequest())
    assert exc_info.value.status_code == 400
    assert "English" in exc_info.value.detail


def test_adapt_accepts_english_source_for_a_reverse_direction(monkeypatch):
    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)

    request = main.AdaptRequest(text="line one\nline two", target_language="Hindi")
    result = main.adapt(request, _FakeRequest())

    assert result["id"]  # ran the engine and returned a result, not rejected


def test_adapt_threads_target_language_into_the_song_input(monkeypatch):
    captured: dict = {}

    def fake_run_engine(song, client=None, room_version="v1", apply_corrective_pass=False):
        captured["target_language"] = song.target_language
        return _FakeEngineResult()

    def fake_to_experience_result(client, result, result_id, explain_why_client=None):
        return {"id": result_id, "hook": "h", "sourceLanguage": "unspecified", "sections": [], "original": []}

    monkeypatch.setattr(main, "run_engine", fake_run_engine)
    monkeypatch.setattr(main, "to_experience_result", fake_to_experience_result)
    monkeypatch.setattr(main, "create_default_client", lambda model=None: _FakeClient())

    request = main.AdaptRequest(text="line one\nline two", target_language="Korean")
    main.adapt(request, _FakeRequest())

    assert captured["target_language"] == "Korean"


def test_same_text_different_target_languages_do_not_collide_in_the_cache(monkeypatch):
    """Without this, an English source submitted for both Hindi and Korean
    would produce the same cache id and the second request would silently
    be served the first's (wrong-language) result."""
    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)

    hindi_id = main.cache.content_id("line one\nline two", target_language="Hindi")
    korean_id = main.cache.content_id("line one\nline two", target_language="Korean")
    assert hindi_id != korean_id

    request = main.AdaptRequest(text="line one\nline two", target_language="Hindi")
    result = main.adapt(request, _FakeRequest())
    assert result["id"] == hindi_id


def test_adapt_logs_a_warning_for_unresolved_verify_errors(monkeypatch, caplog):
    """A section shipped with a real, unaudited change (empty deviation
    ledger despite a rewritten line) — the exact Law 1 violation
    verify.py exists to catch — must show up in production logs, not
    silently pass through.
    """
    anchor = "I keep the drawer locked and I never open it"
    rewritten = "The drawer stays shut and I never touch it"
    section = {
        "section": "verse_1",
        "candidates": [
            {"id": "a1", "agent": "translator", "text": anchor, "round": "generation"},
            {
                "id": "c1",
                "agent": "creative_adapter",
                "text": rewritten,
                "round": "generation",
                "philosophy": "maximum_fidelity",
            },
        ],
        "routing_signals": {},
        "ruling": {
            "section": "verse_1",
            "final_line": rewritten,
            "priority_tradeoffs_made": "test",
            "deviations": [],  # empty despite a real change — the bug
            "invention_penalty": 0.0,
        },
    }
    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(sections=[section]), captured)

    with caplog.at_level("INFO", logger="aura.server"):
        request = main.AdaptRequest(text="line one\nline two")
        main.adapt(request, _FakeRequest())

    warning_lines = [
        r.message
        for r in caplog.records
        if r.levelname == "WARNING" and "unresolved verify.py error" in r.message
    ]
    assert len(warning_lines) == 1
    assert "Law 1" in warning_lines[0]

    verify_lines = [r.message for r in caplog.records if "verify errors=" in r.message]
    assert "errors=1" in verify_lines[0]


def _patch_engine_with_two_sections(monkeypatch, captured: dict):
    """Like _patch_engine, but returns two sections in the experience
    result — needed to test youtube timing attachment, which only makes
    sense against more than a single, always-empty section list."""

    def fake_run_engine(song, client=None, room_version="v1", apply_corrective_pass=False):
        return _FakeEngineResult()

    def fake_to_experience_result(client, result, result_id, explain_why_client=None):
        return {
            "id": result_id,
            "hook": "test hook",
            "sourceLanguage": "unspecified",
            "sections": [
                {"id": "section_1", "literal": "a", "aura": "a2", "why": "w1"},
                {"id": "section_2", "literal": "b", "aura": "b2", "why": "w2"},
            ],
            "original": [],
        }

    monkeypatch.setattr(main, "run_engine", fake_run_engine)
    monkeypatch.setattr(main, "to_experience_result", fake_to_experience_result)
    monkeypatch.setattr(main, "create_default_client", lambda model=None: _FakeClient())


def test_adapt_attaches_matching_youtube_timing(monkeypatch):
    captured: dict = {}
    _patch_engine_with_two_sections(monkeypatch, captured)

    request = main.AdaptRequest(
        text="line one\n\nline two",
        youtube_video_id="dQw4w9WgXcQ",
        youtube_section_timings=[
            main.YoutubeSectionTiming(start=0.0, end=4.5),
            main.YoutubeSectionTiming(start=9.5, end=14.0),
        ],
    )
    result = main.adapt(request, _FakeRequest())

    assert result["videoId"] == "dQw4w9WgXcQ"
    assert result["sections"][0]["startSeconds"] == 0.0
    assert result["sections"][0]["endSeconds"] == 4.5
    assert result["sections"][1]["startSeconds"] == 9.5


def test_adapt_discards_youtube_timing_on_section_count_mismatch(monkeypatch, caplog):
    """The user edited the reviewed draft and changed the number of
    sections - positional timing no longer means anything, so it must be
    dropped rather than mis-synced to the wrong lyric line."""
    captured: dict = {}
    _patch_engine_with_two_sections(monkeypatch, captured)

    request = main.AdaptRequest(
        text="line one\n\nline two",
        youtube_video_id="dQw4w9WgXcQ",
        youtube_section_timings=[main.YoutubeSectionTiming(start=0.0, end=4.5)],
    )
    with caplog.at_level("INFO", logger="aura.server"):
        result = main.adapt(request, _FakeRequest())

    assert "videoId" not in result
    assert "startSeconds" not in result["sections"][0]
    assert any("timing discarded" in r.message for r in caplog.records)


def test_youtube_draft_returns_build_web_draft_result(monkeypatch):
    def fake_build_web_draft(url, preferred_languages=None):
        return {
            "video_id": "dQw4w9WgXcQ",
            "source_language": "Hindi",
            "warning": "DRAFT - NOT REVIEWED.",
            "draft_text": "line one\n\nline two",
            "sections": [{"start": 0.0, "end": 2.0}, {"start": 10.0, "end": 12.0}],
        }

    monkeypatch.setattr(main.youtube_ingest, "build_web_draft", fake_build_web_draft)

    request = main.YoutubeDraftRequest(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    result = main.youtube_draft(request)

    assert result["video_id"] == "dQw4w9WgXcQ"
    assert result["draft_text"] == "line one\n\nline two"


def test_youtube_draft_reports_ingest_failure_as_a_400(monkeypatch):
    def fake_build_web_draft(url, preferred_languages=None):
        raise main.IngestError("Captions are disabled for this video.")

    monkeypatch.setattr(main.youtube_ingest, "build_web_draft", fake_build_web_draft)

    request = main.YoutubeDraftRequest(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    with pytest.raises(main.HTTPException) as exc_info:
        main.youtube_draft(request)

    assert exc_info.value.status_code == 400
    assert "Captions are disabled" in exc_info.value.detail
