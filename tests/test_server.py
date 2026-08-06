"""Tests for server/main.py's request handling. No real HTTP server, no
real LLM calls — route functions are plain Python functions, called
directly with monkeypatched dependencies. server/main.py had no test
coverage before this; these are the first.
"""
from __future__ import annotations

import json

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
    monkeypatch.setattr(main, "MONTHLY_LIMIT", 0)


@pytest.fixture(autouse=True)
def _unlimited_credits(monkeypatch):
    """This file has no real database (see tests/test_credits.py and
    test_v1_api.py for that), but plenty of tests here pass a synthetic
    user_id to exercise history-recording/auth logic that has nothing to
    do with credit sufficiency - without this, every one of them would
    incidentally 402 (credits.deduct returns False with no DATABASE_URL
    at all). Tests that actually exercise the credit gate itself
    override this per-test."""
    monkeypatch.setattr(main.credits, "deduct", lambda *a, **k: True)
    monkeypatch.setattr(main.credits, "refund", lambda *a, **k: None)


def _patch_engine(monkeypatch, engine_result, captured: dict):
    def fake_run_engine(song, client=None, room_version="v1", apply_corrective_pass=False, on_stage=None, on_section_done=None, deadline=None):
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

    with caplog.at_level("INFO", logger="castia.server"):
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

    def fake_run_engine(song, client=None, room_version="v1", apply_corrective_pass=False, on_stage=None, on_section_done=None, deadline=None):
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

    with caplog.at_level("INFO", logger="castia.server"):
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

    def fake_run_engine(song, client=None, room_version="v1", apply_corrective_pass=False, on_stage=None, on_section_done=None, deadline=None):
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


def _authed_request(user_id: str = "user-1", secret: str = "test-secret") -> _FakeRequest:
    request = _FakeRequest()
    request.headers = {"x-castia-user-id": user_id, "x-castia-internal-secret": secret}
    return request


def test_adapt_deducts_credits_per_section_for_a_signed_in_user(monkeypatch):
    """CREDITS_PER_SECTION * the actual section count, not a flat
    per-submission price - a 2-section song must cost twice a 1-section
    one, matching web/app/pricing/page.tsx's SONG_CREDITS derivation."""
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "test-secret")
    captured: dict = {}
    _patch_engine_with_two_sections(monkeypatch, captured)
    deduct_calls = []
    monkeypatch.setattr(
        main.credits,
        "deduct",
        lambda user_id, amount, reason, reference=None: deduct_calls.append(
            (user_id, amount, reason)
        )
        or True,
    )

    request = main.AdaptRequest(text="line one\n\nline two")
    main.adapt(request, _authed_request("user-1"))

    assert deduct_calls == [("user-1", main.CREDITS_PER_SECTION * 2, "adaptation")]


def test_adapt_returns_402_when_credits_are_insufficient(monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "test-secret")
    monkeypatch.setattr(main.credits, "deduct", lambda *a, **k: False)

    request = main.AdaptRequest(text="line one\nline two")
    with pytest.raises(main.HTTPException) as exc_info:
        main.adapt(request, _authed_request("user-1"))

    assert exc_info.value.status_code == 402


def test_adapt_refunds_credits_when_the_engine_fails(monkeypatch):
    """Credits are debited before the engine runs (so a user can't dodge
    the charge by deleting their account mid-run) - a failure after that
    point must refund the exact amount debited, not leave the user
    charged for a run that produced nothing."""
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "test-secret")

    def raise_llm_error(song, client=None, room_version="v1", apply_corrective_pass=False, on_stage=None, on_section_done=None, deadline=None):
        raise main.LLMError("provider is down")

    monkeypatch.setattr(main, "run_engine", raise_llm_error)
    monkeypatch.setattr(main, "create_default_client", lambda model=None: _FakeClient())
    monkeypatch.setattr(main.credits, "deduct", lambda *a, **k: True)
    refund_calls = []
    monkeypatch.setattr(
        main.credits,
        "refund",
        lambda user_id, amount, reference=None: refund_calls.append((user_id, amount)),
    )

    request = main.AdaptRequest(text="line one\nline two")
    with pytest.raises(main.HTTPException):
        main.adapt(request, _authed_request("user-1"))

    assert refund_calls == [("user-1", main.CREDITS_PER_SECTION * 1)]


def test_adapt_does_not_touch_credits_for_an_anonymous_request(monkeypatch):
    """No account at all falls back to the anonymous IP quota entirely -
    credits.deduct must never even be called."""
    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)
    deduct_calls = []
    monkeypatch.setattr(
        main.credits, "deduct", lambda *a, **k: deduct_calls.append(a) or True
    )

    request = main.AdaptRequest(text="line one\nline two")
    main.adapt(request, _FakeRequest())

    assert deduct_calls == []


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


def test_adapt_attaches_section_timing_with_no_video(monkeypatch):
    """web/lib/lyricsImport.ts's .lrc/.srt import produces real per-section
    timing with no video at all - this must still attach startSeconds/
    endSeconds (a real, useful result), just without a videoId key, since
    there's nothing for ResultScreen.tsx's sync player to embed."""
    captured: dict = {}
    _patch_engine_with_two_sections(monkeypatch, captured)

    request = main.AdaptRequest(
        text="line one\n\nline two",
        youtube_section_timings=[
            main.YoutubeSectionTiming(start=0.0, end=4.5),
            main.YoutubeSectionTiming(start=9.5, end=14.0),
        ],
    )
    result = main.adapt(request, _FakeRequest())

    assert "videoId" not in result
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
    with caplog.at_level("INFO", logger="castia.server"):
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


def _fake_run_engine_reporting_progress(
    song, client=None, room_version="v1", apply_corrective_pass=False,
    on_stage=None, on_section_done=None, deadline=None,
):
    """Stands in for engine/pipeline.py's real run_engine, but still
    invokes on_stage/on_section_done the way the real one does - proves
    server/main.py::_run_adaptation's progress reporting is wired
    correctly without a real engine run. Downstream of run_engine,
    _run_adaptation only ever calls to_experience_result (mocked
    separately, ignores engine_result's actual content) and
    engine_result.to_dict() (verify_result) - _FakeEngineResult already
    covers both, same as _patch_engine's tests rely on elsewhere in this
    file."""
    total = len(song.sections)
    for index, section in enumerate(song.sections, start=1):
        if on_stage:
            on_stage(section.name, index, total)
        if on_section_done:
            on_section_done(section.name, None, index, total)
    return _FakeEngineResult()


def _patch_song_progress_engine(monkeypatch):
    monkeypatch.setattr(main, "run_engine", _fake_run_engine_reporting_progress)
    monkeypatch.setattr(
        main,
        "to_experience_result",
        lambda client, result, result_id, explain_why_client=None: {
            "id": result_id,
            "hook": "test hook",
            "sourceLanguage": "unspecified",
            "sections": [],
            "original": [],
        },
    )
    monkeypatch.setattr(main, "create_default_client", lambda model=None: _FakeClient())


def test_run_adaptation_reports_incremental_progress_when_given_a_job_id(monkeypatch):
    """_run_adaptation is what /api/adapt/start's background job actually
    calls with a real job_id - the song-side equivalent of
    test_run_comics_adaptation_reports_incremental_progress_when_given_a_job_id."""
    _patch_song_progress_engine(monkeypatch)
    progress_calls: list[dict] = []
    monkeypatch.setattr(
        main.jobs, "set_progress", lambda job_id, progress: progress_calls.append(progress)
    )

    sections, song = main._build_song("line one\n\nline two", "English", "unspecified")

    main._run_adaptation(
        main.AdaptRequest(text="line one\n\nline two"),
        "result-1", "line one\n\nline two", "English", "unspecified",
        sections, song, "127.0.0.1", 0.0, job_id="job-1",
    )

    # One initial "Reading song..." report before anything runs, then one
    # "adapting" + one "done" report per section = 5.
    assert len(progress_calls) == 5
    messages = [c["message"] for c in progress_calls]
    assert messages == [
        "Reading song…",
        "Section 1/2: adapting…",
        "Section 1/2: done",
        "Section 2/2: adapting…",
        "Section 2/2: done",
    ]
    assert progress_calls[0]["completed"] == 0
    assert progress_calls[0]["total"] == 2
    assert progress_calls[-1]["completed"] == 2
    assert progress_calls[-1]["total"] == 2


def test_run_adaptation_reports_progress_before_song_dna_generation(monkeypatch):
    """The very first progress write must land BEFORE run_engine (and the
    Song DNA generation inside it) even starts - proven by making the
    fake run_engine itself check that a report already happened, rather
    than by ordering assertions after the fact."""
    progress_calls: list[dict] = []
    monkeypatch.setattr(
        main.jobs, "set_progress", lambda job_id, progress: progress_calls.append(progress)
    )

    def run_engine_checks_progress_already_reported(
        song, client=None, room_version="v1", apply_corrective_pass=False,
        on_stage=None, on_section_done=None, deadline=None,
    ):
        assert len(progress_calls) == 1
        assert progress_calls[0]["message"] == "Reading song…"
        assert progress_calls[0]["completed"] == 0
        assert progress_calls[0]["total"] == 1
        return _FakeEngineResult()

    monkeypatch.setattr(main, "run_engine", run_engine_checks_progress_already_reported)
    monkeypatch.setattr(
        main,
        "to_experience_result",
        lambda client, result, result_id, explain_why_client=None: {
            "id": result_id,
            "hook": "test hook",
            "sourceLanguage": "unspecified",
            "sections": [],
            "original": [],
        },
    )
    monkeypatch.setattr(main, "create_default_client", lambda model=None: _FakeClient())

    sections, song = main._build_song("line one", "English", "unspecified")

    main._run_adaptation(
        main.AdaptRequest(text="line one"),
        "result-1", "line one", "English", "unspecified",
        sections, song, "127.0.0.1", 0.0, job_id="job-1",
    )

    assert progress_calls[0]["message"] == "Reading song…"


def test_run_adaptation_reports_nothing_without_a_job_id(monkeypatch):
    _patch_song_progress_engine(monkeypatch)
    progress_calls: list[dict] = []
    monkeypatch.setattr(
        main.jobs, "set_progress", lambda job_id, progress: progress_calls.append(progress)
    )

    sections, song = main._build_song("line one", "English", "unspecified")
    main._run_adaptation(
        main.AdaptRequest(text="line one"),
        "result-1", "line one", "English", "unspecified",
        sections, song, "127.0.0.1", 0.0,
    )

    assert progress_calls == []


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
    """Stands in for FastAPI's UploadFile — the `.file.read()` path
    server/main.py's comics_ocr_endpoint uses, plus `.content_type`,
    which the endpoint passes to the vision reader as the image's media
    type. Real UploadFile always has that attribute (it may be None), so
    the fake carries it too rather than making the endpoint defend
    against a shape only this test double ever had.
    """

    def __init__(self, data: bytes, content_type: str | None = "image/png"):
        self.file = _FakeSpooledFile(data)
        self.content_type = content_type


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


def _real_png_bytes(width=200, height=100) -> bytes:
    import io as _io

    from PIL import Image as _Image

    buffer = _io.BytesIO()
    _Image.new("RGB", (width, height), (255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_comics_redraw_endpoint_returns_a_base64_image():
    image_bytes = _real_png_bytes()
    regions = json.dumps(
        [{"bbox": {"x": 10, "y": 10, "width": 100, "height": 40}, "adapted_text": "hello"}]
    )

    result = main.comics_redraw_endpoint(
        image=_FakeUploadFile(image_bytes), regions=regions, default_font=None
    )

    import base64 as _base64

    decoded = _base64.b64decode(result["image_base64"])
    assert decoded[:8] == b"\x89PNG\r\n\x1a\n"  # real PNG magic bytes


def test_comics_redraw_endpoint_rejects_malformed_regions_json():
    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_redraw_endpoint(
            image=_FakeUploadFile(_real_png_bytes()), regions="not valid json", default_font=None
        )
    assert exc_info.value.status_code == 400


def test_comics_redraw_endpoint_rejects_a_region_missing_required_fields():
    regions = json.dumps([{"bbox": {"x": 10, "y": 10}, "adapted_text": "hello"}])  # no width/height
    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_redraw_endpoint(image=_FakeUploadFile(_real_png_bytes()), regions=regions, default_font=None)
    assert exc_info.value.status_code == 400


def test_comics_redraw_endpoint_rejects_an_empty_region_list():
    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_redraw_endpoint(image=_FakeUploadFile(_real_png_bytes()), regions="[]", default_font=None)
    assert exc_info.value.status_code == 400


def test_comics_redraw_endpoint_reports_a_redraw_failure_as_a_400():
    regions = json.dumps(
        [{"bbox": {"x": 10, "y": 10, "width": 20, "height": 20}, "adapted_text": "x"}]
    )
    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_redraw_endpoint(image=_FakeUploadFile(b"not a real image"), regions=regions, default_font=None)
    assert exc_info.value.status_code == 400


def test_comics_redraw_endpoint_rejects_an_oversized_image():
    oversized = b"x" * (main.MAX_IMAGE_BYTES + 1)
    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_redraw_endpoint(image=_FakeUploadFile(oversized), regions="[]", default_font=None)
    assert exc_info.value.status_code == 413


def test_comics_redraw_endpoint_rejects_an_unknown_default_font():
    regions = json.dumps(
        [{"bbox": {"x": 10, "y": 10, "width": 100, "height": 40}, "adapted_text": "hello"}]
    )
    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_redraw_endpoint(
            image=_FakeUploadFile(_real_png_bytes()), regions=regions, default_font="not-a-real-font"
        )
    assert exc_info.value.status_code == 400
    assert "not-a-real-font" in exc_info.value.detail


def test_comics_redraw_endpoint_rejects_an_unknown_per_region_font():
    regions = json.dumps(
        [
            {
                "bbox": {"x": 10, "y": 10, "width": 100, "height": 40},
                "adapted_text": "hello",
                "font": "totally-made-up",
            }
        ]
    )
    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_redraw_endpoint(
            image=_FakeUploadFile(_real_png_bytes()), regions=regions, default_font=None
        )
    assert exc_info.value.status_code == 400
    assert "totally-made-up" in exc_info.value.detail


def test_comics_redraw_endpoint_accepts_a_real_default_font():
    regions = json.dumps(
        [{"bbox": {"x": 10, "y": 10, "width": 100, "height": 40}, "adapted_text": "hello"}]
    )
    result = main.comics_redraw_endpoint(
        image=_FakeUploadFile(_real_png_bytes()), regions=regions, default_font="patrick-hand"
    )
    import base64 as _base64

    decoded = _base64.b64decode(result["image_base64"])
    assert decoded[:8] == b"\x89PNG\r\n\x1a\n"


def test_comics_redraw_endpoint_recomputes_for_a_different_font(monkeypatch):
    """Same image, same regions, different font: must be a real recompute,
    not a cache hit that silently serves the old font's image back."""
    image_bytes = _real_png_bytes()
    regions = json.dumps(
        [{"bbox": {"x": 10, "y": 10, "width": 100, "height": 40}, "adapted_text": "hello"}]
    )

    call_count = 0
    real_redraw = main.redraw_panel_detailed

    def counting_redraw(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return real_redraw(*args, **kwargs)

    monkeypatch.setattr(main, "redraw_panel_detailed", counting_redraw)

    first = main.comics_redraw_endpoint(
        image=_FakeUploadFile(image_bytes), regions=regions, default_font="comic-neue"
    )
    second = main.comics_redraw_endpoint(
        image=_FakeUploadFile(image_bytes), regions=regions, default_font="patrick-hand"
    )

    assert call_count == 2
    assert first["id"] != second["id"]


def test_comics_redraw_endpoint_returns_a_real_content_addressed_id():
    image_bytes = _real_png_bytes()
    regions = json.dumps(
        [{"bbox": {"x": 10, "y": 10, "width": 100, "height": 40}, "adapted_text": "hello"}]
    )

    result = main.comics_redraw_endpoint(
        image=_FakeUploadFile(image_bytes), regions=regions, default_font=None
    )

    assert result["id"] == main.cache.comics_redraw_content_id(
        image_bytes,
        [{"bbox": {"x": 10, "y": 10, "width": 100, "height": 40}, "adapted_text": "hello", "font": None}],
        None,
    )


def test_comics_redraw_endpoint_serves_an_identical_request_from_cache(monkeypatch):
    image_bytes = _real_png_bytes()
    regions = json.dumps(
        [{"bbox": {"x": 10, "y": 10, "width": 100, "height": 40}, "adapted_text": "hello"}]
    )

    call_count = 0
    real_redraw = main.redraw_panel_detailed

    def counting_redraw(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return real_redraw(*args, **kwargs)

    monkeypatch.setattr(main, "redraw_panel_detailed", counting_redraw)

    first = main.comics_redraw_endpoint(
        image=_FakeUploadFile(image_bytes), regions=regions, default_font=None
    )
    second = main.comics_redraw_endpoint(
        image=_FakeUploadFile(image_bytes), regions=regions, default_font=None
    )

    assert call_count == 1  # the inpainting pipeline only actually ran once
    assert second["id"] == first["id"]
    assert second["image_base64"] == first["image_base64"]
    assert second["inpaint_method"] == first["inpaint_method"]


def test_comics_redraw_endpoint_recomputes_for_different_adapted_text(monkeypatch):
    image_bytes = _real_png_bytes()

    call_count = 0
    real_redraw = main.redraw_panel_detailed

    def counting_redraw(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return real_redraw(*args, **kwargs)

    monkeypatch.setattr(main, "redraw_panel_detailed", counting_redraw)

    first_regions = json.dumps(
        [{"bbox": {"x": 10, "y": 10, "width": 100, "height": 40}, "adapted_text": "hello"}]
    )
    second_regions = json.dumps(
        [{"bbox": {"x": 10, "y": 10, "width": 100, "height": 40}, "adapted_text": "goodbye"}]
    )

    first = main.comics_redraw_endpoint(
        image=_FakeUploadFile(image_bytes), regions=first_regions, default_font=None
    )
    second = main.comics_redraw_endpoint(
        image=_FakeUploadFile(image_bytes), regions=second_regions, default_font=None
    )

    assert call_count == 2  # different text is a different result, not a cache hit
    assert first["id"] != second["id"]


def test_get_comics_redraw_returns_a_previously_cached_result():
    image_bytes = _real_png_bytes()
    regions = json.dumps(
        [{"bbox": {"x": 10, "y": 10, "width": 100, "height": 40}, "adapted_text": "hello"}]
    )
    created = main.comics_redraw_endpoint(
        image=_FakeUploadFile(image_bytes), regions=regions, default_font=None
    )

    fetched = main.get_comics_redraw(created["id"])

    assert fetched == created


def test_get_comics_redraw_404s_for_an_unknown_id():
    with pytest.raises(main.HTTPException) as exc_info:
        main.get_comics_redraw("not-a-real-id")
    assert exc_info.value.status_code == 404


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


def _fake_adapt_chapter(chapter, dna, client, on_stage=None, on_bubble_done=None, deadline=None):
    """Stands in for engine/comics_adapt.py's real adapt_chapter, but
    still invokes on_stage/on_bubble_done the way the real one does -
    server/main.py::_run_comics_adaptation now builds each panel's
    output (and reports job progress) from those callbacks rather than
    from adapt_chapter's return value, so a fake that only returns a
    list without calling them would silently produce zero panels."""
    results = [_FakeSectionResult(b.id, f"adapted {b.id}") for b in chapter.bubbles]
    total = len(results)
    for index, (bubble, result) in enumerate(zip(chapter.bubbles, results), start=1):
        if on_stage:
            on_stage(bubble.id, "adapting", index, total)
            on_stage(bubble.id, "verifying", index, total)
        if on_bubble_done:
            on_bubble_done(bubble.id, result, index, total)
    return results


def _patch_comics_adapt(monkeypatch, dna=None):
    monkeypatch.setattr(main, "generate_chapter_dna", lambda chapter, client: dna or _fake_chapter_dna())
    monkeypatch.setattr(main, "adapt_chapter", _fake_adapt_chapter)
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


def test_run_comics_adaptation_reports_incremental_progress_when_given_a_job_id(monkeypatch):
    """_run_comics_adaptation is what /api/comics/adapt/start's
    background job actually calls with a real job_id - this is the
    piece that lets a poller see each panel's real finished text as soon
    as it's ready, rather than only once the whole chapter is done."""
    _patch_comics_adapt(monkeypatch)
    progress_calls: list[dict] = []
    monkeypatch.setattr(
        main.jobs, "set_progress", lambda job_id, progress: progress_calls.append(progress)
    )

    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[
            main.ComicsPanelText(id="panel-1", text="hello"),
            main.ComicsPanelText(id="panel-2", text="goodbye"),
        ],
    )
    non_empty_panels = [p for p in request.panels if p.text.strip()]

    payload = main._run_comics_adaptation(
        request, "result-1", non_empty_panels, user_id=None, job_id="job-1"
    )

    # One initial "Reading chapter..." report before anything runs, then
    # one "adapting" + one "verifying" + one "done" report per panel = 7.
    assert len(progress_calls) == 7
    messages = [c["message"] for c in progress_calls]
    assert messages == [
        "Reading chapter…",
        "Panel 1/2: adapting…",
        "Panel 1/2: verifying…",
        "Panel 1/2: done",
        "Panel 2/2: adapting…",
        "Panel 2/2: verifying…",
        "Panel 2/2: done",
    ]
    # The first panel's real result is visible in progress well before
    # the second panel starts - the whole point of reporting per-panel
    # rather than only at the very end.
    assert progress_calls[3]["panels"] == [
        {"id": "panel-1", "literal": "literal panel-1", "adapted_text": "adapted panel-1", "why": "why text"}
    ]
    assert progress_calls[4]["panels"] == progress_calls[3]["panels"]  # unchanged mid-panel-2
    assert progress_calls[-1]["panels"] == payload["panels"]
    assert progress_calls[-1]["completed"] == 2
    assert progress_calls[-1]["total"] == 2


def test_run_comics_adaptation_reports_progress_before_chapter_dna_generation(monkeypatch):
    """The very first progress write must land BEFORE generate_chapter_dna
    runs, not just before the bubble loop - Chapter DNA generation is
    itself a real LLM call that can be slow (rate-limited, etc.), and a
    poller should never see zero feedback while it's in flight. Proven by
    making generate_chapter_dna itself check that a report already
    happened, rather than by ordering assertions after the fact."""
    progress_calls: list[dict] = []
    monkeypatch.setattr(
        main.jobs, "set_progress", lambda job_id, progress: progress_calls.append(progress)
    )

    def dna_checks_progress_already_reported(chapter, client):
        assert len(progress_calls) == 1
        assert progress_calls[0]["message"] == "Reading chapter…"
        assert progress_calls[0]["completed"] == 0
        assert progress_calls[0]["total"] == 1
        return _fake_chapter_dna()

    monkeypatch.setattr(main, "generate_chapter_dna", dna_checks_progress_already_reported)
    monkeypatch.setattr(main, "adapt_chapter", _fake_adapt_chapter)
    monkeypatch.setattr(main, "_translator_text", lambda result: f"literal {result.section}")
    monkeypatch.setattr(
        main, "_explain_why", lambda client, thesis, literal, adapted, tradeoffs: "why text"
    )
    monkeypatch.setattr(main, "create_default_client", lambda: object())

    request = main.ComicsAdaptRequest(
        source_language="Korean", panels=[main.ComicsPanelText(id="panel-1", text="hello")]
    )

    main._run_comics_adaptation(request, "result-1", request.panels, user_id=None, job_id="job-1")

    assert progress_calls[0]["message"] == "Reading chapter…"


def test_run_comics_adaptation_reports_nothing_without_a_job_id(monkeypatch):
    _patch_comics_adapt(monkeypatch)
    progress_calls: list[dict] = []
    monkeypatch.setattr(
        main.jobs, "set_progress", lambda job_id, progress: progress_calls.append(progress)
    )

    request = main.ComicsAdaptRequest(
        source_language="Korean", panels=[main.ComicsPanelText(id="panel-1", text="hello")]
    )
    main._run_comics_adaptation(request, "result-1", request.panels, user_id=None)

    assert progress_calls == []


def test_run_comics_adaptation_logs_real_measured_token_usage(monkeypatch, caplog):
    """The comics job path had no cost visibility at all (unlike the song
    path's tokens_by_stage log line) - this is the real, measured
    (never estimated) per-chapter token/cost log server/main.py now emits,
    mirroring _adapt_or_serve_cached's existing pattern for songs."""
    _patch_comics_adapt(monkeypatch)

    from engine.models import LLMCallRecord

    class _RecordingClient:
        def __init__(self):
            self.call_log = [
                LLMCallRecord(
                    stage="translator", model="gpt-4o", prompt_tokens=100,
                    completion_tokens=20, latency_seconds=0.5,
                ),
                LLMCallRecord(
                    stage="judge_triage", model="gpt-4o", prompt_tokens=300,
                    completion_tokens=80, latency_seconds=1.2,
                ),
            ]

    monkeypatch.setattr(main, "create_default_client", lambda: _RecordingClient())

    request = main.ComicsAdaptRequest(
        source_language="Korean", panels=[main.ComicsPanelText(id="panel-1", text="hello")]
    )

    with caplog.at_level("INFO", logger="castia.server"):
        main._run_comics_adaptation(request, "result-1", request.panels, user_id=None)

    cost_lines = [r.message for r in caplog.records if "comics_adapt id=" in r.message]
    assert len(cost_lines) == 1
    assert "prompt_tokens=400" in cost_lines[0]
    assert "completion_tokens=100" in cost_lines[0]
    assert "llm_calls=2" in cost_lines[0]
    assert "translator[gpt-4o]=100p/20c" in cost_lines[0]
    assert "judge_triage[gpt-4o]=300p/80c" in cost_lines[0]


def test_comics_adapt_endpoint_threads_voice_into_bubble_input(monkeypatch):
    _patch_comics_adapt(monkeypatch)
    captured_chapters = []

    def capturing_adapt_chapter(chapter, dna, client, on_stage=None, on_bubble_done=None, deadline=None):
        captured_chapters.append(chapter)
        return _fake_adapt_chapter(chapter, dna, client, on_stage=on_stage, on_bubble_done=on_bubble_done)

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


def test_comics_adapt_endpoint_rejects_a_chapter_over_the_panel_cap(monkeypatch):
    """Comics had no per-request size ceiling at all before MAX_COMICS_PANELS -
    unlike songs (MAX_INPUT_CHARS), a chapter's cost scales directly with
    panel count and nothing bounded it: a 100-panel chapter and a 3-panel
    one both cost "1" against the daily/monthly quota."""
    monkeypatch.setattr(main, "MAX_COMICS_PANELS", 2)
    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[
            main.ComicsPanelText(id="panel-1", text="a"),
            main.ComicsPanelText(id="panel-2", text="b"),
            main.ComicsPanelText(id="panel-3", text="c"),
        ],
    )
    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_adapt_endpoint(request, _FakeRequest())

    assert exc_info.value.status_code == 413


def test_comics_adapt_endpoint_enforces_ip_quota(monkeypatch):
    """The browser-facing comics endpoint had NO quota enforcement at all
    before this - _check_quota was only ever called from the song
    endpoints. Comics is the more expensive path per request (an OCR
    pass plus a full Writers' Room run per panel), so this gap mattered
    more here, not less."""
    _patch_comics_adapt(monkeypatch)
    monkeypatch.setattr(main, "DAILY_LIMIT", 1)
    monkeypatch.setattr(main, "MONTHLY_LIMIT", 5)

    request = main.ComicsAdaptRequest(
        source_language="Korean", panels=[main.ComicsPanelText(id="panel-1", text="hello")]
    )
    main.comics_adapt_endpoint(request, _FakeRequest())  # first call: allowed

    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_adapt_endpoint(
            main.ComicsAdaptRequest(
                source_language="Korean",
                panels=[main.ComicsPanelText(id="panel-2", text="different text")],
            ),
            _FakeRequest(),
        )

    assert exc_info.value.status_code == 429
    assert "chapters" in exc_info.value.detail


def test_comics_adapt_endpoint_deducts_credits_per_panel_for_a_signed_in_user(monkeypatch):
    """CREDITS_PER_PANEL * the actual panel count, matching web/app/
    pricing/page.tsx's PAGE_CREDITS derivation - not a flat per-chapter
    price, so a 5-panel chapter costs 5x a 1-panel one."""
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "test-secret")
    _patch_comics_adapt(monkeypatch)
    deduct_calls = []
    monkeypatch.setattr(
        main.credits,
        "deduct",
        lambda user_id, amount, reason, reference=None: deduct_calls.append(
            (user_id, amount, reason)
        )
        or True,
    )

    request = main.ComicsAdaptRequest(
        source_language="Korean",
        panels=[
            main.ComicsPanelText(id="panel-1", text="hello"),
            main.ComicsPanelText(id="panel-2", text="goodbye"),
        ],
    )
    main.comics_adapt_endpoint(request, _authed_request("user-1"))

    assert deduct_calls == [("user-1", main.CREDITS_PER_PANEL * 2, "adaptation")]


def test_comics_adapt_endpoint_returns_402_when_credits_are_insufficient(monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "test-secret")
    monkeypatch.setattr(main.credits, "deduct", lambda *a, **k: False)

    request = main.ComicsAdaptRequest(
        source_language="Korean", panels=[main.ComicsPanelText(id="panel-1", text="hello")]
    )
    with pytest.raises(main.HTTPException) as exc_info:
        main.comics_adapt_endpoint(request, _authed_request("user-1"))

    assert exc_info.value.status_code == 402


def test_comics_adapt_endpoint_refunds_credits_when_the_engine_fails(monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "test-secret")
    monkeypatch.setattr(main, "create_default_client", lambda: object())

    def raise_llm_error(chapter, client):
        raise main.LLMError("provider is down")

    monkeypatch.setattr(main, "generate_chapter_dna", raise_llm_error)
    monkeypatch.setattr(main.credits, "deduct", lambda *a, **k: True)
    refund_calls = []
    monkeypatch.setattr(
        main.credits,
        "refund",
        lambda user_id, amount, reference=None: refund_calls.append((user_id, amount)),
    )

    request = main.ComicsAdaptRequest(
        source_language="Korean", panels=[main.ComicsPanelText(id="panel-1", text="hello")]
    )
    with pytest.raises(main.HTTPException):
        main.comics_adapt_endpoint(request, _authed_request("user-1"))

    assert refund_calls == [("user-1", main.CREDITS_PER_PANEL * 1)]


def test_comics_adapt_endpoint_does_not_touch_credits_for_an_anonymous_request(monkeypatch):
    _patch_comics_adapt(monkeypatch)
    deduct_calls = []
    monkeypatch.setattr(
        main.credits, "deduct", lambda *a, **k: deduct_calls.append(a) or True
    )

    request = main.ComicsAdaptRequest(
        source_language="Korean", panels=[main.ComicsPanelText(id="panel-1", text="hello")]
    )
    main.comics_adapt_endpoint(request, _FakeRequest())

    assert deduct_calls == []


def test_v1_comics_adapt_does_not_enforce_ip_quota(monkeypatch):
    """The public API path is gated by its own per-key limit
    (_require_api_key -> API_DAILY_LIMIT), not the browser's per-IP one -
    same split songs already have between /api/adapt and /v1/adapt."""
    _patch_comics_adapt(monkeypatch)
    monkeypatch.setattr(main, "DAILY_LIMIT", 1)
    monkeypatch.setattr(main, "MONTHLY_LIMIT", 1)
    monkeypatch.setattr(
        main, "_require_api_key", lambda request: {"user_id": "u1", "key_id": "k1"}
    )

    for i in range(3):
        request = main.ComicsAdaptRequest(
            source_language="Korean",
            panels=[main.ComicsPanelText(id=f"panel-{i}", text=f"text {i}")],
        )
        main.v1_comics_adapt(request, _FakeRequest())  # must not raise 429


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
        "x-castia-user-id": "user-42",
        "x-castia-internal-secret": "test-secret",
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


# ---------------------------------------------------------------------------
# The vision-LLM read pass runs CONCURRENTLY with Cloud Vision, not after
# it. That's the whole reason the alignment layer (engine/comics_align.py)
# exists instead of just handing the model Vision's boxes, so it's worth a
# test that would actually fail if the two calls were ever serialized.
# ---------------------------------------------------------------------------


def test_ocr_and_vision_reading_run_concurrently(monkeypatch):
    import threading

    from engine import comics_align, comics_vision

    both_started = threading.Barrier(2, timeout=5)

    def fake_ocr(image_bytes, language=None):
        # Blocks until the vision call has also started. If these ran one
        # after the other this barrier would never fill and the test times
        # out rather than passing slowly.
        both_started.wait()
        return {
            "regions": [{"text": "HELL0", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1},
                         "confidence": 70.0}],
            "full_text": "HELL0",
            "warning": None,
            "image_width": 10,
            "image_height": 10,
            "detected_languages": [],
        }

    def fake_read_panel(image_bytes, mime_type="image/jpeg"):
        both_started.wait()
        return [comics_align.Reading(text="HELLO", kind="dialogue", speaker="Mira")]

    monkeypatch.setattr(main.comics_ocr, "extract_text_regions", fake_ocr)
    monkeypatch.setattr(comics_vision, "read_panel", fake_read_panel)

    result = main.comics_ocr_endpoint(image=_FakeUploadFile(b"bytes"), language=None)

    assert result["regions"][0]["text"] == "HELLO"
    assert result["vision_corrected_count"] == 1


def test_a_vision_failure_still_returns_the_ocr_result(monkeypatch):
    """Enrichment must never cost the user the thing they asked for."""
    from engine import comics_vision

    monkeypatch.setattr(
        main.comics_ocr,
        "extract_text_regions",
        lambda image_bytes, language=None: {
            "regions": [{"text": "HELL0", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1},
                         "confidence": 70.0}],
            "full_text": "HELL0",
            "warning": None,
            "image_width": 10,
            "image_height": 10,
            "detected_languages": [],
        },
    )
    # read_panel's own contract is to swallow failures and return [];
    # this asserts the endpoint is fine with that empty result.
    monkeypatch.setattr(comics_vision, "read_panel", lambda *a, **k: [])

    result = main.comics_ocr_endpoint(image=_FakeUploadFile(b"bytes"), language=None)
    assert result["regions"][0]["text"] == "HELL0"
    assert "vision_corrected_count" not in result


def test_two_step_read_is_used_when_a_detector_is_configured(monkeypatch):
    from engine import comics_read, config

    monkeypatch.setattr(config, "TEXT_DETECTOR_URL", "http://detector.internal/detect")
    monkeypatch.setattr(
        comics_read,
        "read_panel_two_step",
        lambda *a, **k: {"regions": [{"node_id": "r0", "text": "TWO STEP"}], "warning": None},
    )
    result = main.comics_ocr_endpoint(image=_FakeUploadFile(b"bytes"), language=None)
    assert result["regions"][0]["text"] == "TWO STEP"


def test_a_two_step_failure_falls_back_to_the_single_step_path(monkeypatch):
    """Detection returning nothing must not fail the request - the old
    single-step path is still a complete, working read.
    """
    from engine import comics_read, comics_vision, config

    monkeypatch.setattr(config, "TEXT_DETECTOR_URL", "http://detector.internal/detect")
    monkeypatch.setattr(comics_read, "read_panel_two_step", lambda *a, **k: {})
    monkeypatch.setattr(comics_vision, "read_panel", lambda *a, **k: [])
    monkeypatch.setattr(
        main.comics_ocr,
        "extract_text_regions",
        lambda image_bytes, language=None: {
            "regions": [{"text": "FALLBACK", "bbox": {"x": 0, "y": 0, "width": 1, "height": 1},
                         "confidence": 70.0}],
            "full_text": "FALLBACK",
            "warning": None,
            "image_width": 10,
            "image_height": 10,
            "detected_languages": [],
        },
    )
    result = main.comics_ocr_endpoint(image=_FakeUploadFile(b"bytes"), language=None)
    assert result["regions"][0]["text"] == "FALLBACK"


def test_no_detector_configured_keeps_the_original_single_step_path(monkeypatch):
    from engine import comics_read, comics_vision, config

    monkeypatch.setattr(config, "TEXT_DETECTOR_URL", "")
    monkeypatch.setattr(
        comics_read,
        "read_panel_two_step",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not run")),
    )
    monkeypatch.setattr(comics_vision, "read_panel", lambda *a, **k: [])
    monkeypatch.setattr(
        main.comics_ocr,
        "extract_text_regions",
        lambda image_bytes, language=None: {
            "regions": [], "full_text": "", "warning": None,
            "image_width": 0, "image_height": 0, "detected_languages": [],
        },
    )
    assert main.comics_ocr_endpoint(image=_FakeUploadFile(b"bytes"), language=None)["regions"] == []
