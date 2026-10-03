import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite://")

from app.db import Base, get_db
from app.main import app
from app.models import Episode, EpisodeQuality, User, UserRole
from app.security import hash_password

engine = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def add_user(db, email, password, role, name="User"):
    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name,
        role=UserRole(role),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(client, email, password):
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def add_episode(db, code="EP-00001", quality=EpisodeQuality.good, task="pick cup"):
    episode = Episode(
        episode_id=code,
        robot_id="arm-01",
        task_name=task,
        recorded_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        duration_seconds=30,
        operator_name="Diane",
        quality=quality,
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode


def future_deadline():
    return (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
