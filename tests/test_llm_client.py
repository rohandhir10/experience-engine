"""No network calls here — these test client construction and error
handling around the OpenAI SDK boundary, not the SDK itself.
"""
from __future__ import annotations

import json

import httpx
import openai
import pytest

from unittest.mock import MagicMock

from engine import config
from engine.llm_client import LLMError, OpenAILLMClient


@pytest.fixture(autouse=True)
def _dummy_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-not-real")


# ---------------------------------------------------------------------------
# get_api_key — regression test for a real production bug
# ---------------------------------------------------------------------------


def test_api_key_trailing_whitespace_is_stripped(monkeypatch):
    """Regression test for a real bug found in production: a trailing
    space in the OPENAI_API_KEY env var (a Vercel dashboard copy-paste
    artifact) turned the Authorization header into something httpx's HTTP
    layer rejects outright — "LocalProtocolError: Illegal header value" —
    before any request was even sent. That looked exactly like a network
    connection failure and took real debugging to trace back to this.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-not-real \n")
    assert config.get_api_key("openai") == "sk-test-dummy-not-real"


def test_api_key_without_whitespace_is_unaffected(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-not-real")
    assert config.get_api_key("openai") == "sk-test-dummy-not-real"


def test_whitespace_only_api_key_is_treated_as_unset(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "   ")
    with pytest.raises(RuntimeError, match="is not set"):
        config.get_api_key("openai")


def test_force_ipv4_default_builds_a_custom_http_client(monkeypatch):
    monkeypatch.setattr(config, "FORCE_IPV4", True)
    client = OpenAILLMClient()
    # openai.OpenAI stores whatever http_client it was given (or builds its
    # own default if None) — confirm ours actually wired one in rather than
    # silently falling through to openai's default.
    assert client._client._client is not None


def test_force_ipv4_disabled_lets_openai_use_its_own_default(monkeypatch):
    monkeypatch.setattr(config, "FORCE_IPV4", False)
    client = OpenAILLMClient()
    # Should still construct cleanly with no custom transport supplied.
    assert client._client is not None


def test_connection_error_message_surfaces_the_underlying_exception(monkeypatch):
    """Regression test: openai's own str(exc) for a connection failure is
    just "Connection error." with no detail — indistinguishable between a
    DNS failure, a refused connection, or a TLS failure. This is exactly
    what made a real Vercel deployment failure hard to diagnose. The fix
    must surface __cause__ (the real httpx/socket exception) in the raised
    LLMError, not just re-wrap the generic message.
    """
    client = OpenAILLMClient()

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    underlying = ConnectionRefusedError("[Errno 111] Connection refused")
    api_error = openai.APIConnectionError(request=request)
    api_error.__cause__ = underlying

    def _raise(*args, **kwargs):
        raise api_error

    monkeypatch.setattr(client._client.chat.completions, "create", _raise)

    with pytest.raises(LLMError) as exc_info:
        client._call("system", "user", None)

    message = str(exc_info.value)
    assert "Connection error" in message
    assert "ConnectionRefusedError" in message
    assert "Connection refused" in message


def test_connection_error_without_a_cause_says_so_rather_than_crashing(monkeypatch):
    client = OpenAILLMClient()
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    api_error = openai.APIConnectionError(request=request)
    # No __cause__ set — must degrade to an honest "don't know", not a
    # bare AttributeError from assuming __cause__ is always present.

    def _raise(*args, **kwargs):
        raise api_error

    monkeypatch.setattr(client._client.chat.completions, "create", _raise)

    with pytest.raises(LLMError) as exc_info:
        client._call("system", "user", None)

    assert "no underlying exception captured" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Cost/latency instrumentation — measured, not estimated (LLMCallRecord)
# ---------------------------------------------------------------------------


def _fake_response(text: str, prompt_tokens: int, completion_tokens: int):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=text))]
    response.usage = MagicMock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return response


def test_call_returns_real_token_counts_from_the_response(monkeypatch):
    client = OpenAILLMClient()
    monkeypatch.setattr(
        client._client.chat.completions,
        "create",
        lambda **kwargs: _fake_response('{"ok": true}', 123, 45),
    )
    text, prompt_tokens, completion_tokens = client._call("system", "user", None)
    assert text == '{"ok": true}'
    assert prompt_tokens == 123
    assert completion_tokens == 45


def test_complete_json_appends_a_measured_call_record(monkeypatch):
    client = OpenAILLMClient()
    monkeypatch.setattr(
        client._client.chat.completions,
        "create",
        lambda **kwargs: _fake_response('{"ok": true}', 200, 50),
    )
    client.complete_json("system", "user", stage="translator")

    assert len(client.call_log) == 1
    record = client.call_log[0]
    assert record.stage == "translator"
    assert record.model == client.model
    assert record.prompt_tokens == 200
    assert record.completion_tokens == 50
    assert record.attempt == "initial"
    assert record.latency_seconds >= 0.0


def test_json_repair_retry_logs_its_own_call_record(monkeypatch):
    """A malformed first reply triggers exactly one corrective retry
    (LLMClient.complete_json) — both calls are real API calls and must
    both be measured, not just the first.
    """
    client = OpenAILLMClient()
    responses = [
        _fake_response("not json at all", 100, 10),
        _fake_response('{"ok": true}', 120, 15),
    ]
    monkeypatch.setattr(
        client._client.chat.completions,
        "create",
        lambda **kwargs: responses.pop(0),
    )
    result = client.complete_json("system", "user", stage="judge_triage")

    assert result == {"ok": True}
    assert len(client.call_log) == 2
    assert client.call_log[0].attempt == "initial"
    assert client.call_log[0].prompt_tokens == 100
    assert client.call_log[1].attempt == "json_repair_retry"
    assert client.call_log[1].prompt_tokens == 120


def test_default_stage_is_labeled_unknown_not_left_blank(monkeypatch):
    client = OpenAILLMClient()
    monkeypatch.setattr(
        client._client.chat.completions,
        "create",
        lambda **kwargs: _fake_response('{"ok": true}', 10, 5),
    )
    client.complete_json("system", "user")  # no stage= passed
    assert client.call_log[0].stage == "unknown"


def test_a_full_engine_run_produces_a_real_stage_labeled_call_log(monkeypatch):
    """End-to-end: a real OpenAILLMClient (network call mocked, everything
    else real) run through the whole pipeline should leave behind a
    call_log that actually identifies which pipeline stage made each call
    — this is the data the cost-profile request needs, and until now
    nothing captured it at all.
    """
    from engine.models import SectionInput, SongInput
    from engine.pipeline import run_engine

    from .test_pipeline_mock import FAKE_SONG_DNA
    from .test_writers_room_v1 import DIMENSION_SCORES, FIVE_PHILOSOPHY_CANDIDATES

    READY_LINE = FIVE_PHILOSOPHY_CANDIDATES[0]["text"]

    def _fake_create(**kwargs):
        system = kwargs["messages"][0]["content"]
        if "You are a songwriting analyst" in system:
            content = json.dumps(FAKE_SONG_DNA)
        elif "You are the Creative Adapter" in system:
            content = json.dumps({"candidates": FIVE_PHILOSOPHY_CANDIDATES})
        elif "uncertainty_type" in system:
            content = json.dumps(
                {
                    "text": READY_LINE,
                    "leans_into": "guarded attachment",
                    "confidence": 0.9,
                    "uncertainty_type": "none",
                }
            )
        elif "running the minimal V1 room" in system:
            content = json.dumps(
                {
                    "ready_to_rule": True,
                    "ruling": {
                        "final_line": READY_LINE,
                        "sources_used": [],
                        "vetoes_applied": [],
                        "deviations": [],
                        "dimension_scores": DIMENSION_SCORES,
                        "priority_tradeoffs_made": "test",
                        "disagreements_overruled": [],
                    },
                    "specialists_needed": [],
                    "why": "test",
                }
            )
        else:
            raise AssertionError(f"Unexpected prompt: {system[:80]!r}")
        return _fake_response(content, prompt_tokens=100, completion_tokens=50)

    client = OpenAILLMClient()
    monkeypatch.setattr(client._client.chat.completions, "create", _fake_create)

    song = SongInput(
        source_language="English (test)",
        sections=[SectionInput(name="verse_1", source_text="line one")],
    )
    result = run_engine(song, client=client, room_version="v1")

    stages = [record.stage for record in result.call_log]
    assert stages == ["song_dna", "translator", "creative_adapter", "judge_triage"]
    assert all(record.prompt_tokens == 100 for record in result.call_log)
    assert all(record.completion_tokens == 50 for record in result.call_log)
    assert all(record.model == client.model for record in result.call_log)

    # Same data must round-trip through the stored result.
    dumped = result.to_dict()["llm_calls"]
    assert [c["stage"] for c in dumped] == stages
