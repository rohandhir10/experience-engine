"""Email/password sign-up, as a second way onto the same `users` table
Google sign-in already uses (server/accounts.py::sync_user) - one account
model, two ways to prove you own it. This module owns everything specific
to the password path: hashing, verification tokens, and login.

Trust model matches server/accounts.py's: every function here is called
from endpoints gated by `_require_internal_secret` (server/main.py), the
same shared secret that lets the Next.js server (which runs
next-auth/providers/credentials's authorize() server-side, never in the
browser) prove a request is really coming from itself.

No account-enumeration leaks: register() and resend_verification() both
always report success to the caller regardless of whether the email was
new, already verified, or Google-owned - the only thing that differs is
what happens (or doesn't) behind that response. Whether an email exists
is never observable from either endpoint's response shape or status
code.

Everything degrades to None/a stable "not configured" outcome when
DATABASE_URL is unset, same convention as accounts.py/credits.py - no
in-memory pretend-mode for something that genuinely needs durable
storage.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from . import emailing

logger = logging.getLogger("castia.password_auth")

# OWASP's current PBKDF2-HMAC-SHA256 recommendation is >=600,000
# iterations; 260,000 is the longstanding Django default and a
# deliberately conservative middle ground for a service this size - high
# enough to make offline brute-forcing a stolen hash expensive, low
# enough not to make login noticeably slow. Stored inside the hash
# string itself (see hash_password), so raising this later never
# invalidates existing hashes - verify_password reads whatever
# iteration count a given hash was created with.
_PBKDF2_ITERATIONS = 260_000
_MIN_PASSWORD_LENGTH = 8
_TOKEN_TTL = timedelta(hours=24)
# Shorter than email verification's 24h - a reset link is a live
# credential to an existing account (not just an activation step), so it
# sits in an inbox for less time before it stops working.
_RESET_TOKEN_TTL = timedelta(hours=1)


def _use_db() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(derived).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time comparison of the derived hash, not the password
    itself - hmac.compare_digest is what actually defends against a
    timing attack; the surrounding parse can branch on encoding freely
    since none of that depends on the password's content."""
    try:
        algo, iterations_str, salt_b64, hash_b64 = encoded.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(hash_b64)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations_str))
    return hmac.compare_digest(derived, expected)


# A fixed, precomputed hash checked (and always failed) against whenever
# no real user/password_hash exists to compare against - so a login
# attempt against an unregistered email takes roughly the same time as
# one against a real email with a wrong password, instead of returning
# early and leaking existence through response timing.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def _as_aware_utc(value: datetime) -> datetime:
    """SQLite (unlike Postgres) drops tzinfo on a DateTime(timezone=True)
    column when reading it back, even though every value written here
    (db_models._now, this module) was UTC to begin with - so a naive
    value read back is assumed to already be UTC, never re-interpreted
    in local time."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _issue_and_send_token(session, user) -> None:
    from .db_models import EmailVerificationToken

    raw_token = secrets.token_urlsafe(32)
    session.add(
        EmailVerificationToken(
            token_hash=_hash_token(raw_token),
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + _TOKEN_TTL,
        )
    )
    emailing.send_verification_email(user.email, raw_token)


def _issue_and_send_reset_token(session, user) -> None:
    from .db_models import PasswordResetToken

    raw_token = secrets.token_urlsafe(32)
    session.add(
        PasswordResetToken(
            token_hash=_hash_token(raw_token),
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + _RESET_TOKEN_TTL,
        )
    )
    emailing.send_password_reset_email(user.email, raw_token)


def register(email: str, password: str) -> dict | None:
    """Validates first (no DB needed for that), so a malformed request
    gets a real 400 even on a deployment with no database configured.
    Raises ValueError on invalid input - server/main.py translates that
    into a 400. Returns None only when DATABASE_URL is unset (accounts
    genuinely unavailable, same as accounts.sync_user); otherwise always
    returns {"status": "ok"} regardless of which branch below actually
    ran, per the module's no-enumeration rule."""
    email = email.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise ValueError("Enter a valid email address.")
    if len(password) < _MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters.")
    if not _use_db():
        return None

    from . import db
    from .db_models import User

    with db.session_scope() as session:
        existing = session.query(User).filter_by(email=email).one_or_none()
        if existing is not None:
            if existing.email_verified:
                logger.info("register: %s already has a verified account, no-op", email)
                return {"status": "ok"}
            if existing.password_hash is None:
                logger.info("register: %s belongs to a google-only account, no-op", email)
                return {"status": "ok"}
            # An unverified password account retrying sign-up - refresh
            # the password (they may have mistyped it the first time)
            # and send a fresh link rather than reusing the old one.
            existing.password_hash = hash_password(password)
            user = existing
        else:
            user = User(email=email, password_hash=hash_password(password), email_verified=False)
            session.add(user)
        session.flush()
        _issue_and_send_token(session, user)
        session.commit()
        return {"status": "ok"}


def verify_email_token(raw_token: str) -> bool:
    """True iff a real, unexpired, unused token was consumed. Expired and
    already-used tokens are rejected identically - the caller only needs
    to know the link no longer works, not why."""
    if not _use_db():
        return False

    from . import db
    from .db_models import EmailVerificationToken, User

    with db.session_scope() as session:
        token = session.get(EmailVerificationToken, _hash_token(raw_token))
        if token is None or token.used_at is not None:
            return False
        if _as_aware_utc(token.expires_at) < datetime.now(timezone.utc):
            return False
        user = session.get(User, token.user_id)
        if user is None:
            return False
        user.email_verified = True
        token.used_at = datetime.now(timezone.utc)
        session.commit()
        return True


def authenticate(email: str, password: str) -> dict:
    """{"status": "ok", "id", "email", "plan"} on success; {"status":
    "unverified"} for a real account with the right password that hasn't
    clicked its verification link yet (a deliberately distinct outcome
    the credentials provider surfaces to the user - see web/auth.ts);
    {"status": "invalid"} for anything else (wrong password, no such
    email, a Google-only account with no password to check)."""
    if not _use_db():
        return {"status": "invalid"}

    from . import db
    from .db_models import User

    email = email.strip().lower()
    with db.session_scope() as session:
        user = session.query(User).filter_by(email=email).one_or_none()
        if user is None or user.password_hash is None:
            verify_password(password, _DUMMY_HASH)
            return {"status": "invalid"}
        if not verify_password(password, user.password_hash):
            return {"status": "invalid"}
        if not user.email_verified:
            return {"status": "unverified"}
        return {"status": "ok", "id": str(user.id), "email": user.email, "plan": user.plan}


def resend_verification(email: str) -> dict:
    """Always {"status": "ok"} - see the module docstring on why this
    endpoint's response can never reveal whether the email exists."""
    if not _use_db():
        return {"status": "ok"}

    from . import db
    from .db_models import User

    email = email.strip().lower()
    with db.session_scope() as session:
        user = session.query(User).filter_by(email=email).one_or_none()
        if user is not None and user.password_hash is not None and not user.email_verified:
            _issue_and_send_token(session, user)
            session.commit()
    return {"status": "ok"}


def request_password_reset(email: str) -> dict:
    """Always {"status": "ok"} regardless of whether the email exists, is
    Google-only, or belongs to a password account - same no-enumeration
    rule as register()/resend_verification() above, and for the same
    reason: an attacker probing this endpoint must not be able to tell a
    real password account from a nonexistent or Google-only one just by
    watching the response. A reset link is only ever issued for an
    existing password account (google_sub-only rows have no password to
    reset)."""
    if not _use_db():
        return {"status": "ok"}

    from . import db
    from .db_models import User

    email = email.strip().lower()
    with db.session_scope() as session:
        user = session.query(User).filter_by(email=email).one_or_none()
        if user is not None and user.password_hash is not None:
            _issue_and_send_reset_token(session, user)
            session.commit()
    return {"status": "ok"}


def reset_password(raw_token: str, new_password: str) -> dict:
    """{"status": "ok"} on a real, unexpired, unused token - the password
    is updated and the token is consumed so the same link can't be
    replayed. {"status": "invalid"} for anything else (unknown, expired,
    or already-used token); the caller doesn't get to distinguish which,
    same as verify_email_token's contract. Also marks the account
    email_verified - clicking a link that only the inbox owner could have
    received is exactly as strong a proof of ownership as clicking a
    verification link is, so an unverified account that resets its
    password shouldn't stay stuck unverified. Raises ValueError on a
    too-short new password before touching the database, same as
    register()."""
    if len(new_password) < _MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters.")
    if not _use_db():
        return {"status": "invalid"}

    from . import db
    from .db_models import PasswordResetToken, User

    with db.session_scope() as session:
        token = session.get(PasswordResetToken, _hash_token(raw_token))
        if token is None or token.used_at is not None:
            return {"status": "invalid"}
        if _as_aware_utc(token.expires_at) < datetime.now(timezone.utc):
            return {"status": "invalid"}
        user = session.get(User, token.user_id)
        if user is None:
            return {"status": "invalid"}
        user.password_hash = hash_password(new_password)
        user.email_verified = True
        token.used_at = datetime.now(timezone.utc)
        session.commit()
        return {"status": "ok"}
