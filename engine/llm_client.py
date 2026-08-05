"""LLM adapters used by every stage of the engine.

Every prompt in this engine asks the model to return a single JSON object.
This module owns the one place that calls a model provider and parses that
JSON, so every other module works with plain Python data, never raw model
text — and so no other module needs to know or care which provider is
actually behind `client.complete_json(...)`.

Two providers are implemented:
  - OpenAI (`OpenAILLMClient`) — the active default.
  - Anthropic (`AnthropicLLMClient`) — kept in the codebase, inactive by
    default. Set CASTIA_PROVIDER=anthropic (engine/config.py) to use it.

Swapping providers never touches any other module — pipeline.py, the
Writers' Room, and Song DNA generation all call `complete_json` on
whatever `create_default_client()` returns.
"""
from __future__ import annotations

import json
import re
import threading
import time
from typing import Any

from . import config
from .models import LLMCallRecord


class LLMError(RuntimeError):
    """Raised when the model cannot be reached or returns unparseable output."""


# Provider SDK clients (openai.OpenAI / anthropic.Anthropic), shared
# across LLMClient instances. Each SDK client owns an httpx connection
# pool; before this cache, every create_default_client() call — twice
# per adaptation request (main model + explain-why model), plus one per
# background job — built a fresh pool, so under concurrent load nothing
# ever reused a keep-alive connection and socket/file-descriptor usage
# multiplied with request count instead of stabilizing (flagged in
# docs/CAPABILITY_MATRIX.md's scalability audit). Both SDK clients are
# documented thread-safe. Keyed by everything that changes the
# constructed client (provider, api key, timeout, retries, transport),
# so a test or env change that alters any of them gets its own client
# rather than a stale cached one. The wrapper LLMClient instances stay
# per-request — call_log is per-instance accounting and must not be
# shared.
_sdk_clients: dict[tuple, Any] = {}
_sdk_clients_lock = threading.Lock()


def _shared_sdk_client(cache_key: tuple, build) -> Any:
    with _sdk_clients_lock:
        client = _sdk_clients.get(cache_key)
        if client is None:
            client = build()
            _sdk_clients[cache_key] = client
        return client


class LLMClient:
    """Shared retry/parsing logic. Subclasses implement `_call` only.

    Subclasses must set `self.call_log: list[LLMCallRecord] = []` in their
    own __init__ before making any calls — see OpenAILLMClient/
    AnthropicLLMClient. Not set here in a base __init__ because neither
    subclass currently calls super().__init__(), and a base __init__ they
    never invoke would silently never run.
    """

    def complete_json_with_image(
        self,
        system: str,
        user: str,
        image_data_url: str,
        max_tokens: int | None = None,
        stage: str = "unknown",
    ) -> dict[str, Any]:
        """Same contract as complete_json, with one image attached.

        A separate named entry point rather than just a keyword argument
        on complete_json, so an image call is obvious at the call site -
        it costs meaningfully more than a text call and only works on a
        vision-capable model (config.VISION_MODEL).
        """
        return self.complete_json(
            system, user, max_tokens=max_tokens, stage=stage, image_data_url=image_data_url
        )

    def complete_json(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
        stage: str = "unknown",
        image_data_url: str | None = None,
    ) -> dict[str, Any]:
        """Call the model and parse its reply as a single JSON object.

        Retries once with a corrective instruction if the first reply isn't
        valid JSON — models occasionally wrap JSON in prose or code fences
        despite instructions not to. `stage` labels which pipeline step this
        call belongs to (see LLMCallRecord) — purely for cost/latency
        accounting, never sent to the model or used in any decision.
        """
        raw = self._timed_call(
            system, user, max_tokens, stage, "initial", image_data_url
        )
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
            system, corrective_user, max_tokens, stage, "json_repair_retry", image_data_url
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
        image_data_url: str | None = None,
    ) -> str:
        started = time.perf_counter()
        if image_data_url:
            text, prompt_tokens, completion_tokens = self._call_with_image(
                system, user, image_data_url, max_tokens
            )
        else:
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

    def _call_with_image(
        self, system: str, user: str, image_data_url: str, max_tokens: int | None
    ) -> tuple[str, int, int]:
        """Same contract as _call, with one image attached to the user
        turn. Only implemented by providers whose configured model can
        accept image input.
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
        resolved_key = api_key or config.get_api_key("openai")
        cache_key = (
            "openai",
            resolved_key,
            config.LLM_TIMEOUT_SECONDS,
            config.LLM_MAX_RETRIES,
            config.FORCE_IPV4,
        )

        def _build() -> openai.OpenAI:
            http_client = None
            if config.FORCE_IPV4:
                # Some containerized/serverless environments (seen: a Vercel
                # Python function) have broken or unreachable IPv6 egress —
                # a connection attempt that tries an IPv6 address first fails
                # almost instantly ("no route to host"), which looks exactly
                # like the fast, repeated "Connection error." failures this
                # was added for, rather than a slow timeout. Binding the local
                # address forces httpx to resolve and connect over IPv4 only.
                # A hypothesis, not a confirmed diagnosis — CASTIA_FORCE_IPV4=0
                # disables this if it turns out not to be the cause.
                http_client = httpx.Client(
                    transport=httpx.HTTPTransport(local_address="0.0.0.0")
                )
            return openai.OpenAI(
                api_key=resolved_key,
                timeout=config.LLM_TIMEOUT_SECONDS,
                max_retries=config.LLM_MAX_RETRIES,
                http_client=http_client,
            )

        # Shared across instances — the SDK client (and its connection
        # pool) is model-agnostic, since the model name is passed per
        # request in _call. See _sdk_clients above.
        self._client = _shared_sdk_client(cache_key, _build)

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

    def _call_with_image(
        self, system: str, user: str, image_data_url: str, max_tokens: int | None
    ) -> tuple[str, int, int]:
        import openai

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens or config.MAX_TOKENS,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user},
                            {"type": "image_url", "image_url": {"url": image_data_url}},
                        ],
                    },
                ],
            )
        except openai.APIError as exc:
            detail = (
                f"{type(exc.__cause__).__name__}: {exc.__cause__}"
                if exc.__cause__
                else "no underlying exception captured"
            )
            raise LLMError(
                f"OpenAI vision call failed: {exc} | underlying: {detail}"
            ) from exc
        text = response.choices[0].message.content or ""
        usage = response.usage
        return text, (usage.prompt_tokens if usage else 0), (usage.completion_tokens if usage else 0)


class AnthropicLLMClient(LLMClient):
    """Inactive by default (engine/config.py PROVIDER). Kept in the
    codebase rather than removed — set CASTIA_PROVIDER=anthropic to use it.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None):
        import anthropic  # imported lazily so the openai-only path never needs this installed

        self.model = model or config.ANTHROPIC_MODEL
        self.call_log: list[LLMCallRecord] = []
        resolved_key = api_key or config.get_api_key("anthropic")
        # Same shared-SDK-client discipline as OpenAILLMClient above.
        self._client = _shared_sdk_client(
            ("anthropic", resolved_key),
            lambda: anthropic.Anthropic(api_key=resolved_key),
        )

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

    def _call_with_image(
        self, system: str, user: str, image_data_url: str, max_tokens: int | None
    ) -> tuple[str, int, int]:
        import anthropic

        # Anthropic takes the media type and raw base64 as separate
        # fields rather than a single data: URL, so unpack it here rather
        # than making every caller know which provider is active.
        media_type, _, encoded = image_data_url.partition(";base64,")
        media_type = media_type.removeprefix("data:")
        if not encoded:
            raise LLMError("Image must be a base64 data: URL for the Anthropic provider.")

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens or config.MAX_TOKENS,
                system=system,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": encoded,
                                },
                            },
                            {"type": "text", "text": user},
                        ],
                    }
                ],
            )
        except anthropic.APIError as exc:
            raise LLMError(f"Anthropic vision call failed: {exc}") from exc
        text = "".join(block.text for block in response.content if block.type == "text")
        usage = response.usage
        return text, (usage.input_tokens if usage else 0), (usage.output_tokens if usage else 0)


_PROVIDERS: dict[str, type[LLMClient]] = {
    "openai": OpenAILLMClient,
    "anthropic": AnthropicLLMClient,
}


def create_default_client(model: str | None = None) -> LLMClient:
    """Builds the client for whichever provider is active
    (config.PROVIDER / CASTIA_PROVIDER env var). Defaults to OpenAI.

    `model` overrides that provider's default model (e.g. a cheaper model
    for a lower-stakes call like server/mapping.py's explain_why) — still
    the same provider, just a different model name from the same class.
    """
    provider = config.PROVIDER
    cls = _PROVIDERS.get(provider)
    if cls is None:
        raise RuntimeError(
            f"Unknown CASTIA_PROVIDER {provider!r}; expected one of {list(_PROVIDERS)}"
        )
    return cls(model=model) if model else cls()


def create_vision_client() -> LLMClient:
    """Builds a client pinned to config.VISION_MODEL - a model that can
    accept image input (engine/comics_vision.py).

    Separate from create_default_client so the text pipeline's model can
    be changed, or pointed at something cheap, without silently breaking
    panel reading by aiming it at a text-only model.
    """
    return create_default_client(model=config.VISION_MODEL)
