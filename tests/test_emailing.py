"""server/emailing.py::send_verification_email - real Resend wiring,
gated behind RESEND_API_KEY the same way server/paddle.py gates on
PADDLE_WEBHOOK_SECRET. No real network call is ever made here; httpx
itself is monkeypatched so these tests run offline like every other
test in this suite.
"""
from __future__ import annotations

import httpx
import pytest

from server import emailing


@pytest.fixture(autouse=True)
def _no_resend_key(monkeypatch):
    """Default every test to the no-provider-configured state; tests
    that need a key set it explicitly."""
    monkeypatch.delenv("RESEND_API_KEY", raising=False)


def test_falls_back_to_logging_when_no_api_key_is_configured(monkeypatch, caplog):
    calls = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: calls.append((a, k)))

    with caplog.at_level("INFO", logger="castia.emailing"):
        emailing.send_verification_email("user@example.com", "raw-token-123")

    assert calls == []  # never attempts a real HTTP call without a key
    assert any(
        "not actually sent" in r.message and "raw-token-123" in r.message
        for r in caplog.records
    )


def test_sends_via_resend_when_api_key_is_configured(monkeypatch, caplog):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    captured = {}

    class _FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)

    with caplog.at_level("INFO", logger="castia.emailing"):
        emailing.send_verification_email("user@example.com", "raw-token-123")

    assert captured["url"] == emailing.RESEND_API_URL
    assert captured["headers"] == {"Authorization": "Bearer re_test_key"}
    assert captured["json"]["to"] == ["user@example.com"]
    assert captured["json"]["from"] == emailing.EMAIL_FROM
    assert "raw-token-123" in captured["json"]["html"]
    # A real send must not leave the raw verification link sitting in
    # server logs - that's only ever correct in the no-provider fallback,
    # where logging IS the delivery mechanism.
    success_lines = [r.message for r in caplog.records if "sent via Resend" in r.message]
    assert len(success_lines) == 1
    assert "raw-token-123" not in success_lines[0]


def test_uses_a_custom_from_address_when_configured(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setattr(emailing, "EMAIL_FROM", "Castia <noreply@usecastia.com>")
    captured = {}

    class _FakeResponse:
        def raise_for_status(self):
            pass

    monkeypatch.setattr(
        httpx, "post", lambda url, headers=None, json=None, timeout=None: captured.update(json=json) or _FakeResponse()
    )

    emailing.send_verification_email("user@example.com", "tok")

    assert captured["json"]["from"] == "Castia <noreply@usecastia.com>"


def test_never_raises_when_resend_call_fails(monkeypatch, caplog):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")

    def fake_post(*a, **k):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", fake_post)

    with caplog.at_level("WARNING", logger="castia.emailing"):
        # Must not raise - a delivery failure can't take down a signup
        # request that otherwise succeeded.
        emailing.send_verification_email("user@example.com", "raw-token-456")

    warning_lines = [r.message for r in caplog.records if r.levelname == "WARNING"]
    assert len(warning_lines) == 1
    # The fallback link IS still logged on failure - a user must not be
    # stranded with genuinely no way to verify just because Resend's API
    # call failed.
    assert "raw-token-456" in warning_lines[0]


def test_never_raises_on_a_non_2xx_response(monkeypatch, caplog):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")

    class _FailingResponse:
        def raise_for_status(self):
            raise httpx.HTTPStatusError("422", request=None, response=None)

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FailingResponse())

    with caplog.at_level("WARNING", logger="castia.emailing"):
        emailing.send_verification_email("user@example.com", "raw-token-789")

    assert any(r.levelname == "WARNING" for r in caplog.records)


def test_verification_link_uses_web_app_url(monkeypatch):
    monkeypatch.setattr(emailing, "WEB_APP_URL", "https://example.test")
    assert emailing.verification_link("abc") == "https://example.test/verify-email?token=abc"
