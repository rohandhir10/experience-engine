"""Create (once) the stable test account Vercel preview deployments sign
in with to exercise the ManageLeads dashboard.

Preview deployments are ephemeral, but a real dashboard test needs a
real, signed-in user - and creating/tearing down a fresh account on
every preview build would be both slower and less repeatable than one
account that just always exists. This script creates that one account
directly against the database, using the exact same User model
(server/db_models.py) and password hashing (server/password_auth.py::
hash_password) the running application itself uses, so the resulting
row is completely indistinguishable from one created through the real
sign-up flow.

Idempotent by design: it looks the account up by email first and, if
found, reports the existing id and exits without touching the row again
- safe to run on every preview deploy, forever, without ever mutating
or re-issuing credentials for an account already in use.

Usage:
    python -m scripts.create_test_user

Requires DATABASE_URL to be set in the environment, same as the main
FastAPI app (server/db.py).
"""
from __future__ import annotations

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("scripts.create_test_user")

TEST_USER_EMAIL = "test.preview@manageleads.co"
TEST_USER_PASSWORD = "OmH$0Bn6DDvEGHJOKWno"
TEST_USER_DISPLAY_NAME = "Test Preview User"


def create_test_user() -> str:
    """Returns the test user's id (as a string), creating the row first
    if it doesn't already exist. Never modifies an existing row - see
    the module docstring.
    """
    from datetime import datetime, timezone

    from server import db
    from server.db_models import User
    from server.password_auth import hash_password

    # Alembic, not bare create_all() - matches server/main.py's own
    # startup path (server/db.py::migrate_to_head's docstring), and
    # makes this script safe to run standalone against a brand-new
    # database that has never seen the FastAPI app boot at all.
    db.migrate_to_head()

    with db.session_scope() as session:
        existing = session.query(User).filter_by(email=TEST_USER_EMAIL).one_or_none()
        if existing is not None:
            logger.info(
                "Test user already exists - leaving it untouched (id=%s, email=%s)",
                existing.id,
                existing.email,
            )
            return str(existing.id)

        user = User(
            email=TEST_USER_EMAIL,
            password_hash=hash_password(TEST_USER_PASSWORD),
            email_verified=True,  # must be True to allow signin (server/password_auth.py::authenticate)
            display_name=TEST_USER_DISPLAY_NAME,
            plan="free",
            credits=0,
            google_sub=None,
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.commit()
        logger.info("Created test user (id=%s, email=%s)", user.id, user.email)
        return str(user.id)


def main() -> int:
    try:
        user_id = create_test_user()
    except RuntimeError as exc:
        # Raised by server/db.py::_database_url when DATABASE_URL is unset.
        logger.error("Could not create test user: %s", exc)
        return 1
    except Exception:
        logger.exception("Unexpected error while creating test user")
        return 1

    print("")
    print("=" * 60)
    print("ManageLeads dashboard test user")
    print("=" * 60)
    print(f"User ID:  {user_id}")
    print(f"Email:    {TEST_USER_EMAIL}")
    print(f"Password: {TEST_USER_PASSWORD}")
    print("Plan:     free")
    print("Status:   ready (existing account reused if one already existed)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
