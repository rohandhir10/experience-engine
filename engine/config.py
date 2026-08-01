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
    if not key:
        raise RuntimeError(
            f"{env_var} is not set. Export it before running the engine, "
            f"e.g.: export {env_var}=..."
        )
    return key
