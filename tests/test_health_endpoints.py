"""GET /health and /health/db - both unauthenticated by design (a
hosting platform's health check has no credential to present), which is
exactly why /health/db must never hand an anonymous caller the raw
database driver exception - see that endpoint's own docstring in
server/main.py for the full reasoning. Found during a security audit:
before this, a DB outage's exact error text (host/port and possibly
other connection detail, depending on the driver's error formatting)
was returned straight to any caller on the internet."""
from __future__ import annotations

from fastapi.testclient import TestClient

import server.main as main
from server import db


def test_health_is_ok():
    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_is_ok_when_the_database_is_reachable(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/health_db_test.db")
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)

    client = TestClient(main.app)
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_reports_a_generic_message_without_leaking_the_real_exception(monkeypatch):
    """The regression test: a real driver exception (here, a fake one
    with an identifiable marker string standing in for the kind of
    host/port/connection detail a real one could contain) must never
    reach the response body - only a generic message does."""

    class _FakeEngine:
        def connect(self):
            raise RuntimeError("connection to host secret-db-host.internal:5432 refused")

    monkeypatch.setattr(db, "get_engine", lambda: _FakeEngine())

    client = TestClient(main.app)
    response = client.get("/health/db")
    assert response.status_code == 503
    body = response.json()
    assert body == {"detail": "database unreachable"}
    assert "secret-db-host" not in response.text
