"""Engine-wide configuration, all overridable via environment variables."""
import os

ANTHROPIC_MODEL = os.environ.get("AURA_MODEL", "claude-sonnet-5")
MAX_TOKENS = int(os.environ.get("AURA_MAX_TOKENS", "4096"))
API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"


def get_api_key() -> str:
    key = os.environ.get(API_KEY_ENV_VAR)
    if not key:
        raise RuntimeError(
            f"{API_KEY_ENV_VAR} is not set. Export it before running the engine, "
            "e.g.: export ANTHROPIC_API_KEY=sk-ant-..."
        )
    return key
