"""server/credits.py against a real (sqlite file) database, same fixture
convention as tests/test_accounts.py - these exercise the actual atomic
UPDATE ... WHERE ... RETURNING statements, not mocks.
"""
from __future__ import annotations

import threading

import pytest

import server.db as db
from server import credits


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/credits_test.db"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)
    db.create_all()
    yield url
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)


def _make_user(credits_balance: int = 0) -> str:
    from server.db_models import User

    with db.session_scope() as session:
        user = User(credits=credits_balance)
        session.add(user)
        session.commit()
        return str(user.id)


def test_get_balance_returns_none_without_a_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert credits.get_balance("00000000-0000-0000-0000-000000000000") is None


def test_get_balance_returns_none_for_an_unknown_user(sqlite_db):
    assert credits.get_balance("00000000-0000-0000-0000-000000000000") is None


def test_deduct_succeeds_and_writes_a_ledger_row(sqlite_db):
    user_id = _make_user(credits_balance=10)

    assert credits.deduct(user_id, 3, reason="adaptation", reference="result-1") is True
    assert credits.get_balance(user_id) == 7

    [row] = credits.list_transactions(user_id)
    assert row["amount"] == -3
    assert row["reason"] == "adaptation"
    assert row["reference"] == "result-1"
    assert row["balanceAfter"] == 7


def test_deduct_fails_without_touching_the_balance_when_insufficient(sqlite_db):
    user_id = _make_user(credits_balance=5)

    assert credits.deduct(user_id, 10, reason="adaptation") is False
    assert credits.get_balance(user_id) == 5
    assert credits.list_transactions(user_id) == []


def test_deduct_fails_for_an_unknown_user(sqlite_db):
    assert credits.deduct("00000000-0000-0000-0000-000000000000", 1, reason="adaptation") is False


def test_grant_succeeds_and_writes_a_ledger_row(sqlite_db):
    user_id = _make_user(credits_balance=0)

    new_balance = credits.grant(user_id, 144, reason="purchase", reference="txn_abc")
    assert new_balance == 144
    assert credits.get_balance(user_id) == 144

    [row] = credits.list_transactions(user_id)
    assert row["amount"] == 144
    assert row["reason"] == "purchase"
    assert row["reference"] == "txn_abc"


def test_refund_grants_with_a_distinct_reason(sqlite_db):
    user_id = _make_user(credits_balance=0)

    assert credits.refund(user_id, 10, reference="result-1") == 10
    [row] = credits.list_transactions(user_id)
    assert row["reason"] == "refund"
    assert row["amount"] == 10


def test_deduct_rejects_a_non_positive_amount(sqlite_db):
    user_id = _make_user(credits_balance=10)
    with pytest.raises(ValueError):
        credits.deduct(user_id, 0, reason="adaptation")
    with pytest.raises(ValueError):
        credits.deduct(user_id, -5, reason="adaptation")


def test_grant_rejects_a_non_positive_amount(sqlite_db):
    user_id = _make_user(credits_balance=10)
    with pytest.raises(ValueError):
        credits.grant(user_id, 0, reason="purchase")


def test_transactions_are_most_recent_first(sqlite_db):
    user_id = _make_user(credits_balance=100)
    credits.deduct(user_id, 1, reason="adaptation", reference="first")
    credits.deduct(user_id, 1, reason="adaptation", reference="second")

    rows = credits.list_transactions(user_id)
    assert [r["reference"] for r in rows] == ["second", "first"]


def test_the_double_spend_race_cannot_overdraw_the_balance(sqlite_db):
    """The actual scenario this module exists for: 10 credits, 5
    concurrent requests each costing 10. A read-then-write implementation
    could let all 5 through (each reads "10" before any of them writes
    back); the atomic UPDATE ... WHERE credits >= amount must let exactly
    one through and reject the other four, never going negative.
    """
    user_id = _make_user(credits_balance=10)
    results: list[bool] = []
    results_lock = threading.Lock()

    def attempt():
        ok = credits.deduct(user_id, 10, reason="adaptation")
        with results_lock:
            results.append(ok)

    threads = [threading.Thread(target=attempt) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count(True) == 1
    assert results.count(False) == 4
    assert credits.get_balance(user_id) == 0
