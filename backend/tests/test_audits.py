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


def test_enqueue_audit_creates_row_and_queues(
    client: TestClient, queue: FakeQueue, project_id: str
) -> None:
    res = client.post(f"/projects/{project_id}/audits", json={"environment": "production"})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "queued"
    assert body["environment"] == "production"
    assert body["project_id"] == project_id
    assert len(queue.jobs) == 1
    func, args, _ = queue.jobs[0]
    assert func.__name__ == "run_audit"
    assert args == (body["id"],)


def test_enqueue_audit_defaults_to_production(
    client: TestClient, queue: FakeQueue, project_id: str
) -> None:
    res = client.post(f"/projects/{project_id}/audits", json={})
    assert res.status_code == 201
    assert res.json()["environment"] == "production"


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
    audit_id = client.post(f"/projects/{project_id}/audits", json={}).json()["id"]
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
    audit_id = client.post(f"/projects/{project_id}/audits", json={}).json()["id"]

    _, intruder_token = make_user(email="intruder@example.com")
    auth_cookie(client, intruder_token)
    res = client.get(f"/audits/{audit_id}")
    assert res.status_code == 404


def test_admin_can_see_other_users_audit(client: TestClient, make_user, project_id: str) -> None:
    audit_id = client.post(f"/projects/{project_id}/audits", json={}).json()["id"]

    _, admin_token = make_user(email="admin@example.com", role=Role.admin)
    auth_cookie(client, admin_token)
    res = client.get(f"/audits/{audit_id}")
    assert res.status_code == 200


def test_list_audits_for_project(client: TestClient, project_id: str) -> None:
    client.post(f"/projects/{project_id}/audits", json={})
    client.post(f"/projects/{project_id}/audits", json={})

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
