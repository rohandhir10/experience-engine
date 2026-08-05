"""Tests for server/quota.py's in-memory backend (no DATABASE_URL set in
the test environment) - the DB-backed atomic-UPSERT path needs a real
Postgres instance to exercise meaningfully and isn't covered here.
"""
from __future__ import annotations

import pytest

from server import quota


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    monkeypatch.setattr(quota, "_memory_counts", {})
    monkeypatch.setattr(quota, "_memory_monthly_counts", {})
    monkeypatch.delenv("DATABASE_URL", raising=False)


def test_disabled_quota_always_allows(monkeypatch):
    from collections import defaultdict

    monkeypatch.setattr(quota, "_memory_counts", defaultdict(int))
    for _ in range(100):
        assert quota.check_and_increment("1.2.3.4", daily_limit=0) is True


def test_allows_up_to_the_limit_then_blocks(monkeypatch):
    from collections import defaultdict

    monkeypatch.setattr(quota, "_memory_counts", defaultdict(int))
    assert quota.check_and_increment("1.2.3.4", daily_limit=2) is True
    assert quota.check_and_increment("1.2.3.4", daily_limit=2) is True
    assert quota.check_and_increment("1.2.3.4", daily_limit=2) is False


def test_different_ips_are_independent(monkeypatch):
    from collections import defaultdict

    monkeypatch.setattr(quota, "_memory_counts", defaultdict(int))
    assert quota.check_and_increment("1.2.3.4", daily_limit=1) is True
    assert quota.check_and_increment("5.6.7.8", daily_limit=1) is True
    assert quota.check_and_increment("1.2.3.4", daily_limit=1) is False


def test_monthly_disabled_quota_always_allows(monkeypatch):
    from collections import defaultdict

    monkeypatch.setattr(quota, "_memory_monthly_counts", defaultdict(int))
    for _ in range(100):
        assert quota.check_and_increment_monthly("1.2.3.4", monthly_limit=0) is True


def test_monthly_allows_up_to_the_limit_then_blocks(monkeypatch):
    from collections import defaultdict

    monkeypatch.setattr(quota, "_memory_monthly_counts", defaultdict(int))
    assert quota.check_and_increment_monthly("1.2.3.4", monthly_limit=2) is True
    assert quota.check_and_increment_monthly("1.2.3.4", monthly_limit=2) is True
    assert quota.check_and_increment_monthly("1.2.3.4", monthly_limit=2) is False


def test_monthly_and_daily_counters_are_independent_of_each_other(monkeypatch):
    """The two dimensions must not share state - hitting the daily limit
    must not itself consume or reset the monthly counter, and vice versa
    (they're deliberately separate tables/dicts, see quota.py's
    docstring: daily is anti-burst, monthly is the real ceiling)."""
    from collections import defaultdict

    monkeypatch.setattr(quota, "_memory_counts", defaultdict(int))
    monkeypatch.setattr(quota, "_memory_monthly_counts", defaultdict(int))

    assert quota.check_and_increment("1.2.3.4", daily_limit=1) is True
    assert quota.check_and_increment("1.2.3.4", daily_limit=1) is False
    # The daily block above must not have touched the monthly counter.
    assert quota.check_and_increment_monthly("1.2.3.4", monthly_limit=5) is True
