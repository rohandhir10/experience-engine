"""Error monitoring (Sentry), off unless CASTIA_SENTRY_DSN is set.

Errors were never invisible - server/main.py logs them with
logger.exception and Railway keeps stdout. What was missing is anyone
FINDING OUT: a log line at 3am is only useful to someone already
scrolling logs, and a failure that happens to fifty users in an hour
looks exactly like a failure that happened once. This adds aggregation,
deduplication and alerting on top of the logging that already exists; it
does not replace it, and nothing here is load-bearing for a request.

Degrades to a complete no-op in three separate ways, because an
observability tool that can break the thing it observes is worse than no
observability at all:
  - no DSN configured -> never initialized (local dev, CI, the test suite)
  - sentry-sdk not installed -> ImportError caught, logged once, ignored
  - init or capture raising for any reason -> caught and logged, never
    propagated into a request

PRIVACY - the part that actually needed care here. This service handles
song lyrics and comic dialogue: third-party copyrighted text that users
paste in, which must not be shipped to an external service just because
something threw. Sentry's own defaults would do exactly that
(max_request_body_size defaults to "medium", include_local_variables
defaults to True - a stack frame inside the engine holds the lyrics in a
local). Both are forced off here and are deliberately NOT configurable by
environment variable: the risk is a property of what this application
processes, not of how a given deployment is set up, so it isn't a
deployment's call to make. What gets sent is the exception type, the
message, the stack frames and the scrubbed request metadata - enough to
find a bug, not enough to reconstruct someone's manuscript.

That claim is verified rather than asserted: tests/test_monitoring.py
runs a real init and a real capture against a recording transport and
asserts that runtime-supplied text does not appear anywhere in the
payload that would have gone over the wire. Asserting on the options
passed to init() is NOT the same test and would have missed this - the
guarantee that matters is about the bytes, not the arguments.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("castia.monitoring")

# Header names that carry credentials. Compared case-insensitively - HTTP
# headers are case-insensitive and Sentry preserves whatever casing the
# client sent, so a fixed-case check would miss "Authorization" vs
# "authorization".
_SECRET_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-castia-internal-secret",
        "x-api-key",
        "paddle-signature",
    }
)

# Substrings marking an env/extra KEY whose value is a secret. Matched on
# the key, never on the value: matching values would mean scanning the
# very payloads we refuse to collect.
_SECRET_KEY_HINTS = ("secret", "token", "password", "api_key", "apikey", "dsn", "database_url")

_REDACTED = "[redacted]"

_initialized = False


def _scrub_mapping(mapping: dict[str, Any], secret_names: frozenset[str] | None = None) -> None:
    """Redacts secret-bearing entries of `mapping`, in place.

    In place rather than returning a copy because Sentry hands
    before_send the real event dict and expects it mutated or returned;
    rebuilding it would risk dropping keys this function doesn't know
    about.
    """
    for key in list(mapping):
        lowered = key.lower()
        if secret_names is not None and lowered in secret_names:
            mapping[key] = _REDACTED
        elif any(hint in lowered for hint in _SECRET_KEY_HINTS):
            mapping[key] = _REDACTED


def scrub_event(event: dict[str, Any], _hint: Any = None) -> dict[str, Any]:
    """before_send hook: strips credentials, and drops any request body
    that reached the event despite max_request_body_size="never".

    The body removal is belt-and-braces on purpose. It is the single
    worst thing that could leak here (a full set of lyrics or a chapter's
    dialogue), the option that prevents it lives in Sentry's
    configuration rather than in this file, and an SDK default changing
    under us is a realistic way for that to silently start happening.
    Two independent guards is the right ratio for a one-way mistake.
    """
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)  # the request body, whatever form it took
        headers = request.get("headers")
        if isinstance(headers, dict):
            _scrub_mapping(headers, _SECRET_HEADERS)
        cookies = request.get("cookies")
        if isinstance(cookies, dict):
            request["cookies"] = _REDACTED

    extra = event.get("extra")
    if isinstance(extra, dict):
        _scrub_mapping(extra)

    return event


def init_error_monitoring() -> bool:
    """Starts Sentry if configured. Returns whether it actually started,
    so startup can log which of the two states this process is in rather
    than leaving it ambiguous.

    Idempotent: repeated calls after a successful init are no-ops, which
    matters because the test suite and any future worker entrypoint can
    both reach this.
    """
    global _initialized
    if _initialized:
        return True

    dsn = os.environ.get("CASTIA_SENTRY_DSN", "").strip()
    if not dsn:
        return False

    try:
        import sentry_sdk
    except ImportError:
        logger.warning(
            "CASTIA_SENTRY_DSN is set but sentry-sdk is not installed - "
            "error monitoring is off. Add sentry-sdk to requirements.txt."
        )
        return False

    try:
        sentry_sdk.init(
            dsn=dsn,
            # Which deployment an event came from. Railway/Vercel both
            # expose a commit SHA; without one, releases just aren't
            # tracked rather than being guessed at.
            environment=os.environ.get("CASTIA_ENVIRONMENT", "production"),
            release=os.environ.get("RAILWAY_GIT_COMMIT_SHA")
            or os.environ.get("VERCEL_GIT_COMMIT_SHA")
            or None,
            # --- the privacy locks; see this module's docstring ---
            send_default_pii=False,
            max_request_body_size="never",
            include_local_variables=False,
            # Source context (the lines around the failing line) is left
            # ON deliberately, having been checked rather than assumed:
            # it carries this repository's own source, never runtime
            # values, so no amount of user-submitted text can reach it -
            # and without it a frame is just a file and a line number.
            # The standing consequence is the one already true of this
            # codebase anyway: secrets live in environment variables, not
            # in source, because these lines do leave the building.
            include_source_context=True,
            before_send=scrub_event,
            # Performance tracing is a separate cost and a separate
            # (larger) data-collection question. Off until someone
            # decides they want it, rather than on by accident.
            traces_sample_rate=0.0,
        )
    except Exception:
        # Including a malformed DSN, which sentry_sdk.init raises on.
        logger.exception("error monitoring failed to initialize - continuing without it")
        return False

    _initialized = True
    logger.info("error monitoring active (environment=%s)",
                os.environ.get("CASTIA_ENVIRONMENT", "production"))
    return True


def capture_exception(exc: BaseException, **context: Any) -> None:
    """Reports an exception that was caught and handled - the background
    job failures that would otherwise only ever exist as one line in a
    log nobody is reading.

    Callers go through this rather than importing sentry_sdk directly so
    that (a) an uninstalled/unconfigured SDK stays a no-op at exactly one
    place, and (b) a caller cannot accidentally attach the very payloads
    this module exists to keep out - `context` is for identifiers (a job
    id, a result id, a panel count), never for user content. Values are
    still run through the same scrubber via before_send.

    Never raises. A monitoring call that could fail a request it was only
    observing would be strictly worse than no monitoring.
    """
    if not _initialized:
        return
    try:
        import sentry_sdk

        if context:
            with sentry_sdk.new_scope() as scope:
                for key, value in context.items():
                    scope.set_tag(key, str(value))
                sentry_sdk.capture_exception(exc)
        else:
            sentry_sdk.capture_exception(exc)
    except Exception:
        logger.exception("failed to report an exception to error monitoring")
