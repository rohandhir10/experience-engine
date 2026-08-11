"""Tests for server/monitoring.py.

Two things are being pinned down here, and the second matters more than
the first.

1. It must never be able to break the thing it observes: no DSN, a
   missing SDK, a malformed DSN or a capture that throws all have to end
   in a no-op, never an exception reaching a request or a background job.

2. It must not leak the content this service handles. Users paste song
   lyrics and comic dialogue - third-party copyrighted text - and
   Sentry's own defaults would ship it: max_request_body_size defaults to
   "medium" and include_local_variables defaults to True, and a stack
   frame inside the engine holds the lyrics in a local variable. These
   tests fail if either lock is ever removed, which is the point: that
   regression would be completely invisible in normal use, and would only
   be discovered by reading someone's manuscript out of an error report.
"""
from __future__ import annotations

import pytest

from server import monitoring


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(monitoring, "_initialized", False)
    monkeypatch.delenv("CASTIA_SENTRY_DSN", raising=False)


# --- Never breaks the thing it observes -------------------------------


def test_does_nothing_without_a_dsn():
    assert monitoring.init_error_monitoring() is False


def test_a_blank_or_whitespace_dsn_counts_as_unset(monkeypatch):
    monkeypatch.setenv("CASTIA_SENTRY_DSN", "   ")
    assert monitoring.init_error_monitoring() is False


def test_a_malformed_dsn_is_swallowed_rather_than_crashing_startup(monkeypatch):
    """init runs inside the FastAPI lifespan - a typo'd DSN must not stop
    the service from coming up."""
    monkeypatch.setenv("CASTIA_SENTRY_DSN", "not-a-valid-dsn")
    assert monitoring.init_error_monitoring() is False


def test_a_missing_sdk_is_reported_once_and_ignored(monkeypatch):
    """The package is in requirements.txt, but an image built without it
    must still serve traffic."""
    import builtins

    real_import = builtins.__import__

    def no_sentry(name, *args, **kwargs):
        if name == "sentry_sdk":
            raise ImportError("no sentry_sdk")
        return real_import(name, *args, **kwargs)

    monkeypatch.setenv("CASTIA_SENTRY_DSN", "https://public@o0.ingest.sentry.io/0")
    monkeypatch.setattr(builtins, "__import__", no_sentry)
    assert monitoring.init_error_monitoring() is False


def test_capture_exception_is_a_no_op_when_uninitialized():
    monitoring.capture_exception(ValueError("boom"), job_id="abc")


def test_capture_exception_never_raises_even_if_the_sdk_throws(monkeypatch):
    import sentry_sdk

    monkeypatch.setattr(monitoring, "_initialized", True)

    def explode(*args, **kwargs):
        raise RuntimeError("sentry itself is broken")

    monkeypatch.setattr(sentry_sdk, "capture_exception", explode)
    # Must return normally: this is called from an `except` block that has
    # already decided how the job fails.
    monitoring.capture_exception(ValueError("boom"))


def test_init_is_idempotent(monkeypatch):
    monkeypatch.setattr(monitoring, "_initialized", True)
    assert monitoring.init_error_monitoring() is True


# --- The privacy locks -------------------------------------------------


def _init_capturing_options(monkeypatch) -> dict:
    """Runs a real init against a syntactically valid DSN, capturing the
    options actually handed to sentry_sdk.init rather than asserting on
    what this module's source says it passes."""
    import sentry_sdk

    captured: dict = {}
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setenv("CASTIA_SENTRY_DSN", "https://public@o0.ingest.sentry.io/0")
    assert monitoring.init_error_monitoring() is True
    return captured


def test_request_bodies_are_never_collected(monkeypatch):
    """The single worst leak available here: a request body IS the
    lyrics/dialogue. Sentry's default for this is "medium", i.e. on."""
    assert _init_capturing_options(monkeypatch)["max_request_body_size"] == "never"


def test_stack_frame_locals_are_never_collected(monkeypatch):
    """Sentry defaults this to True. An exception raised inside the
    engine has the full lyrics sitting in a local variable one frame up."""
    assert _init_capturing_options(monkeypatch)["include_local_variables"] is False


def test_default_pii_is_off(monkeypatch):
    assert _init_capturing_options(monkeypatch)["send_default_pii"] is False


def test_a_scrubber_is_installed(monkeypatch):
    assert _init_capturing_options(monkeypatch)["before_send"] is monitoring.scrub_event


def test_performance_tracing_is_off_by_default(monkeypatch):
    """Separate cost and a larger data-collection question - off until
    somebody decides they want it, rather than on by accident."""
    assert _init_capturing_options(monkeypatch)["traces_sample_rate"] == 0.0


# --- The scrubber itself ----------------------------------------------


def test_scrubber_drops_the_request_body_outright():
    event = {"request": {"data": "Verse 1: the actual copyrighted lyrics"}}
    assert "data" not in monitoring.scrub_event(event)["request"]


def test_scrubber_redacts_credential_headers_case_insensitively():
    event = {
        "request": {
            "headers": {
                "Authorization": "Bearer sk_live_realkey",
                "X-Castia-Internal-Secret": "the-internal-secret",
                "Cookie": "session=abc",
                "User-Agent": "Mozilla/5.0",
            }
        }
    }
    headers = monitoring.scrub_event(event)["request"]["headers"]
    assert headers["Authorization"] == "[redacted]"
    assert headers["X-Castia-Internal-Secret"] == "[redacted]"
    assert headers["Cookie"] == "[redacted]"
    # Non-secret headers survive - they're how you debug the thing.
    assert headers["User-Agent"] == "Mozilla/5.0"


def test_scrubber_redacts_cookies_wholesale():
    event = {"request": {"cookies": {"next-auth.session-token": "a-real-session"}}}
    assert monitoring.scrub_event(event)["request"]["cookies"] == "[redacted]"


def test_scrubber_redacts_secret_looking_extra_keys():
    event = {
        "extra": {
            "DATABASE_URL": "postgresql://user:hunter2@host/db",
            "RESEND_API_KEY": "re_live_xxx",
            "paddle_webhook_secret": "pdl_xxx",
            "job_id": "abc123",
            "panel_count": 22,
        }
    }
    extra = monitoring.scrub_event(event)["extra"]
    assert extra["DATABASE_URL"] == "[redacted]"
    assert extra["RESEND_API_KEY"] == "[redacted]"
    assert extra["paddle_webhook_secret"] == "[redacted]"
    # Identifiers are the whole point of attaching context - they stay.
    assert extra["job_id"] == "abc123"
    assert extra["panel_count"] == 22


def test_scrubber_handles_an_event_with_none_of_these_sections():
    assert monitoring.scrub_event({"message": "hi"}) == {"message": "hi"}


def test_scrubber_tolerates_unexpected_shapes_without_raising():
    """before_send runs inside the SDK on every event - raising there
    would turn one error into two."""
    for weird in ({"request": "not-a-dict"}, {"request": {"headers": None}}, {"extra": []}):
        monitoring.scrub_event(weird)


def test_a_real_secret_never_survives_a_round_trip():
    """End-to-end falsification: dump the scrubbed event and confirm the
    literal secret strings are absent from the whole payload, not just
    from the keys we happened to assert on."""
    import json

    event = {
        "request": {
            "data": "SECRET_LYRICS_TEXT",
            "headers": {"authorization": "Bearer SECRET_API_KEY"},
            "cookies": {"session": "SECRET_SESSION"},
        },
        "extra": {"database_url": "postgres://u:SECRET_PASSWORD@h/d"},
    }
    dumped = json.dumps(monitoring.scrub_event(event))
    for secret in ("SECRET_LYRICS_TEXT", "SECRET_API_KEY", "SECRET_SESSION", "SECRET_PASSWORD"):
        assert secret not in dumped, secret


# --- The guarantee, verified on the payload rather than the arguments --
#
# Everything above this line asserts what gets PASSED to sentry_sdk.init.
# That is necessary and insufficient: it would keep passing if an SDK
# default changed, if an option were renamed, or if some other mechanism
# collected the same data by another route. These run a real init and a
# real capture against a recording transport and look at the payload that
# would actually have been transmitted.


def _capture_payload(monkeypatch, fn) -> str:
    """Runs `fn` (which must raise), captures the exception through the
    real SDK with the network replaced by a recorder, and returns the
    serialized payload that would have been sent."""
    import json

    import sentry_sdk

    sent: list = []
    real_init = sentry_sdk.init
    monkeypatch.setattr(
        sentry_sdk, "init",
        lambda **kw: real_init(**{**kw, "transport": lambda event: sent.append(event)}),
    )
    monkeypatch.setenv("CASTIA_SENTRY_DSN", "https://public@o0.ingest.sentry.io/0")
    monkeypatch.setattr(monitoring, "_initialized", False)
    assert monitoring.init_error_monitoring() is True

    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - the whole point
        monitoring.capture_exception(exc, job_id="job-123", kind="song_adapt")
    sentry_sdk.flush(timeout=2)

    assert sent, "nothing was captured"
    return json.dumps(sent, default=str)


def test_runtime_user_text_never_reaches_the_payload(monkeypatch, tmp_path):
    """The guarantee that actually matters. The text arrives at runtime
    and is held in a local exactly the way the engine holds lyrics - it
    must not appear anywhere in what would be transmitted.

    The token is generated at runtime precisely so it cannot appear in
    any source file - see the comment below.
    """
    import os
    import uuid

    # Generated at runtime, so this exact string exists in NO source file
    # anywhere - not the engine's, and not this test's own. A literal
    # would show up in the frame's source context (real code, not user
    # data) and fail this test for a reason unrelated to the guarantee.
    secret_text = uuid.uuid4().hex
    monkeypatch.setenv("FAKE_USER_INPUT", secret_text)

    def engine_frame():
        held_in_a_local = os.environ["FAKE_USER_INPUT"]
        _derived = held_in_a_local.upper()  # a second local holding it too
        raise RuntimeError("engine blew up")

    payload = _capture_payload(monkeypatch, engine_frame)
    assert secret_text not in payload
    # ...while still being a useful report.
    assert "RuntimeError" in payload
    assert "engine blew up" in payload
    assert "job-123" in payload


def test_stack_frames_carry_no_variables_at_all(monkeypatch):
    """Stronger and more durable than checking one string's absence: no
    frame may carry a `vars` mapping, whatever happened to be in it."""
    def engine_frame():
        raise RuntimeError("boom")

    import json

    payload = json.loads(_capture_payload(monkeypatch, engine_frame))
    frames = payload[0]["exception"]["values"][0]["stacktrace"]["frames"]
    assert frames, "expected real stack frames"
    for frame in frames:
        assert "vars" not in frame, f"frame {frame.get('function')} leaked local variables"
