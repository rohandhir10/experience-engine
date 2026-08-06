"""Engine-wide configuration, all overridable via environment variables.

PROVIDER selects which model adapter engine/llm_client.py builds by
default. OpenAI is the active default; Anthropic is kept in the codebase
but inactive — set CASTIA_PROVIDER=anthropic to switch back to it.
"""
import os

PROVIDER = os.environ.get("CASTIA_PROVIDER", "openai")  # "openai" (active) | "anthropic" (inactive)

OPENAI_MODEL = os.environ.get("CASTIA_OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL = os.environ.get("CASTIA_ANTHROPIC_MODEL", "claude-sonnet-5")
MAX_TOKENS = int(os.environ.get("CASTIA_MAX_TOKENS", "4096"))

# server/mapping.py::_explain_why — the reader-facing "why this changed"
# sentence. Presentation, not adaptation reasoning: it doesn't touch the
# engine's own output, so it's the lowest-risk place to use a cheaper
# model. Defaults to a cheaper OpenAI model only when OpenAI is actually
# the active provider — if CASTIA_PROVIDER=anthropic, there's no hardcoded
# "cheap Anthropic model" assumption here, so it falls back to the same
# model as everything else rather than silently guessing at one.
#
# Provisional, not yet quality-validated: this should be confirmed against
# a real side-by-side test (a blind sample of explanations, same songs,
# both models) before being trusted as a free win. Set
# CASTIA_EXPLAIN_WHY_MODEL to the main model to revert instantly if that
# test doesn't hold up.
EXPLAIN_WHY_MODEL = os.environ.get(
    "CASTIA_EXPLAIN_WHY_MODEL",
    "gpt-4o-mini" if PROVIDER == "openai" else ANTHROPIC_MODEL,
)

# Per-request timeout and SDK-level retry budget for LLM calls. A full
# section can legitimately take a while, but a call that hangs past this
# is dead — fail it and let the engine's own error handling surface it.
LLM_TIMEOUT_SECONDS = float(os.environ.get("CASTIA_LLM_TIMEOUT", "120"))
LLM_MAX_RETRIES = int(os.environ.get("CASTIA_LLM_MAX_RETRIES", "2"))

# See engine/llm_client.py::OpenAILLMClient — forces the OpenAI HTTP client
# to connect over IPv4 only, a mitigation for environments with broken
# IPv6 egress. On by default; set to "0" to rule it out if it isn't the
# actual cause of a connection failure.
FORCE_IPV4 = os.environ.get("CASTIA_FORCE_IPV4", "1") != "0"

# engine/comics_vision.py — a vision-capable model reading comic panels
# alongside Cloud Vision's OCR (see that module's docstring). Off by
# default: it adds a real per-panel model call with real cost, and the
# OCR path works without it, so this is opted into deliberately rather
# than switched on for every deployment by a code update.
VISION_READING_ENABLED = os.environ.get("CASTIA_VISION_READING", "0") == "1"

# Must be a model that accepts image input. Kept separate from
# OPENAI_MODEL so the text pipeline's model can be changed (or pinned to
# something cheap) without silently breaking panel reading by pointing it
# at a text-only model.
VISION_MODEL = os.environ.get(
    "CASTIA_VISION_MODEL",
    "gpt-4o" if PROVIDER == "openai" else ANTHROPIC_MODEL,
)

# engine/comics_recognize.py — manga-ocr, a Japanese-manga-specific text
# recogniser. Off by default and deliberately so: it depends on torch and
# transformers, which take this project's python:3.11-slim image from a
# couple of hundred megabytes to several gigabytes, and it downloads model
# weights from Hugging Face on first use. Neither is an assumption to make
# about a deployment by default.
MANGA_OCR_ENABLED = os.environ.get("CASTIA_MANGA_OCR", "0") == "1"

# Preferred over the in-process option above when set: the URL of a
# recogniser running as its own service, so the torch dependency never
# enters the API container at all. Takes precedence over
# MANGA_OCR_ENABLED.
MANGA_OCR_URL = os.environ.get("CASTIA_MANGA_OCR_URL", "")

# engine/comics_detect.py — a text-region detector running as its own
# service (comic-text-detector, a YOLO bubble model, or similar). Unset
# means detection falls back to deriving boxes from the Cloud Vision call
# the pipeline already makes.
TEXT_DETECTOR_URL = os.environ.get("CASTIA_TEXT_DETECTOR_URL", "")

# engine/comics_inpaint.py — a LaMa/IOPaint inpainting service for
# reconstructing artwork behind erased comic text. Unset means the local
# OpenCV Telea fill, which needs no weights, no network and no service:
# genuinely adequate on plain speech bubbles, and visibly smeary on text
# over drawn artwork, which is what the remote model is for.
INPAINT_URL = os.environ.get("CASTIA_INPAINT_URL", "")
# Generous by default: a LaMa pass on a full page is real GPU work, and a
# timeout here costs redraw QUALITY (it falls back to OpenCV), not the
# request itself.
INPAINT_TIMEOUT_SECONDS = float(os.environ.get("CASTIA_INPAINT_TIMEOUT", "60"))
# How many times RemoteInpainter retries a TRANSPORT failure (connection
# error, timeout) before giving up and falling back to local OpenCV -
# same idea as LLM_MAX_RETRIES above, for the same reason: a single
# network blip shouldn't permanently downgrade this redraw's quality
# when trying again costs nothing but a little time. Does NOT apply to a
# response the service actually returned (wrong dimensions, unreadable
# body) - that's not the kind of failure a retry fixes.
INPAINT_MAX_RETRIES = int(os.environ.get("CASTIA_INPAINT_MAX_RETRIES", "1"))

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
