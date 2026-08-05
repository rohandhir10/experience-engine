"""server/password_auth.py against a real (sqlite file) database - same
fixture convention as tests/test_credits.py."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import server.db as db
from server import password_auth


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/password_auth_test.db"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)
    db.create_all()
    yield url
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)


@pytest.fixture()
def sent_emails(monkeypatch):
    """Captures every (to_email, token) send_verification_email is asked
    to send, instead of actually logging - lets tests grab the real raw
    token a registration/resend generated."""
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        password_auth.emailing, "send_verification_email", lambda to, token: sent.append((to, token))
    )
    return sent


def _make_user(email: str, *, password_hash: str | None = None, google_sub: str | None = None, verified: bool = False):
    from server.db_models import User

    with db.session_scope() as session:
        user = User(email=email, password_hash=password_hash, google_sub=google_sub, email_verified=verified)
        session.add(user)
        session.commit()
        return str(user.id)


class TestPasswordHashing:
    def test_correct_password_verifies(self):
        encoded = password_auth.hash_password("correct horse battery staple")
        assert password_auth.verify_password("correct horse battery staple", encoded) is True

    def test_wrong_password_fails(self):
        encoded = password_auth.hash_password("correct horse battery staple")
        assert password_auth.verify_password("wrong password", encoded) is False

    def test_two_hashes_of_the_same_password_differ(self):
        # Distinct random salts - proves the salt is actually random, not
        # reused, since an identical hash would mean it wasn't.
        assert password_auth.hash_password("hunter2") != password_auth.hash_password("hunter2")

    def test_malformed_encoded_hash_fails_closed(self):
        assert password_auth.verify_password("hunter2", "not-a-real-hash") is False


class TestRegister:
    def test_new_email_creates_an_unverified_user_and_sends_a_token(self, sqlite_db, sent_emails):
        result = password_auth.register("new@example.com", "a-real-password")
        assert result == {"status": "ok"}
        assert len(sent_emails) == 1
        assert sent_emails[0][0] == "new@example.com"

        from server.db_models import User

        with db.session_scope() as session:
            user = session.query(User).filter_by(email="new@example.com").one()
            assert user.email_verified is False
            assert user.password_hash is not None

    def test_invalid_email_raises_before_touching_the_database(self, sqlite_db, sent_emails):
        with pytest.raises(ValueError):
            password_auth.register("not-an-email", "a-real-password")
        assert sent_emails == []

    def test_short_password_raises(self, sqlite_db, sent_emails):
        with pytest.raises(ValueError):
            password_auth.register("new@example.com", "short")
        assert sent_emails == []

    def test_returns_none_without_a_database(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        assert password_auth.register("new@example.com", "a-real-password") is None

    def test_already_verified_email_is_a_silent_no_op(self, sqlite_db, sent_emails):
        _make_user("taken@example.com", password_hash="x", verified=True)
        result = password_auth.register("taken@example.com", "a-real-password")
        assert result == {"status": "ok"}
        assert sent_emails == []

    def test_google_only_email_is_a_silent_no_op(self, sqlite_db, sent_emails):
        _make_user("taken@example.com", google_sub="sub-123", verified=True)
        result = password_auth.register("taken@example.com", "a-real-password")
        assert result == {"status": "ok"}
        assert sent_emails == []

    def test_retrying_an_unverified_signup_resends_a_fresh_token(self, sqlite_db, sent_emails):
        password_auth.register("retry@example.com", "first-password")
        assert len(sent_emails) == 1
        result = password_auth.register("retry@example.com", "second-password")
        assert result == {"status": "ok"}
        assert len(sent_emails) == 2
        # The new password actually took effect.
        assert password_auth.authenticate("retry@example.com", "first-password")["status"] == "invalid"


class TestVerifyEmailToken:
    def test_valid_token_verifies_the_user_and_is_single_use(self, sqlite_db, sent_emails):
        password_auth.register("verify@example.com", "a-real-password")
        _, raw_token = sent_emails[0]

        assert password_auth.verify_email_token(raw_token) is True

        from server.db_models import User

        with db.session_scope() as session:
            user = session.query(User).filter_by(email="verify@example.com").one()
            assert user.email_verified is True

        # Same token again: already used, must not succeed twice.
        assert password_auth.verify_email_token(raw_token) is False

    def test_unknown_token_fails(self, sqlite_db):
        assert password_auth.verify_email_token("not-a-real-token") is False

    def test_expired_token_fails(self, sqlite_db, sent_emails):
        password_auth.register("expired@example.com", "a-real-password")
        _, raw_token = sent_emails[0]

        from server.db_models import EmailVerificationToken

        with db.session_scope() as session:
            token = session.get(EmailVerificationToken, password_auth._hash_token(raw_token))
            token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            session.commit()

        assert password_auth.verify_email_token(raw_token) is False


class TestAuthenticate:
    def test_correct_credentials_for_a_verified_user_succeed(self, sqlite_db, sent_emails):
        password_auth.register("login@example.com", "a-real-password")
        _, raw_token = sent_emails[0]
        password_auth.verify_email_token(raw_token)

        result = password_auth.authenticate("login@example.com", "a-real-password")
        assert result["status"] == "ok"
        assert result["email"] == "login@example.com"
        assert "id" in result

    def test_correct_credentials_for_an_unverified_user_are_distinct_from_invalid(self, sqlite_db, sent_emails):
        password_auth.register("unverified@example.com", "a-real-password")
        result = password_auth.authenticate("unverified@example.com", "a-real-password")
        assert result == {"status": "unverified"}

    def test_wrong_password_is_invalid(self, sqlite_db, sent_emails):
        password_auth.register("wrongpw@example.com", "a-real-password")
        result = password_auth.authenticate("wrongpw@example.com", "totally-wrong")
        assert result == {"status": "invalid"}

    def test_unknown_email_is_invalid(self, sqlite_db):
        assert password_auth.authenticate("nobody@example.com", "whatever123") == {"status": "invalid"}

    def test_google_only_account_cannot_log_in_with_a_password(self, sqlite_db):
        _make_user("googleuser@example.com", google_sub="sub-abc", verified=True)
        result = password_auth.authenticate("googleuser@example.com", "whatever123")
        assert result == {"status": "invalid"}


class TestResendVerification:
    def test_resends_for_a_real_unverified_account(self, sqlite_db, sent_emails):
        password_auth.register("resend@example.com", "a-real-password")
        assert len(sent_emails) == 1
        result = password_auth.resend_verification("resend@example.com")
        assert result == {"status": "ok"}
        assert len(sent_emails) == 2

    def test_is_a_silent_no_op_for_an_unknown_email(self, sqlite_db, sent_emails):
        result = password_auth.resend_verification("nobody@example.com")
        assert result == {"status": "ok"}
        assert sent_emails == []

    def test_is_a_silent_no_op_for_an_already_verified_email(self, sqlite_db, sent_emails):
        password_auth.register("done@example.com", "a-real-password")
        _, raw_token = sent_emails[0]
        password_auth.verify_email_token(raw_token)

        result = password_auth.resend_verification("done@example.com")
        assert result == {"status": "ok"}
        assert len(sent_emails) == 1  # no second send
