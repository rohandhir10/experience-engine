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


def test_adapt_requires_an_explicit_source_language_for_a_non_english_target(monkeypatch):
    """target_language != English used to trust an unspecified source,
    guarded by a Latin-script heuristic that assumed the source must be
    English. That assumption broke once direct pairs (Hindi -> Korean)
    became possible, so an unspecified source is now rejected outright
    instead of guessed at."""
    request = main.AdaptRequest(text="line one\nline two", target_language="Hindi")
    with pytest.raises(main.HTTPException) as exc_info:
        main.adapt(request, _FakeRequest())
    assert exc_info.value.status_code == 400
    assert "source language" in exc_info.value.detail


def test_adapt_rejects_source_and_target_being_the_same_language(monkeypatch):
    request = main.AdaptRequest(
        text="line one\nline two", source_language="Hindi", target_language="Hindi"
    )
    with pytest.raises(main.HTTPException) as exc_info:
        main.adapt(request, _FakeRequest())
    assert exc_info.value.status_code == 400


def test_adapt_rejects_an_unsupported_source_language(monkeypatch):
    request = main.AdaptRequest(
        text="line one\nline two", source_language="French", target_language="Hindi"
    )
    with pytest.raises(main.HTTPException) as exc_info:
        main.adapt(request, _FakeRequest())
    assert exc_info.value.status_code == 400
    assert "French" in exc_info.value.detail


def test_adapt_accepts_english_source_for_a_reverse_direction(monkeypatch):
    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)

    request = main.AdaptRequest(
        text="line one\nline two", source_language="English", target_language="Hindi"
    )
    result = main.adapt(request, _FakeRequest())

    assert result["id"]  # ran the engine and returned a result, not rejected


def test_adapt_accepts_a_direct_non_english_pair(monkeypatch):
    """Hindi -> Korean: no English on either side. The whole point of
    opening the full matrix rather than a curated allow-list."""
    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)

    request = main.AdaptRequest(
        text="line one\nline two", source_language="Hindi", target_language="Korean"
    )
    result = main.adapt(request, _FakeRequest())

    assert result["id"]


def test_adapt_threads_source_and_target_language_into_the_song_input(monkeypatch):
    captured: dict = {}

    def fake_run_engine(song, client=None, room_version="v1", apply_corrective_pass=False):
        captured["source_language"] = song.source_language
        captured["target_language"] = song.target_language
        return _FakeEngineResult()

    def fake_to_experience_result(client, result, result_id, explain_why_client=None):
        return {"id": result_id, "hook": "h", "sourceLanguage": "unspecified", "sections": [], "original": []}

    monkeypatch.setattr(main, "run_engine", fake_run_engine)
    monkeypatch.setattr(main, "to_experience_result", fake_to_experience_result)
    monkeypatch.setattr(main, "create_default_client", lambda model=None: _FakeClient())

    request = main.AdaptRequest(
        text="line one\nline two", source_language="Japanese", target_language="Korean"
    )
    main.adapt(request, _FakeRequest())

    assert captured["source_language"] == "Japanese"
    assert captured["target_language"] == "Korean"


def test_same_text_different_target_languages_do_not_collide_in_the_cache(monkeypatch):
    """Without this, an English source submitted for both Hindi and Korean
    would produce the same cache id and the second request would silently
    be served the first's (wrong-language) result."""
    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)

    hindi_id = main.cache.content_id(
        "line one\nline two", target_language="Hindi", source_language="English"
    )
    korean_id = main.cache.content_id(
        "line one\nline two", target_language="Korean", source_language="English"
    )
    assert hindi_id != korean_id

    request = main.AdaptRequest(
        text="line one\nline two", source_language="English", target_language="Hindi"
    )
    result = main.adapt(request, _FakeRequest())
    assert result["id"] == hindi_id


def test_same_text_different_source_languages_do_not_collide_in_the_cache(monkeypatch):
    """Hindi -> Korean and Japanese -> Korean of the same (unlikely but
    possible) source text must not collide either - source_language has
    to be part of the id too, once it's an explicit, meaningful field."""
    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)

    hindi_source_id = main.cache.content_id(
        "line one\nline two", target_language="Korean", source_language="Hindi"
    )
    japanese_source_id = main.cache.content_id(
        "line one\nline two", target_language="Korean", source_language="Japanese"
    )
    assert hindi_source_id != japanese_source_id

    request = main.AdaptRequest(
        text="line one\nline two", source_language="Hindi", target_language="Korean"
    )
    result = main.adapt(request, _FakeRequest())
    assert result["id"] == hindi_source_id


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


def test_adapt_attaches_phoneme_repetition_similarity(monkeypatch):
    """The song-level Sim_pho correlation is computed by verify_result, not
    mapping.py's per-section shape - attach it separately onto the same
    response dict, straight from the report, not recomputed or guessed."""
    from engine.verify import VerificationReport

    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)
    monkeypatch.setattr(
        main, "verify_result", lambda *args, **kwargs: VerificationReport(phoneme_repetition_similarity=0.42)
    )

    result = main.adapt(main.AdaptRequest(text="line one\n\nline two"), _FakeRequest())

    assert result["phonemeRepetitionSimilarity"] == 0.42


def test_adapt_leaves_phoneme_repetition_similarity_none_when_unmeasured(monkeypatch):
    from engine.verify import VerificationReport

    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)
    monkeypatch.setattr(
        main, "verify_result", lambda *args, **kwargs: VerificationReport(phoneme_repetition_similarity=None)
    )

    result = main.adapt(main.AdaptRequest(text="line one\n\nline two"), _FakeRequest())

    assert result["phonemeRepetitionSimilarity"] is None


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


class _FakeUploadFile:
    """Stands in for FastAPI's UploadFile — only the `.file.read()` path
    server/main.py's comics_ocr_endpoint actually uses."""

    def __init__(self, data: bytes):
        self.file = _FakeSpooledFile(data)


class _FakeSpooledFile:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


def test_comics_ocr_endpoint_returns_extract_text_regions_result(monkeypatch):
    def fake_extract(image_bytes, language="English"):
        assert image_bytes == b"fake-image-bytes"
        assert language == "English"
        return {"regions": [], "full_text": "", "warning": None, "image_width": 10, "image_height": 10}

    monkeypatch.setattr(main.comics_ocr, "extract_text_regions", fake_extract)

    result = main.comics_ocr_endpoint(
        image=_FakeUploadFile(b"fake-image-bytes"), language="English"
    )

    assert result["image_width"] == 10


def test_comics_ocr_endpoint_reports_ocr_failure_as_a_400(monkeypatch):
    def fake_extract(image_bytes, language="English"):
        raise main.OcrError("Could not decode this image.")

    monkeypatch.setattr(main.comics_ocr, "extract_text_regions", fake_extract)

    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_ocr_endpoint(image=_FakeUploadFile(b"garbage"), language="English")

    assert exc_info.value.status_code == 400
    assert "Could not decode" in exc_info.value.detail


def test_comics_ocr_endpoint_rejects_an_oversized_image():
    oversized = b"x" * (main.MAX_IMAGE_BYTES + 1)
    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_ocr_endpoint(image=_FakeUploadFile(oversized), language="English")

    assert exc_info.value.status_code == 413


class _FakeRuling:
    def __init__(self, final_line, priority_tradeoffs_made="test tradeoff"):
        self.final_line = final_line
        self.priority_tradeoffs_made = priority_tradeoffs_made


class _FakeSectionResult:
    def __init__(self, section, final_line):
        self.section = section
        self.ruling = _FakeRuling(final_line)


def _fake_chapter_dna(**overrides):
    from engine.models import ChapterDNA

    defaults = dict(
        artistic_thesis="test thesis",
        genre_feel="drama",
        tone="tense",
        ongoing_plot_context="test context",
        characters=[],
    )
    defaults.update(overrides)
    return ChapterDNA(**defaults)


def _patch_comics_adapt(monkeypatch, dna=None):
    monkeypatch.setattr(main, "generate_chapter_dna", lambda chapter, client: dna or _fake_chapter_dna())
    monkeypatch.setattr(
        main,
        "adapt_chapter",
        lambda chapter, dna, client: [
            _FakeSectionResult(b.id, f"adapted {b.id}") for b in chapter.bubbles
        ],
    )
    monkeypatch.setattr(main, "_translator_text", lambda result: f"literal {result.section}")
    monkeypatch.setattr(
        main, "_explain_why", lambda client, thesis, literal, adapted, tradeoffs: "why text"
    )
    monkeypatch.setattr(main, "create_default_client", lambda: object())


def test_comics_adapt_endpoint_returns_chapter_dna_and_per_panel_results(monkeypatch):
    _patch_comics_adapt(monkeypatch, dna=_fake_chapter_dna(genre_feel="royal-court drama"))

    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[
            main.ComicsPanelText(id="panel-1", text="hello"),
            main.ComicsPanelText(id="panel-2", text="goodbye"),
        ],
    )
    result = main.comics_adapt_endpoint(request, _FakeRequest())

    assert result["chapter_dna"]["genre_feel"] == "royal-court drama"
    assert result["panels"] == [
        {"id": "panel-1", "literal": "literal panel-1", "adapted_text": "adapted panel-1", "why": "why text"},
        {"id": "panel-2", "literal": "literal panel-2", "adapted_text": "adapted panel-2", "why": "why text"},
    ]


def test_comics_adapt_endpoint_threads_voice_into_bubble_input(monkeypatch):
    _patch_comics_adapt(monkeypatch)
    captured_chapters = []

    def capturing_adapt_chapter(chapter, dna, client):
        captured_chapters.append(chapter)
        return [_FakeSectionResult(b.id, f"adapted {b.id}") for b in chapter.bubbles]

    monkeypatch.setattr(main, "adapt_chapter", capturing_adapt_chapter)

    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[
            main.ComicsPanelText(id="panel-1", text="hello", voice="Guard Captain"),
            main.ComicsPanelText(id="panel-2", text="goodbye"),
        ],
    )
    main.comics_adapt_endpoint(request, _FakeRequest())

    bubbles = {b.id: b for b in captured_chapters[0].bubbles}
    assert bubbles["panel-1"].voice == "Guard Captain"
    assert bubbles["panel-2"].voice is None


def test_comics_adapt_endpoint_skips_panels_with_only_whitespace_text(monkeypatch):
    _patch_comics_adapt(monkeypatch)

    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[
            main.ComicsPanelText(id="panel-1", text="hello"),
            main.ComicsPanelText(id="panel-2", text="   "),
        ],
    )
    result = main.comics_adapt_endpoint(request, _FakeRequest())

    assert [p["id"] for p in result["panels"]] == ["panel-1"]


def test_comics_adapt_endpoint_rejects_all_empty_panels():
    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[main.ComicsPanelText(id="panel-1", text="   ")],
    )
    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_adapt_endpoint(request, _FakeRequest())

    assert exc_info.value.status_code == 400


def test_comics_adapt_endpoint_returns_a_persisted_id(monkeypatch):
    """The first real persistence comics has had: a real, content-addressed
    id (server/cache.py::comics_content_id), the same get()/set() storage
    /api/adapt uses - not just a per-request response with nothing to
    point a share link at afterward."""
    _patch_comics_adapt(monkeypatch)

    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[main.ComicsPanelText(id="panel-1", text="hello")],
    )
    result = main.comics_adapt_endpoint(request, _FakeRequest())

    expected_id = main.cache.comics_content_id(
        ["hello"], target_language="English", source_language="Korean"
    )
    assert result["id"] == expected_id


def test_comics_adapt_endpoint_is_a_cache_hit_on_a_repeat_submission(monkeypatch):
    """A second submission of the identical chapter must not re-run the
    engine at all - mirrors /api/adapt's cache-hit path."""
    _patch_comics_adapt(monkeypatch)
    call_count = {"n": 0}

    def counting_generate_chapter_dna(chapter, client):
        call_count["n"] += 1
        return _fake_chapter_dna()

    monkeypatch.setattr(main, "generate_chapter_dna", counting_generate_chapter_dna)

    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[main.ComicsPanelText(id="panel-1", text="hello")],
    )
    first = main.comics_adapt_endpoint(request, _FakeRequest())
    second = main.comics_adapt_endpoint(request, _FakeRequest())

    assert call_count["n"] == 1
    assert first["id"] == second["id"]
    assert first["panels"] == second["panels"]


def test_comics_adapt_endpoint_records_history_for_a_signed_in_user(monkeypatch):
    _patch_comics_adapt(monkeypatch)
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "test-secret")
    captured = {}

    def fake_record_adaptation(user_id, result_id, source_language, medium="music"):
        captured["user_id"] = user_id
        captured["medium"] = medium

    monkeypatch.setattr(main.accounts, "record_adaptation", fake_record_adaptation)

    authed_request = _FakeRequest()
    authed_request.headers = {
        "x-aura-user-id": "user-42",
        "x-aura-internal-secret": "test-secret",
    }

    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[main.ComicsPanelText(id="panel-1", text="hello")],
    )
    main.comics_adapt_endpoint(request, authed_request)

    assert captured == {"user_id": "user-42", "medium": "webtoons"}


def test_get_comics_adapt_returns_a_previously_persisted_result(monkeypatch):
    _patch_comics_adapt(monkeypatch)

    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[main.ComicsPanelText(id="panel-1", text="hello")],
    )
    posted = main.comics_adapt_endpoint(request, _FakeRequest())

    fetched = main.get_comics_adapt(posted["id"])
    assert fetched == posted


def test_get_comics_adapt_404s_for_an_unknown_id():
    with pytest.raises(main.HTTPException) as exc_info:
        main.get_comics_adapt("no-such-id")
    assert exc_info.value.status_code == 404


def test_comics_adapt_endpoint_reports_engine_failure_as_a_502(monkeypatch):
    monkeypatch.setattr(main, "create_default_client", lambda: object())

    def raise_llm_error(chapter, client):
        raise main.LLMError("provider is down")

    monkeypatch.setattr(main, "generate_chapter_dna", raise_llm_error)

    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[main.ComicsPanelText(id="panel-1", text="hello")],
    )
    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_adapt_endpoint(request, _FakeRequest())

    assert exc_info.value.status_code == 502
