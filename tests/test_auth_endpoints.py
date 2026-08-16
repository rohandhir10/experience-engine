"""POST /api/auth/register, /login, /verify-email, /resend-verification -
the actual routes, via a real TestClient, gated by the internal secret
exactly like /api/users/sync (tests/test_password_auth.py already covers
server/password_auth.py's logic directly; this file is just the HTTP
plumbing on top of it)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import server.db as db
import server.main as main
from server import password_auth

SECRET = "test-internal-secret"


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/auth_endpoints_test.db"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)
    db.create_all()
    yield url
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)


@pytest.fixture()
def no_real_emails(monkeypatch):
    monkeypatch.setattr(password_auth.emailing, "send_verification_email", lambda to, token: None)


@pytest.fixture()
def api_client(monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_SECRET", SECRET)
    return TestClient(main.app)


def _headers():
    return {"X-Castia-Internal-Secret": SECRET}


def test_register_requires_the_internal_secret(sqlite_db, api_client, no_real_emails):
    response = api_client.post("/api/auth/register", json={"email": "a@example.com", "password": "a-real-password"})
    assert response.status_code == 401


def test_register_then_login_before_verifying_says_unverified(sqlite_db, api_client, no_real_emails):
    register_response = api_client.post(
        "/api/auth/register",
        json={"email": "roundtrip@example.com", "password": "a-real-password"},
        headers=_headers(),
    )
    assert register_response.status_code == 200
    assert register_response.json() == {"status": "ok"}

    # Not verified yet - login must say so, not "invalid".
    login_before = api_client.post(
        "/api/auth/login",
        json={"email": "roundtrip@example.com", "password": "a-real-password"},
        headers=_headers(),
    )
    assert login_before.json() == {"status": "unverified"}


def test_verify_email_with_real_token_then_login_succeeds(sqlite_db, api_client, monkeypatch):
    captured: list[str] = []
    monkeypatch.setattr(
        password_auth.emailing, "send_verification_email", lambda to, token: captured.append(token)
    )

    api_client.post(
        "/api/auth/register",
        json={"email": "verifyme@example.com", "password": "a-real-password"},
        headers=_headers(),
    )
    assert len(captured) == 1

    verify_response = api_client.post(
        "/api/auth/verify-email", json={"token": captured[0]}, headers=_headers()
    )
    assert verify_response.status_code == 200

    login_response = api_client.post(
        "/api/auth/login",
        json={"email": "verifyme@example.com", "password": "a-real-password"},
        headers=_headers(),
    )
    body = login_response.json()
    assert body["status"] == "ok"
    assert body["email"] == "verifyme@example.com"


def test_verify_email_with_bad_token_is_400(sqlite_db, api_client):
    response = api_client.post("/api/auth/verify-email", json={"token": "not-a-real-token"}, headers=_headers())
    assert response.status_code == 400


def test_register_with_a_short_password_is_400(sqlite_db, api_client, no_real_emails):
    response = api_client.post(
        "/api/auth/register", json={"email": "short@example.com", "password": "short"}, headers=_headers()
    )
    assert response.status_code == 400


def test_resend_verification_always_returns_ok_even_for_an_unknown_email(sqlite_db, api_client):
    response = api_client.post(
        "/api/auth/resend-verification", json={"email": "nobody@example.com"}, headers=_headers()
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_wrong_password_is_invalid(sqlite_db, api_client, no_real_emails):
    api_client.post(
        "/api/auth/register",
        json={"email": "wrongpw@example.com", "password": "a-real-password"},
        headers=_headers(),
    )
    response = api_client.post(
        "/api/auth/login",
        json={"email": "wrongpw@example.com", "password": "totally-wrong"},
        headers=_headers(),
    )
    assert response.json() == {"status": "invalid"}


def test_register_enforces_a_per_ip_daily_limit(sqlite_db, api_client, no_real_emails, monkeypatch):
    """Every register() call runs a real PBKDF2-260k hash - unbounded,
    this is a cheap CPU-exhaustion DoS (see AUTH_REGISTER_DAILY_LIMIT's
    comment in server/main.py). The limit must be checked BEFORE that
    hash runs, so a caller who's already over it is rejected by one
    cheap quota check, not by paying for another hash."""
    monkeypatch.setattr(main, "AUTH_REGISTER_DAILY_LIMIT", 1)

    first = api_client.post(
        "/api/auth/register",
        json={"email": "first@example.com", "password": "a-real-password"},
        headers=_headers(),
    )
    assert first.status_code == 200

    second = api_client.post(
        "/api/auth/register",
        json={"email": "second@example.com", "password": "a-real-password"},
        headers=_headers(),
    )
    assert second.status_code == 429


def test_login_enforces_a_per_ip_daily_limit(sqlite_db, api_client, no_real_emails, monkeypatch):
    """Same protection as register's, for authenticate() - which runs a
    real PBKDF2-260k comparison even for a nonexistent email
    (password_auth._DUMMY_HASH), so an attacker doesn't even need a
    valid-looking account to trigger the expensive path."""
    api_client.post(
        "/api/auth/register",
        json={"email": "loginlimit@example.com", "password": "a-real-password"},
        headers=_headers(),
    )
    monkeypatch.setattr(main, "AUTH_LOGIN_DAILY_LIMIT", 1)

    first = api_client.post(
        "/api/auth/login",
        json={"email": "loginlimit@example.com", "password": "totally-wrong"},
        headers=_headers(),
    )
    assert first.status_code == 200
    assert first.json() == {"status": "invalid"}

    # Second attempt from the same IP is refused before it even reaches
    # authenticate() - regardless of whether these credentials are real.
    second = api_client.post(
        "/api/auth/login",
        json={"email": "loginlimit@example.com", "password": "a-real-password"},
        headers=_headers(),
    )
    assert second.status_code == 429
