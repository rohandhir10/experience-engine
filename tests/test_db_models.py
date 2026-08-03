"""Schema smoke test against sqlite in-memory — no real Postgres needed.
Confirms the User model's columns and constraints behave as declared;
server/db.py's DATABASE_URL parsing (Postgres-specific) is exercised
separately, not here.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.db import Base
from server.db_models import User


def _sqlite_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_user_can_be_created_with_defaults():
    session = _sqlite_session()
    user = User(email="rohan@example.com")
    session.add(user)
    session.commit()

    fetched = session.query(User).one()
    assert fetched.email == "rohan@example.com"
    assert fetched.plan == "free"
    assert fetched.google_sub is None
    assert fetched.id is not None
    assert fetched.created_at is not None


def test_user_can_exist_with_only_google_sub():
    session = _sqlite_session()
    user = User(google_sub="google-sub-123")
    session.add(user)
    session.commit()

    fetched = session.query(User).one()
    assert fetched.email is None
    assert fetched.google_sub == "google-sub-123"
