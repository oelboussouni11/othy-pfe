from fastapi.testclient import TestClient

from app.db.models import Role
from tests.conftest import auth_cookie

VALID = {
    "name": "Acme Site",
    "client_name": "Acme Inc",
    "production_url": "https://acme.com",
    "staging_url": "https://staging.acme.com",
}


# ---------- create ----------


def test_create_project_returns_201_and_assigns_owner(client: TestClient, make_user) -> None:
    user, token = make_user()
    auth_cookie(client, token)

    res = client.post("/projects", json=VALID)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["owner_id"] == user.id
    assert body["name"] == "Acme Site"
    assert body["status"] == "draft"


def test_create_project_requires_auth(client: TestClient) -> None:
    res = client.post("/projects", json=VALID)
    assert res.status_code == 401


def test_create_project_rejects_invalid_url(client: TestClient, make_user) -> None:
    _, token = make_user()
    auth_cookie(client, token)

    res = client.post("/projects", json={**VALID, "production_url": "not-a-url"})
    assert res.status_code == 422


def test_create_project_accepts_only_production_url(client: TestClient, make_user) -> None:
    _, token = make_user()
    auth_cookie(client, token)

    res = client.post(
        "/projects",
        json={"name": "Acme", "production_url": "https://acme.com"},
    )
    assert res.status_code == 201
    assert res.json()["staging_url"] is None


# ---------- list ----------


def test_list_returns_only_own_projects_for_developer(client: TestClient, make_user) -> None:
    alice, alice_token = make_user(email="alice@example.com")
    bob, bob_token = make_user(email="bob@example.com")

    auth_cookie(client, alice_token)
    client.post("/projects", json={**VALID, "name": "Alice's"})

    auth_cookie(client, bob_token)
    res = client.get("/projects")
    assert res.status_code == 200
    assert res.json() == []  # Bob doesn't see Alice's


def test_list_admin_sees_everything(client: TestClient, make_user) -> None:
    alice, alice_token = make_user(email="alice@example.com")
    _, admin_token = make_user(email="admin@example.com", role=Role.admin)

    auth_cookie(client, alice_token)
    client.post("/projects", json={**VALID, "name": "Alice's"})

    auth_cookie(client, admin_token)
    res = client.get("/projects")
    assert res.status_code == 200
    assert len(res.json()) == 1


# ---------- get ----------


def test_get_own_project(client: TestClient, make_user) -> None:
    _, token = make_user()
    auth_cookie(client, token)
    project_id = client.post("/projects", json=VALID).json()["id"]

    res = client.get(f"/projects/{project_id}")
    assert res.status_code == 200


def test_get_others_project_returns_404_not_403(client: TestClient, make_user) -> None:
    """Don't leak existence — a project the viewer can't access should look missing."""
    alice, alice_token = make_user(email="alice@example.com")
    _, bob_token = make_user(email="bob@example.com")

    auth_cookie(client, alice_token)
    project_id = client.post("/projects", json=VALID).json()["id"]

    auth_cookie(client, bob_token)
    res = client.get(f"/projects/{project_id}")
    assert res.status_code == 404


def test_get_admin_sees_other_users_project(client: TestClient, make_user) -> None:
    _, alice_token = make_user(email="alice@example.com")
    _, admin_token = make_user(email="admin@example.com", role=Role.admin)

    auth_cookie(client, alice_token)
    project_id = client.post("/projects", json=VALID).json()["id"]

    auth_cookie(client, admin_token)
    res = client.get(f"/projects/{project_id}")
    assert res.status_code == 200


# ---------- update ----------


def test_owner_can_update(client: TestClient, make_user) -> None:
    _, token = make_user()
    auth_cookie(client, token)
    project_id = client.post("/projects", json=VALID).json()["id"]

    res = client.patch(f"/projects/{project_id}", json={"name": "Renamed"})
    assert res.status_code == 200
    assert res.json()["name"] == "Renamed"


def test_non_owner_cannot_update(client: TestClient, make_user) -> None:
    _, alice_token = make_user(email="alice@example.com")
    _, bob_token = make_user(email="bob@example.com")

    auth_cookie(client, alice_token)
    project_id = client.post("/projects", json=VALID).json()["id"]

    auth_cookie(client, bob_token)
    res = client.patch(f"/projects/{project_id}", json={"name": "Hijacked"})
    assert res.status_code == 403


def test_admin_can_update_others_project(client: TestClient, make_user) -> None:
    _, alice_token = make_user(email="alice@example.com")
    _, admin_token = make_user(email="admin@example.com", role=Role.admin)

    auth_cookie(client, alice_token)
    project_id = client.post("/projects", json=VALID).json()["id"]

    auth_cookie(client, admin_token)
    res = client.patch(f"/projects/{project_id}", json={"name": "Admin Edit"})
    assert res.status_code == 200


def test_update_rejects_invalid_url(client: TestClient, make_user) -> None:
    _, token = make_user()
    auth_cookie(client, token)
    project_id = client.post("/projects", json=VALID).json()["id"]

    res = client.patch(f"/projects/{project_id}", json={"production_url": "ftp://oops"})
    assert res.status_code == 422


# ---------- delete ----------


def test_owner_can_delete(client: TestClient, make_user) -> None:
    _, token = make_user()
    auth_cookie(client, token)
    project_id = client.post("/projects", json=VALID).json()["id"]

    res = client.delete(f"/projects/{project_id}")
    assert res.status_code == 204
    assert client.get(f"/projects/{project_id}").status_code == 404


def test_non_owner_cannot_delete(client: TestClient, make_user) -> None:
    _, alice_token = make_user(email="alice@example.com")
    _, bob_token = make_user(email="bob@example.com")

    auth_cookie(client, alice_token)
    project_id = client.post("/projects", json=VALID).json()["id"]

    auth_cookie(client, bob_token)
    res = client.delete(f"/projects/{project_id}")
    assert res.status_code == 403
