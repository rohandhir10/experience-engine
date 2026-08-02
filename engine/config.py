"""Engine-wide configuration, all overridable via environment variables.

PROVIDER selects which model adapter engine/llm_client.py builds by
default. OpenAI is the active default; Anthropic is kept in the codebase
but inactive — set AURA_PROVIDER=anthropic to switch back to it.
"""
import os

PROVIDER = os.environ.get("AURA_PROVIDER", "openai")  # "openai" (active) | "anthropic" (inactive)

OPENAI_MODEL = os.environ.get("AURA_OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL = os.environ.get("AURA_ANTHROPIC_MODEL", "claude-sonnet-5")
MAX_TOKENS = int(os.environ.get("AURA_MAX_TOKENS", "4096"))

# Per-request timeout and SDK-level retry budget for LLM calls. A full
# section can legitimately take a while, but a call that hangs past this
# is dead — fail it and let the engine's own error handling surface it.
LLM_TIMEOUT_SECONDS = float(os.environ.get("AURA_LLM_TIMEOUT", "120"))
LLM_MAX_RETRIES = int(os.environ.get("AURA_LLM_MAX_RETRIES", "2"))

# See engine/llm_client.py::OpenAILLMClient — forces the OpenAI HTTP client
# to connect over IPv4 only, a mitigation for environments with broken
# IPv6 egress. On by default; set to "0" to rule it out if it isn't the
# actual cause of a connection failure.
FORCE_IPV4 = os.environ.get("AURA_FORCE_IPV4", "1") != "0"

_API_KEY_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def get_api_key(provider: str | None = None) -> str:
    provider = provider or PROVIDER
    env_var = _API_KEY_ENV_VARS.get(provider)
    if env_var is None:
        raise RuntimeError(
            f"Unknown provider {provider!r}; expected one of {list(_API_KEY_ENV_VARS)}"
        )
    key = os.environ.get(env_var)
    if key is not None:
        # A trailing space or newline is a common copy-paste artifact when
        # setting an env var through a dashboard UI (confirmed in
        # production: Vercel). It's invisible in most UIs, but it turns
        # the Authorization header into something httpx's HTTP layer
        # rejects outright as malformed — "LocalProtocolError: Illegal
        # header value" — before any request is even sent, which looks
        # exactly like a fast, repeated connection failure and is very
        # hard to diagnose from that alone. Stripping here removes an
        # entire class of "the key is right but it still doesn't work"
        # bug reports.
        key = key.strip()
    if not key:
        raise RuntimeError(
            f"{env_var} is not set. Export it before running the engine, "
            f"e.g.: export {env_var}=..."
        )
    return key
