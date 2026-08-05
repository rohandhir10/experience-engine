"""The credit ledger: atomic balance changes plus an append-only history
row for every one, backing server/db_models.py's User.credits and
CreditTransaction.

The double-spend race this exists to close, stated plainly: if a user
has 10 credits and submits 5 requests in the same instant, reading the
balance in Python, checking it, then writing a new value back is three
separate steps with a window between them - every one of those 5
requests can read "10", decide it's enough, and all 5 succeed, leaving
the account at -40 instead of blocking the ones it can't afford. The
fix is not a lock taken in this process (server/main.py can run more
than one worker, and Railway can run more than one instance) - it's
forcing the database to do the check and the write in one atomic
statement it can't be interrupted partway through, the same reasoning
server/quota.py's atomic UPSERT already uses for the daily/monthly
submission caps.

Everything here degrades to a no-op when DATABASE_URL is unset, same
convention as server/accounts.py: credits genuinely need a durable,
shared balance, so there is no in-memory pretend-mode that would fake
consistency the feature doesn't have without a real database.
"""
from __future__ import annotations

import os
import uuid


def _use_db() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def get_balance(user_id: str) -> int | None:
    """None means "no database, or no such user" - never confuse that
    with a real, known-zero balance."""
    if not _use_db():
        return None

    from . import db
    from .db_models import User

    with db.session_scope() as session:
        user = session.get(User, uuid.UUID(user_id))
        return user.credits if user is not None else None


def deduct(user_id: str, amount: int, reason: str, reference: str | None = None) -> bool:
    """Atomically debits `amount` credits, returning False (no balance
    change, no ledger row) if the account doesn't have enough or doesn't
    exist. `amount` must be positive - this subtracts it.

    The WHERE clause is the whole mechanism: `credits >= amount` is
    evaluated by Postgres as part of the same UPDATE that writes the new
    value, so two concurrent calls that would each individually succeed
    against a stale balance can't both succeed against the real one -
    the second sees the row the first already changed, per the module
    docstring's race condition.
    """
    if amount <= 0:
        raise ValueError(f"deduct() amount must be positive, got {amount}")
    if not _use_db():
        return False

    from sqlalchemy import update

    from . import db
    from .db_models import CreditTransaction, User

    with db.session_scope() as session:
        stmt = (
            update(User)
            .where(User.id == uuid.UUID(user_id), User.credits >= amount)
            .values(credits=User.credits - amount)
            .returning(User.credits)
        )
        row = session.execute(stmt).first()
        if row is None:
            return False
        new_balance = row[0]
        session.add(
            CreditTransaction(
                user_id=uuid.UUID(user_id),
                amount=-amount,
                reason=reason,
                reference=reference,
                balance_after=new_balance,
            )
        )
        session.commit()
    return True


def grant(user_id: str, amount: int, reason: str, reference: str | None = None) -> int | None:
    """Atomically credits `amount` to the account (a Paddle purchase/
    subscription renewal, or a refund - see server/paddle.py and the
    adapt endpoints' failure handling). Returns the new balance, or None
    if the user doesn't exist or there's no database. `amount` must be
    positive; refunding and purchasing are both grants, never a negative
    deduct() in disguise, so amount<=0 is always a caller bug here.
    """
    if amount <= 0:
        raise ValueError(f"grant() amount must be positive, got {amount}")
    if not _use_db():
        return None

    from sqlalchemy import update

    from . import db
    from .db_models import CreditTransaction, User

    with db.session_scope() as session:
        stmt = (
            update(User)
            .where(User.id == uuid.UUID(user_id))
            .values(credits=User.credits + amount)
            .returning(User.credits)
        )
        row = session.execute(stmt).first()
        if row is None:
            return None
        new_balance = row[0]
        session.add(
            CreditTransaction(
                user_id=uuid.UUID(user_id),
                amount=amount,
                reason=reason,
                reference=reference,
                balance_after=new_balance,
            )
        )
        session.commit()
    return new_balance


def refund(user_id: str, amount: int, reference: str | None = None) -> int | None:
    """A deduct() that turned out to be unearned - the engine/GPU call it
    paid for failed after the debit already happened (server/main.py's
    adapt endpoints debit before calling the engine, per this module's
    docstring: never let a job start before its cost is locked in, or a
    user could delete their account mid-run and dodge the charge).
    Thin wrapper over grant() so refunds share its atomicity and get
    their own "refund" reason in the ledger rather than looking like an
    ordinary purchase.
    """
    return grant(user_id, amount, reason="refund", reference=reference)


def list_transactions(user_id: str, limit: int = 50) -> list[dict]:
    """Most-recent-first ledger history for the billing dashboard.
    Returns [] rather than None on no-database/no-user - an empty
    history is a legitimate, renderable state; a missing balance is not
    (see get_balance), so the two don't share a sentinel."""
    if not _use_db():
        return []

    from . import db
    from .db_models import CreditTransaction

    with db.session_scope() as session:
        rows = (
            session.query(CreditTransaction)
            .filter_by(user_id=uuid.UUID(user_id))
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(row.id),
                "amount": row.amount,
                "reason": row.reason,
                "reference": row.reference,
                # camelCase to match server/api_keys.py's list_keys - the
                # backend does this conversion at the source everywhere
                # else in this API, not left to each frontend caller.
                "balanceAfter": row.balance_after,
                "createdAt": row.created_at.isoformat(),
            }
            for row in rows
        ]
