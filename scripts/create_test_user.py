#!/usr/bin/env python3
"""Standalone helper for creating a dedicated ManageLeads dashboard test
user directly in the production Postgres database.

Usage:

    DATABASE_URL=postgresql://... python scripts/create_test_user.py

Idempotent: if a user with TEST_EMAIL already exists, its identifying
fields are reported and it is left untouched - this script never
modifies an existing row. If it doesn't exist, exactly one row is
created in the `users` table (no Account/AccountUser rows - those don't
exist in this schema) with a password hashed the same way
server/password_auth.py::hash_password() hashes every other
email/password sign-up.

Prints a single JSON object to stdout on both success and failure so the
result is easy to capture from a shell/CI step.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as `python scripts/create_test_user.py` from the repo
# root without needing the package installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TEST_EMAIL = "test.preview@manageleads.co"
TEST_PASSWORD = "OmH$0Bn6DDvEGHJOKWno"


def main() -> int:
    try:
        from server import db
        from server.db_models import User
        from server.password_auth import hash_password
    except Exception as exc:  # pragma: no cover - import/setup failure
        print(json.dumps({
            "success": False,
            "action": None,
            "message": f"Failed to import server modules: {exc}",
        }))
        return 1

    try:
        with db.session_scope() as session:
            existing = session.query(User).filter_by(email=TEST_EMAIL).one_or_none()

            if existing is not None:
                result = {
                    "success": True,
                    "action": "found_existing",
                    "userId": str(existing.id),
                    "email": existing.email,
                    "emailVerified": existing.email_verified,
                    "plan": existing.plan,
                    "createdAt": existing.created_at.isoformat() if existing.created_at else None,
                    "message": (
                        f"User {TEST_EMAIL} already exists - left unmodified."
                    ),
                }
                print(json.dumps(result, indent=2))
                return 0

            user = User(
                email=TEST_EMAIL,
                password_hash=hash_password(TEST_PASSWORD),
                email_verified=True,
                plan="free",
                credits=0,
            )
            # is_active / role columns don't exist on this User model
            # (server/db_models.py) - omitted per instructions.
            session.add(user)
            session.commit()

            result = {
                "success": True,
                "action": "created",
                "userId": str(user.id),
                "email": user.email,
                "password": TEST_PASSWORD,
                "emailVerified": user.email_verified,
                "plan": user.plan,
                "credits": user.credits,
                "createdAt": user.created_at.isoformat() if user.created_at else None,
                "message": (
                    f"Created test user {TEST_EMAIL} for ManageLeads dashboard testing."
                ),
            }
            print(json.dumps(result, indent=2))
            return 0
    except Exception as exc:
        print(json.dumps({
            "success": False,
            "action": None,
            "email": TEST_EMAIL,
            "message": f"Failed to create/look up test user: {exc}",
        }))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
