from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_token

REGISTER_BODY = {"name": "Ada Lovelace", "email": "ada@example.com", "password": "correcthorse"}


def _register(client: TestClient, body: dict | None = None) -> dict:
    res = client.post("/auth/register", json=body or REGISTER_BODY)
    assert res.status_code == 201, res.text
    return res.json()


def test_register_creates_user_and_sets_cookies(client: TestClient) -> None:
    res = client.post("/auth/register", json=REGISTER_BODY)
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "ada@example.com"
    assert body["role"] == "developer"
    assert "id" in body and "password_hash" not in body
    assert "access_token" in res.cookies
    assert "refresh_token" in res.cookies


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    _register(client)
    res = client.post("/auth/register", json=REGISTER_BODY)
    assert res.status_code == 409


def test_register_email_is_lowercased(client: TestClient) -> None:
    _register(client, {**REGISTER_BODY, "email": "ADA@EXAMPLE.COM"})
    res = client.post("/auth/login", json={"email": "ada@example.com", "password": "correcthorse"})
    assert res.status_code == 200


def test_login_success_sets_cookies(client: TestClient) -> None:
    _register(client)
    client.cookies.clear()
    res = client.post("/auth/login", json={"email": "ada@example.com", "password": "correcthorse"})
    assert res.status_code == 200
    assert "access_token" in res.cookies
    assert "refresh_token" in res.cookies


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    _register(client)
    res = client.post("/auth/login", json={"email": "ada@example.com", "password": "wrong"})
    assert res.status_code == 401


def test_login_unknown_email_returns_401(client: TestClient) -> None:
    res = client.post("/auth/login", json={"email": "ghost@example.com", "password": "whatever"})
    assert res.status_code == 401


def test_me_returns_user_when_authenticated(client: TestClient) -> None:
    _register(client)
    res = client.get("/auth/me")
    assert res.status_code == 200
    assert res.json()["email"] == "ada@example.com"


def test_me_returns_401_without_cookie(client: TestClient) -> None:
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_me_with_expired_token_returns_401(client: TestClient) -> None:
    user = _register(client)

    expired = jwt.encode(
        {
            "sub": user["id"],
            "type": "access",
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    client.cookies.clear()
    client.cookies.set("access_token", expired)
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_refresh_issues_new_token_pair(client: TestClient) -> None:
    _register(client)
    refresh_value = client.cookies.get("refresh_token")
    client.cookies.clear()
    client.cookies.set("refresh_token", refresh_value)

    res = client.post("/auth/refresh")
    assert res.status_code == 200
    assert "access_token" in res.cookies
    assert "refresh_token" in res.cookies


def test_refresh_rejects_access_token(client: TestClient) -> None:
    _register(client)
    access = client.cookies.get("access_token")
    client.cookies.clear()
    client.cookies.set("refresh_token", access)  # wrong type
    res = client.post("/auth/refresh")
    assert res.status_code == 401


def test_refresh_without_cookie_returns_401(client: TestClient) -> None:
    res = client.post("/auth/refresh")
    assert res.status_code == 401


def test_logout_clears_cookies(client: TestClient) -> None:
    _register(client)
    res = client.post("/auth/logout")
    assert res.status_code == 204
    # Subsequent /me hits should fail
    client.cookies.clear()
    assert client.get("/auth/me").status_code == 401


def test_role_guard_forbids_non_admin(client: TestClient) -> None:
    """Sanity check: admin-only route blocks default-role user."""
    from fastapi import Depends

    from app.api.deps import require_roles
    from app.db.models import Role
    from app.main import app

    @app.get("/_test/admin-only", tags=["_test"])
    def admin_only(user=Depends(require_roles(Role.admin))):
        return {"ok": True}

    try:
        _register(client)
        res = client.get("/_test/admin-only")
        assert res.status_code == 403
    finally:
        app.routes[:] = [r for r in app.routes if getattr(r, "path", "") != "/_test/admin-only"]


def test_role_guard_allows_admin(client: TestClient, db) -> None:
    from fastapi import Depends

    from app.api.deps import require_roles
    from app.core.security import hash_password
    from app.db.models import Role, User
    from app.main import app

    admin = User(
        name="Admin",
        email="admin@example.com",
        password_hash=hash_password("correcthorse"),
        role=Role.admin,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    @app.get("/_test/admin-only", tags=["_test"])
    def admin_only(user=Depends(require_roles(Role.admin))):
        return {"ok": True, "id": user.id}

    try:
        client.cookies.clear()
        client.cookies.set("access_token", create_token(admin.id, "access"))
        res = client.get("/_test/admin-only")
        assert res.status_code == 200
    finally:
        app.routes[:] = [r for r in app.routes if getattr(r, "path", "") != "/_test/admin-only"]
