from collections.abc import Iterator

import pytest
from audit_engine.types import Issue, Severity
from fastapi.testclient import TestClient
from pytest_httpserver import HTTPServer
from sqlalchemy.orm import Session

from app.db.models import (
    Audit,
    AuditEnvironment,
    AuditIssue,
    AuditStatus,
    Project,
    Role,
)
from app.workers.audit_task import _broken_links_count, _seo_score, run_audit
from tests.conftest import FakeQueue, auth_cookie

BASE_PROJECT = {
    "name": "Acme",
    "production_url": "https://acme.com",
    "staging_url": "https://staging.acme.com",
}


@pytest.fixture
def project_id(client: TestClient, make_user) -> Iterator[str]:
    _, token = make_user()
    auth_cookie(client, token)
    pid = client.post("/projects", json=BASE_PROJECT).json()["id"]
    yield pid


# ---------- POST /projects/{id}/audits ----------


def test_enqueue_explicit_production_creates_one_audit(
    client: TestClient, queue: FakeQueue, project_id: str
) -> None:
    res = client.post(f"/projects/{project_id}/audits", json={"environment": "production"})
    assert res.status_code == 201, res.text
    body = res.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["status"] == "queued"
    assert body[0]["environment"] == "production"
    assert body[0]["companion_audit_id"] is None
    assert len(queue.jobs) == 1
    func, args, _ = queue.jobs[0]
    assert func.__name__ == "run_audit"
    assert args == (body[0]["id"],)


def test_enqueue_default_creates_pair_when_project_has_both_urls(
    client: TestClient, queue: FakeQueue, project_id: str
) -> None:
    res = client.post(f"/projects/{project_id}/audits", json={})
    assert res.status_code == 201
    body = res.json()
    assert len(body) == 2

    by_env = {a["environment"]: a for a in body}
    assert "production" in by_env and "staging" in by_env
    # Each side points at the other.
    assert by_env["production"]["companion_audit_id"] == by_env["staging"]["id"]
    assert by_env["staging"]["companion_audit_id"] == by_env["production"]["id"]
    assert len(queue.jobs) == 2


def test_enqueue_default_single_audit_when_no_staging_url(
    client: TestClient, queue: FakeQueue, make_user
) -> None:
    _, token = make_user()
    auth_cookie(client, token)
    pid = client.post("/projects", json={"name": "X", "production_url": "https://x.com"}).json()[
        "id"
    ]

    res = client.post(f"/projects/{pid}/audits", json={})
    assert res.status_code == 201
    body = res.json()
    assert len(body) == 1
    assert body[0]["environment"] == "production"
    assert len(queue.jobs) == 1


def test_enqueue_audit_rejects_staging_when_no_staging_url(client: TestClient, make_user) -> None:
    _, token = make_user()
    auth_cookie(client, token)
    pid = client.post("/projects", json={"name": "X", "production_url": "https://x.com"}).json()[
        "id"
    ]

    res = client.post(f"/projects/{pid}/audits", json={"environment": "staging"})
    assert res.status_code == 400
    assert "staging_url" in res.json()["detail"]


def test_enqueue_audit_unauthenticated_returns_401(client: TestClient, project_id: str) -> None:
    client.cookies.clear()
    res = client.post(f"/projects/{project_id}/audits", json={})
    assert res.status_code == 401


def test_enqueue_audit_for_other_users_project_returns_404(
    client: TestClient, make_user, project_id: str
) -> None:
    _, intruder_token = make_user(email="intruder@example.com")
    auth_cookie(client, intruder_token)
    res = client.post(f"/projects/{project_id}/audits", json={})
    assert res.status_code == 404


# ---------- GET /audits/{id} ----------


def test_get_audit_returns_status_and_empty_issues(client: TestClient, project_id: str) -> None:
    audit_id = client.post(
        f"/projects/{project_id}/audits", json={"environment": "production"}
    ).json()[0]["id"]
    res = client.get(f"/audits/{audit_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == audit_id
    assert body["status"] == "queued"
    assert body["issues"] == []


def test_get_audit_404_for_unknown_id(client: TestClient, project_id: str) -> None:
    # need to authenticate first via project_id fixture
    res = client.get("/audits/does-not-exist")
    assert res.status_code == 404


def test_get_audit_404_for_other_users_audit(
    client: TestClient, make_user, project_id: str
) -> None:
    audit_id = client.post(
        f"/projects/{project_id}/audits", json={"environment": "production"}
    ).json()[0]["id"]

    _, intruder_token = make_user(email="intruder@example.com")
    auth_cookie(client, intruder_token)
    res = client.get(f"/audits/{audit_id}")
    assert res.status_code == 404


def test_admin_can_see_other_users_audit(client: TestClient, make_user, project_id: str) -> None:
    audit_id = client.post(
        f"/projects/{project_id}/audits", json={"environment": "production"}
    ).json()[0]["id"]

    _, admin_token = make_user(email="admin@example.com", role=Role.admin)
    auth_cookie(client, admin_token)
    res = client.get(f"/audits/{audit_id}")
    assert res.status_code == 200


def test_list_audits_for_project(client: TestClient, project_id: str) -> None:
    client.post(f"/projects/{project_id}/audits", json={"environment": "production"})
    client.post(f"/projects/{project_id}/audits", json={"environment": "production"})

    res = client.get(f"/projects/{project_id}/audits")
    assert res.status_code == 200
    assert len(res.json()) == 2


# ---------- worker task: pure-unit ----------


def test_run_audit_marks_failed_when_no_target_url(db: Session, db_factory, make_user) -> None:
    user, _ = make_user()
    project = Project(name="No Staging", production_url="https://x.com", owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)

    audit = Audit(project_id=project.id, environment=AuditEnvironment.staging)
    db.add(audit)
    db.commit()
    db.refresh(audit)
    audit_id = audit.id

    run_audit(audit_id, session_factory=db_factory)

    db.expire_all()
    refreshed = db.get(Audit, audit_id)
    assert refreshed.status == AuditStatus.failed
    assert refreshed.error_message and "staging_url" in refreshed.error_message


# ---------- worker task: end-to-end via httpserver ----------


def test_run_audit_full_pipeline(
    db: Session, db_factory, make_user, httpserver: HTTPServer
) -> None:
    """Spin up a real HTTP target. Run the actual crawler+checks. Verify DB state."""
    httpserver.expect_request("/").respond_with_data(
        '<html><head><title>tiny</title></head><body><a href="/missing">x</a></body></html>',
        content_type="text/html",
    )
    httpserver.expect_request("/missing").respond_with_data("nope", status=404)

    user, _ = make_user()
    project = Project(
        name="HTTPServer Site",
        production_url=httpserver.url_for("/"),
        owner_id=user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    audit = Audit(project_id=project.id, environment=AuditEnvironment.production)
    db.add(audit)
    db.commit()
    db.refresh(audit)
    audit_id = audit.id

    run_audit(audit_id, session_factory=db_factory)

    db.expire_all()
    refreshed = db.get(Audit, audit_id)
    assert refreshed.status == AuditStatus.completed
    assert refreshed.pages_crawled >= 1
    assert refreshed.broken_links_count >= 1  # /missing returned 404
    assert refreshed.seo_score is not None and 0 <= refreshed.seo_score <= 100
    assert refreshed.started_at is not None
    assert refreshed.finished_at is not None

    issues = db.query(AuditIssue).filter_by(audit_id=audit_id).all()
    assert any(i.type == "client_error" for i in issues)
    # Title is "tiny" (4 chars) — too short
    assert any(i.type == "title_too_short" for i in issues)


# ---------- score helpers ----------


def test_seo_score_clamps_and_weights() -> None:
    issues = [
        Issue(page_url="x", type="t", severity=Severity.critical, message=""),
        Issue(page_url="x", type="t", severity=Severity.warning, message=""),
        Issue(page_url="x", type="t", severity=Severity.info, message=""),
    ]
    # 100 - 10 - 3 - 1 = 86
    assert _seo_score(issues) == 86


def test_seo_score_floors_at_zero() -> None:
    issues = [Issue(page_url="x", type="t", severity=Severity.critical, message="")] * 50
    assert _seo_score(issues) == 0


def test_broken_links_count_counts_only_failure_types() -> None:
    issues = [
        Issue(page_url="x", type="client_error", severity=Severity.critical, message=""),
        Issue(page_url="x", type="server_error", severity=Severity.critical, message=""),
        Issue(page_url="x", type="broken_link", severity=Severity.critical, message=""),
        Issue(page_url="x", type="permanent_redirect", severity=Severity.info, message=""),
    ]
    assert _broken_links_count(issues) == 3


# ---------- diff: paired audits + verdict via real worker ----------


def test_diff_endpoint_pending_until_both_audits_complete(
    client: TestClient, project_id: str
) -> None:
    res = client.post(f"/projects/{project_id}/audits", json={})
    audits = res.json()
    production_id = next(a["id"] for a in audits if a["environment"] == "production")

    diff = client.get(f"/audits/{production_id}/diff").json()
    assert diff["pair_complete"] is False
    assert diff["verdict"] is None
    assert diff["diffs"] == []


def test_diff_endpoint_404_for_other_user(client: TestClient, make_user, project_id: str) -> None:
    pid = client.post(f"/projects/{project_id}/audits", json={}).json()[0]["id"]
    _, intruder_token = make_user(email="intruder@example.com")
    auth_cookie(client, intruder_token)
    res = client.get(f"/audits/{pid}/diff")
    assert res.status_code == 404


def test_diff_endpoint_400_for_unpaired_audit(client: TestClient, project_id: str) -> None:
    audit_id = client.post(
        f"/projects/{project_id}/audits", json={"environment": "production"}
    ).json()[0]["id"]
    res = client.get(f"/audits/{audit_id}/diff")
    assert res.status_code == 400


@pytest.fixture
def staging_server() -> Iterator[HTTPServer]:
    """A second HTTPServer instance so staging + production share path structure."""
    server = HTTPServer(host="127.0.0.1", port=0)
    server.start()
    yield server
    server.stop()


def test_paired_run_produces_no_go_when_production_500s_a_page(
    client: TestClient,
    queue: FakeQueue,
    db_factory,
    make_user,
    httpserver: HTTPServer,
    staging_server: HTTPServer,
) -> None:
    """End-to-end: staging serves /api with 200, production with 500. Verdict = no-go."""
    # Staging at /, /api — both healthy
    staging_server.expect_request("/").respond_with_data(
        "<html><head><title>Acme — pre-launch QA platform for serious teams</title></head>"
        '<body><a href="/api">api</a></body></html>',
        content_type="text/html",
    )
    staging_server.expect_request("/api").respond_with_data("ok", content_type="text/html")

    # Production at /, /api — /api regressed to 500
    httpserver.expect_request("/").respond_with_data(
        "<html><head><title>Acme — pre-launch QA platform for serious teams</title></head>"
        '<body><a href="/api">api</a></body></html>',
        content_type="text/html",
    )
    httpserver.expect_request("/api").respond_with_data("oops", status=500)

    _, token = make_user(email="pair@example.com")
    auth_cookie(client, token)
    pid = client.post(
        "/projects",
        json={
            "name": "Pair",
            "production_url": httpserver.url_for("/"),
            "staging_url": staging_server.url_for("/"),
        },
    ).json()["id"]

    audits = client.post(f"/projects/{pid}/audits", json={}).json()
    production_id = next(a["id"] for a in audits if a["environment"] == "production")

    # Drain the queue: runs both audits + triggers diff. We swap to db_factory so the
    # worker creates its own session that won't conflict with the test's session.
    for func, args, _ in queue.jobs:
        func(*args, session_factory=db_factory)
    queue.jobs.clear()

    diff_res = client.get(f"/audits/{production_id}/diff").json()
    assert diff_res["pair_complete"] is True, diff_res
    assert diff_res["verdict"] == "no_go", diff_res
    fields = {d["field"] for d in diff_res["diffs"]}
    assert "status_code" in fields, diff_res


# ---------- HTML export ----------


def test_export_html_returns_styled_report(client: TestClient, project_id: str) -> None:
    audit_id = client.post(
        f"/projects/{project_id}/audits", json={"environment": "production"}
    ).json()[0]["id"]

    res = client.get(f"/audits/{audit_id}/export.html")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    body = res.text
    assert "<!doctype html>" in body.lower()
    assert "Acme" in body  # project name
    assert "<style>" in body  # inline CSS, no external deps


def test_export_html_404_for_other_user(client: TestClient, make_user, project_id: str) -> None:
    audit_id = client.post(
        f"/projects/{project_id}/audits", json={"environment": "production"}
    ).json()[0]["id"]

    _, intruder_token = make_user(email="intruder@example.com")
    auth_cookie(client, intruder_token)
    res = client.get(f"/audits/{audit_id}/export.html")
    assert res.status_code == 404


# ---------- DELETE /audits/{id} ----------


def test_delete_audit_removes_row(client: TestClient, project_id: str) -> None:
    audit_id = client.post(
        f"/projects/{project_id}/audits", json={"environment": "production"}
    ).json()[0]["id"]

    res = client.delete(f"/audits/{audit_id}")
    assert res.status_code == 204
    assert client.get(f"/audits/{audit_id}").status_code == 404


def test_delete_audit_cancels_paired_run(client: TestClient, project_id: str) -> None:
    """Deleting one half of a paired audit also drops the companion."""
    body = client.post(f"/projects/{project_id}/audits", json={}).json()
    production_id = next(a["id"] for a in body if a["environment"] == "production")
    staging_id = next(a["id"] for a in body if a["environment"] == "staging")

    res = client.delete(f"/audits/{production_id}")
    assert res.status_code == 204
    assert client.get(f"/audits/{production_id}").status_code == 404
    assert client.get(f"/audits/{staging_id}").status_code == 404


def test_delete_audit_404_for_other_user(
    client: TestClient, make_user, project_id: str
) -> None:
    audit_id = client.post(
        f"/projects/{project_id}/audits", json={"environment": "production"}
    ).json()[0]["id"]

    _, intruder_token = make_user(email="intruder@example.com")
    auth_cookie(client, intruder_token)
    res = client.delete(f"/audits/{audit_id}")
    assert res.status_code == 404


def test_delete_audit_404_for_unknown_id(client: TestClient, project_id: str) -> None:
    res = client.delete("/audits/does-not-exist")
    assert res.status_code == 404
