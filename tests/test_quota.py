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
