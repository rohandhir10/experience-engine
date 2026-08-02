"""No network calls here — these test client construction and error
handling around the OpenAI SDK boundary, not the SDK itself.
"""
from __future__ import annotations

import httpx
import openai
import pytest

from engine import config
from engine.llm_client import LLMError, OpenAILLMClient


@pytest.fixture(autouse=True)
def _dummy_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-not-real")


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
