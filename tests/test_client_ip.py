"""Tests for server/main.py::_client_ip - which IP a request actually gets
bucketed under for quota purposes.

Why this file exists: every browser-facing request reaches server/main.py
through the Next.js proxy (web/app/api/**/route.ts), never directly. That
proxy opens its own outbound fetch, so from FastAPI's point of view the
peer address is the Next.js server for EVERY user on the site. If nothing
carries the real end user's address across that hop, quota's per-IP
buckets (server/quota.py) silently collapse into one shared bucket for
the entire site - the first few visitors of the day consume it and
everyone else is refused, which is an availability bug, not just a
metering inaccuracy.

The fix these tests cover: the proxy forwards the real client address in
X-Castia-Client-IP, honored only alongside the internal secret - the same
"anyone can set a header, only the Next.js server knows the secret"
convention _authed_user_id already uses for user identity.
"""
from __future__ import annotations

import pytest
from starlette.datastructures import Headers

from server import main


class _FakeClient:
    def __init__(self, host: str) -> None:
        self.host = host


class _FakeRequest:
    """The two attributes _client_ip actually reads. A real Starlette
    Request needs a full ASGI scope to construct, and none of the rest of
    it matters here."""

    def __init__(self, headers: dict[str, str], peer: str | None = "10.0.0.1") -> None:
        self.headers = Headers(headers)
        self.client = _FakeClient(peer) if peer else None


@pytest.fixture(autouse=True)
def _internal_secret(monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "test-secret")


# --- The bug this file was written to catch ---------------------------


def test_two_users_behind_the_proxy_do_not_share_one_bucket():
    """The regression that motivated all of this: without a forwarded
    client address, two different end users arriving through the same
    Next.js proxy both bucket under the proxy's own peer address, so one
    user's traffic exhausts the other's quota."""
    proxy_peer = "10.0.0.1"  # the Next.js server, identical for everyone

    alice = main._client_ip(
        _FakeRequest(
            {"x-castia-internal-secret": "test-secret", "x-castia-client-ip": "203.0.113.7"},
            peer=proxy_peer,
        )
    )
    bob = main._client_ip(
        _FakeRequest(
            {"x-castia-internal-secret": "test-secret", "x-castia-client-ip": "198.51.100.42"},
            peer=proxy_peer,
        )
    )

    assert alice == "203.0.113.7"
    assert bob == "198.51.100.42"
    assert alice != bob, "two different end users must not share one quota bucket"


# --- Trusting the forwarded address only when it's actually trustworthy


def test_forwarded_client_ip_is_ignored_without_the_internal_secret():
    """Anyone on the internet can set this header on a direct request to
    the engine; only the Next.js server knows the secret. Without it the
    header is not evidence of anything and must not be honored, or quota
    becomes opt-out for anyone who reads this source file."""
    ip = main._client_ip(
        _FakeRequest({"x-castia-client-ip": "203.0.113.7"}, peer="198.51.100.1")
    )
    assert ip == "198.51.100.1"


def test_forwarded_client_ip_is_ignored_with_a_wrong_internal_secret():
    ip = main._client_ip(
        _FakeRequest(
            {"x-castia-internal-secret": "not-the-secret", "x-castia-client-ip": "203.0.113.7"},
            peer="198.51.100.1",
        )
    )
    assert ip == "198.51.100.1"


def test_forwarded_client_ip_is_ignored_when_no_secret_is_configured(monkeypatch):
    """A deployment with no internal secret set has no trusted proxy, so
    there is nothing that could legitimately vouch for this header."""
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", "")
    ip = main._client_ip(
        _FakeRequest(
            {"x-castia-internal-secret": "", "x-castia-client-ip": "203.0.113.7"},
            peer="198.51.100.1",
        )
    )
    assert ip == "198.51.100.1"


def test_blank_forwarded_client_ip_falls_through_rather_than_bucketing_everyone_under_empty():
    ip = main._client_ip(
        _FakeRequest(
            {"x-castia-internal-secret": "test-secret", "x-castia-client-ip": "   "},
            peer="198.51.100.1",
        )
    )
    assert ip == "198.51.100.1"


# --- Pre-existing behavior that must keep working ---------------------


def test_still_falls_back_to_x_forwarded_for_for_direct_callers():
    """The public /v1 API is called server-to-server, not through the
    Next.js proxy, and reaches FastAPI through the platform's own edge
    proxy - which sets x-forwarded-for. That path is unchanged."""
    ip = main._client_ip(_FakeRequest({"x-forwarded-for": "203.0.113.9, 70.41.3.18"}))
    assert ip == "203.0.113.9"


def test_still_falls_back_to_the_peer_address_with_no_headers_at_all():
    assert main._client_ip(_FakeRequest({}, peer="198.51.100.1")) == "198.51.100.1"


def test_reports_unknown_rather_than_crashing_when_there_is_no_peer():
    assert main._client_ip(_FakeRequest({}, peer=None)) == "unknown"


def test_authenticated_forwarded_ip_wins_over_x_forwarded_for():
    """Both present: the proxy's authenticated value is the real end
    user; x-forwarded-for on that same hop describes who connected to the
    engine (the proxy), which is exactly the address we're trying not to
    bucket under."""
    ip = main._client_ip(
        _FakeRequest(
            {
                "x-castia-internal-secret": "test-secret",
                "x-castia-client-ip": "203.0.113.7",
                "x-forwarded-for": "10.0.0.1",
            }
        )
    )
    assert ip == "203.0.113.7"
