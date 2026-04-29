from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_token, hash_password
from app.db.base import Base
from app.db.models import Project, Role, User  # noqa: F401  register all models
from app.db.session import get_db
from app.main import app


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def _override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
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
