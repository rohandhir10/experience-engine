"""LLM adapters used by every stage of the engine.

Every prompt in this engine asks the model to return a single JSON object.
This module owns the one place that calls a model provider and parses that
JSON, so every other module works with plain Python data, never raw model
text — and so no other module needs to know or care which provider is
actually behind `client.complete_json(...)`.

Two providers are implemented:
  - OpenAI (`OpenAILLMClient`) — the active default.
  - Anthropic (`AnthropicLLMClient`) — kept in the codebase, inactive by
    default. Set AURA_PROVIDER=anthropic (engine/config.py) to use it.

Swapping providers never touches any other module — pipeline.py, the
Writers' Room, and Song DNA generation all call `complete_json` on
whatever `create_default_client()` returns.
"""
from __future__ import annotations

import json
import re
from typing import Any

from . import config


class LLMError(RuntimeError):
    """Raised when the model cannot be reached or returns unparseable output."""


class LLMClient:
    """Shared retry/parsing logic. Subclasses implement `_call` only."""

    def complete_json(
        self, system: str, user: str, max_tokens: int | None = None
    ) -> dict[str, Any]:
        """Call the model and parse its reply as a single JSON object.

        Retries once with a corrective instruction if the first reply isn't
        valid JSON — models occasionally wrap JSON in prose or code fences
        despite instructions not to.
        """
        raw = self._call(system, user, max_tokens)
        parsed = self._try_parse(raw)
        if parsed is not None:
            return parsed

        corrective_user = (
            user
            + "\n\nYour previous reply could not be parsed as JSON. Reply again "
            "with ONLY a single valid JSON object — no prose, no markdown code "
            "fences, no commentary before or after it."
        )
        raw_retry = self._call(system, corrective_user, max_tokens)
        parsed_retry = self._try_parse(raw_retry)
        if parsed_retry is not None:
            return parsed_retry

        raise LLMError(
            "Model did not return parseable JSON after one retry. "
            f"Last reply:\n{raw_retry[:2000]}"
        )

    def _call(self, system: str, user: str, max_tokens: int | None) -> str:
        raise NotImplementedError

    @staticmethod
    def _try_parse(raw: str) -> dict[str, Any] | None:
        text = raw.strip()
        # Strip a ```json ... ``` or ``` ... ``` fence if the model added one.
        fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Fall back to the first {...} block in the text.
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                return None
        return None


class OpenAILLMClient(LLMClient):
    """Active default provider."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        import openai  # imported lazily so the anthropic-only path never needs this installed

        self.model = model or config.OPENAI_MODEL
        self._client = openai.OpenAI(
            api_key=api_key or config.get_api_key("openai"),
            timeout=config.LLM_TIMEOUT_SECONDS,
            max_retries=config.LLM_MAX_RETRIES,
        )

    def _call(self, system: str, user: str, max_tokens: int | None) -> str:
        import openai

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens or config.MAX_TOKENS,
                # Every prompt in this engine asks for a single JSON object;
                # JSON mode makes the model's decoder enforce that instead of
                # relying on the regex fence-stripping in _try_parse.
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except openai.APIError as exc:
            raise LLMError(f"OpenAI API call failed: {exc}") from exc
        return response.choices[0].message.content or ""


class AnthropicLLMClient(LLMClient):
    """Inactive by default (engine/config.py PROVIDER). Kept in the
    codebase rather than removed — set AURA_PROVIDER=anthropic to use it.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None):
        import anthropic  # imported lazily so the openai-only path never needs this installed

        self.model = model or config.ANTHROPIC_MODEL
        self._client = anthropic.Anthropic(api_key=api_key or config.get_api_key("anthropic"))

    def _call(self, system: str, user: str, max_tokens: int | None) -> str:
        import anthropic

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens or config.MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError as exc:
            raise LLMError(f"Anthropic API call failed: {exc}") from exc
        return "".join(
            block.text for block in response.content if block.type == "text"
        )


_PROVIDERS: dict[str, type[LLMClient]] = {
    "openai": OpenAILLMClient,
    "anthropic": AnthropicLLMClient,
}


def create_default_client() -> LLMClient:
    """Builds the client for whichever provider is active
    (config.PROVIDER / AURA_PROVIDER env var). Defaults to OpenAI.
    """
    provider = config.PROVIDER
    cls = _PROVIDERS.get(provider)
    if cls is None:
        raise RuntimeError(
            f"Unknown AURA_PROVIDER {provider!r}; expected one of {list(_PROVIDERS)}"
        )
    return cls()
