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

    def fake_to_experience_result(client, result, result_id):
        return {
            "id": result_id,
            "hook": "test hook",
            "sourceLanguage": "unspecified",
            "sections": [],
            "original": [],
        }

    monkeypatch.setattr(main, "run_engine", fake_run_engine)
    monkeypatch.setattr(main, "to_experience_result", fake_to_experience_result)
    monkeypatch.setattr(main, "create_default_client", lambda: _FakeClient())


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


def test_adapt_logs_clean_verification_with_no_findings(monkeypatch, caplog):
    captured: dict = {}
    _patch_engine(monkeypatch, _FakeEngineResult(), captured)

    with caplog.at_level("INFO", logger="aura.server"):
        request = main.AdaptRequest(text="line one\nline two")
        main.adapt(request, _FakeRequest())

    verify_lines = [r.message for r in caplog.records if "verify errors=" in r.message]
    assert len(verify_lines) == 1
    assert "errors=0" in verify_lines[0]


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
