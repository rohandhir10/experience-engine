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
import time
from typing import Any

from . import config
from .models import LLMCallRecord


class LLMError(RuntimeError):
    """Raised when the model cannot be reached or returns unparseable output."""


class LLMClient:
    """Shared retry/parsing logic. Subclasses implement `_call` only.

    Subclasses must set `self.call_log: list[LLMCallRecord] = []` in their
    own __init__ before making any calls — see OpenAILLMClient/
    AnthropicLLMClient. Not set here in a base __init__ because neither
    subclass currently calls super().__init__(), and a base __init__ they
    never invoke would silently never run.
    """

    def complete_json(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
        stage: str = "unknown",
    ) -> dict[str, Any]:
        """Call the model and parse its reply as a single JSON object.

        Retries once with a corrective instruction if the first reply isn't
        valid JSON — models occasionally wrap JSON in prose or code fences
        despite instructions not to. `stage` labels which pipeline step this
        call belongs to (see LLMCallRecord) — purely for cost/latency
        accounting, never sent to the model or used in any decision.
        """
        raw = self._timed_call(system, user, max_tokens, stage, "initial")
        parsed = self._try_parse(raw)
        if parsed is not None:
            return parsed

        corrective_user = (
            user
            + "\n\nYour previous reply could not be parsed as JSON. Reply again "
            "with ONLY a single valid JSON object — no prose, no markdown code "
            "fences, no commentary before or after it."
        )
        raw_retry = self._timed_call(
            system, corrective_user, max_tokens, stage, "json_repair_retry"
        )
        parsed_retry = self._try_parse(raw_retry)
        if parsed_retry is not None:
            return parsed_retry

        raise LLMError(
            "Model did not return parseable JSON after one retry. "
            f"Last reply:\n{raw_retry[:2000]}"
        )

    def _timed_call(
        self,
        system: str,
        user: str,
        max_tokens: int | None,
        stage: str,
        attempt: str,
    ) -> str:
        started = time.perf_counter()
        text, prompt_tokens, completion_tokens = self._call(system, user, max_tokens)
        elapsed = time.perf_counter() - started
        self.call_log.append(
            LLMCallRecord(
                stage=stage,
                model=getattr(self, "model", "unknown"),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_seconds=round(elapsed, 3),
                attempt=attempt,  # type: ignore[arg-type]
            )
        )
        return text

    def _call(self, system: str, user: str, max_tokens: int | None) -> tuple[str, int, int]:
        """Returns (response_text, prompt_tokens, completion_tokens) — the
        token counts come from the provider's own response, never counted
        or estimated locally.
        """
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
        import httpx
        import openai  # imported lazily so the anthropic-only path never needs this installed

        self.model = model or config.OPENAI_MODEL
        self.call_log: list[LLMCallRecord] = []
        http_client = None
        if config.FORCE_IPV4:
            # Some containerized/serverless environments (seen: a Vercel
            # Python function) have broken or unreachable IPv6 egress —
            # a connection attempt that tries an IPv6 address first fails
            # almost instantly ("no route to host"), which looks exactly
            # like the fast, repeated "Connection error." failures this
            # was added for, rather than a slow timeout. Binding the local
            # address forces httpx to resolve and connect over IPv4 only.
            # A hypothesis, not a confirmed diagnosis — AURA_FORCE_IPV4=0
            # disables this if it turns out not to be the cause.
            http_client = httpx.Client(
                transport=httpx.HTTPTransport(local_address="0.0.0.0")
            )
        self._client = openai.OpenAI(
            api_key=api_key or config.get_api_key("openai"),
            timeout=config.LLM_TIMEOUT_SECONDS,
            max_retries=config.LLM_MAX_RETRIES,
            http_client=http_client,
        )

    def _call(self, system: str, user: str, max_tokens: int | None) -> tuple[str, int, int]:
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
            # openai's own str(exc) for a connection failure is just
            # "Connection error." — it discards the actual httpx/socket
            # exception (DNS failure, TLS failure, refused connection are
            # all indistinguishable at that point). __cause__ holds the
            # real one; surface it rather than guessing at the failure
            # mode from a message that can't tell them apart.
            detail = f"{type(exc.__cause__).__name__}: {exc.__cause__}" if exc.__cause__ else "no underlying exception captured"
            raise LLMError(f"OpenAI API call failed: {exc} | underlying: {detail}") from exc
        text = response.choices[0].message.content or ""
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        return text, prompt_tokens, completion_tokens


class AnthropicLLMClient(LLMClient):
    """Inactive by default (engine/config.py PROVIDER). Kept in the
    codebase rather than removed — set AURA_PROVIDER=anthropic to use it.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None):
        import anthropic  # imported lazily so the openai-only path never needs this installed

        self.model = model or config.ANTHROPIC_MODEL
        self.call_log: list[LLMCallRecord] = []
        self._client = anthropic.Anthropic(api_key=api_key or config.get_api_key("anthropic"))

    def _call(self, system: str, user: str, max_tokens: int | None) -> tuple[str, int, int]:
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
        text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        usage = response.usage
        prompt_tokens = usage.input_tokens if usage else 0
        completion_tokens = usage.output_tokens if usage else 0
        return text, prompt_tokens, completion_tokens


_PROVIDERS: dict[str, type[LLMClient]] = {
    "openai": OpenAILLMClient,
    "anthropic": AnthropicLLMClient,
}


def create_default_client(model: str | None = None) -> LLMClient:
    """Builds the client for whichever provider is active
    (config.PROVIDER / AURA_PROVIDER env var). Defaults to OpenAI.

    `model` overrides that provider's default model (e.g. a cheaper model
    for a lower-stakes call like server/mapping.py's explain_why) — still
    the same provider, just a different model name from the same class.
    """
    provider = config.PROVIDER
    cls = _PROVIDERS.get(provider)
    if cls is None:
        raise RuntimeError(
            f"Unknown AURA_PROVIDER {provider!r}; expected one of {list(_PROVIDERS)}"
        )
    return cls(model=model) if model else cls()
