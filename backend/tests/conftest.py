from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.clock import get_now
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# pool_size 25 because the concurrency test holds 20 connections at once
test_engine = create_engine(
    settings.test_database_url, pool_size=25, connect_args={"options": "-c timezone=UTC"}
)
TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)


def at(hhmm: str) -> datetime:
    hour, minute = map(int, hhmm.split(":"))
    return datetime(2030, 1, 1, hour, minute, tzinfo=UTC)


class Clock:
    def __init__(self):
        self.now = at("10:00")


@pytest.fixture(scope="session")
def tables():
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)


@pytest.fixture
def clean_db(tables):
    yield
    with test_engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE users, rfqs, auction_configs, bids, auction_events "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def db(clean_db):
    with TestSession() as session:
        yield session


@pytest.fixture
def client(clean_db, clock):

    def test_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = test_get_db
    app.dependency_overrides[get_now] = lambda: clock.now
    yield TestClient(app)
    app.dependency_overrides.clear()
