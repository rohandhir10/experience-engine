"""Schema smoke test against sqlite in-memory — no real Postgres needed.
Confirms the models' columns, defaults, and relationships behave as
declared; server/db.py's DATABASE_URL parsing (Postgres-specific) is
exercised separately, not here.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.db import Base
from server.db_models import Adaptation, Collection, User


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


def test_adaptation_links_to_its_owning_user():
    session = _sqlite_session()
    user = User(email="rohan@example.com")
    session.add(user)
    session.commit()

    adaptation = Adaptation(
        user_id=user.id,
        result_id="abc123",
        song_key="abc123",
    )
    session.add(adaptation)
    session.commit()

    fetched = session.query(Adaptation).one()
    assert fetched.version == 1
    assert fetched.is_favorite is False
    assert fetched.verified is None
    assert fetched.user.email == "rohan@example.com"


def test_reruns_share_a_song_key_across_versions():
    session = _sqlite_session()
    user = User(email="rohan@example.com")
    session.add(user)
    session.commit()

    v1 = Adaptation(user_id=user.id, result_id="abc123", song_key="sadda-haq", version=1)
    v2 = Adaptation(user_id=user.id, result_id="def456", song_key="sadda-haq", version=2)
    session.add_all([v1, v2])
    session.commit()

    versions = (
        session.query(Adaptation)
        .filter_by(song_key="sadda-haq")
        .order_by(Adaptation.version)
        .all()
    )
    assert [v.version for v in versions] == [1, 2]
    assert [v.result_id for v in versions] == ["abc123", "def456"]


def test_collection_groups_adaptations_many_to_many():
    session = _sqlite_session()
    user = User(email="rohan@example.com")
    session.add(user)
    session.commit()

    a1 = Adaptation(user_id=user.id, result_id="abc123", song_key="abc123")
    a2 = Adaptation(user_id=user.id, result_id="def456", song_key="def456")
    session.add_all([a1, a2])
    session.commit()

    collection = Collection(user_id=user.id, name="Hindi Rock")
    collection.adaptations.append(a1)
    collection.adaptations.append(a2)
    session.add(collection)
    session.commit()

    fetched = session.query(Collection).filter_by(name="Hindi Rock").one()
    assert {a.result_id for a in fetched.adaptations} == {"abc123", "def456"}
    assert collection in a1.collections
