from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import AuditEnvironment, AuditStatus, IssueSeverity


class AuditCreate(BaseModel):
    environment: AuditEnvironment = AuditEnvironment.production


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


class AuditDetail(AuditOut):
    issues: list[AuditIssueOut] = []
