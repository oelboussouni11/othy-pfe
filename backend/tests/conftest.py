from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_token, hash_password
from app.db.base import Base
from app.db.models import Audit, AuditIssue, Project, Role, User  # noqa: F401  register
from app.db.session import get_db
from app.main import app
from app.workers.queue import get_queue


class FakeQueue:
    """In-memory stand-in for rq.Queue. Captures enqueued jobs without running them."""

    def __init__(self) -> None:
        self.jobs: list[tuple[Any, tuple, dict]] = []

    def enqueue(self, func, *args, **kwargs):
        self.jobs.append((func, args, kwargs))

        class _Job:
            id = f"job-{len(self.jobs)}"

        return _Job()

    def run_pending(self) -> None:
        """Drain the queue by calling each job synchronously. Useful in integration tests."""
        for func, args, kwargs in self.jobs:
            func(*args, **kwargs)
        self.jobs.clear()


@pytest.fixture
def db_factory() -> Iterator[sessionmaker]:
    """A sessionmaker bound to an in-memory SQLite. Use it to spin up sessions
    in tests that exercise the worker (which manages its own session lifecycle)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield SessionLocal
    finally:
        Base.metadata.drop_all(engine)


@pytest.fixture
def db(db_factory: sessionmaker) -> Iterator[Session]:
    session = db_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def queue() -> FakeQueue:
    return FakeQueue()


@pytest.fixture
def client(db: Session, queue: FakeQueue) -> Iterator[TestClient]:
    def _override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_queue] = lambda: queue
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db: Session):
    """Factory for users — give it an email/role, get back a (User, access_token) pair."""

    def _make(
        email: str = "user@example.com",
        name: str = "Test User",
        password: str = "correcthorse",
        role: Role = Role.developer,
    ) -> tuple[User, str]:
        user = User(
            name=name,
            email=email.lower(),
            password_hash=hash_password(password),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_token(user.id, "access")
        return user, token

    return _make


def auth_cookie(client: TestClient, token: str) -> None:
    """Set the access_token cookie on the test client. Replaces any prior cookie."""
    client.cookies.clear()
    client.cookies.set("access_token", token)
