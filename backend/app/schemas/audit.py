from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import (
    AuditEnvironment,
    AuditStatus,
    DiffChangeType,
    IssueSeverity,
    Verdict,
)


class AuditCreate(BaseModel):
    # None = "auto": run both environments if the project has staging_url, else production.
    environment: AuditEnvironment | None = None


class AuditIssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    page_url: str
    type: str
    severity: IssueSeverity
    message: str
    recommendation: str
    status_code: int | None


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    environment: AuditEnvironment
    status: AuditStatus
    pages_crawled: int
    broken_links_count: int
    seo_score: int | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    companion_audit_id: str | None
    verdict: Verdict | None


class AuditDetail(AuditOut):
    issues: list[AuditIssueOut] = []


class AuditDiffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    page_url: str
    field: str
    staging_value: str | None
    production_value: str | None
    change_type: DiffChangeType
    severity: IssueSeverity


class DiffResponse(BaseModel):
    audit_id: str  # the production-side audit (the diff "owner")
    companion_audit_id: str
    pair_complete: bool
    verdict: Verdict | None
    diffs: list[AuditDiffOut]
