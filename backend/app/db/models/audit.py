import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.project import Project


class AuditStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class AuditEnvironment(StrEnum):
    production = "production"
    staging = "staging"


class IssueSeverity(StrEnum):
    """Mirrors audit_engine.types.Severity but at the DB-storage layer."""

    critical = "critical"
    warning = "warning"
    info = "info"
    ok = "ok"


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    environment: Mapped[AuditEnvironment] = mapped_column(
        Enum(AuditEnvironment, name="audit_environment", native_enum=False, length=20),
        nullable=False,
    )
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus, name="audit_status", native_enum=False, length=20),
        nullable=False,
        default=AuditStatus.queued,
    )
    pages_crawled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    broken_links_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    seo_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    project: Mapped[Project] = relationship("Project")
    issues: Mapped[list["AuditIssue"]] = relationship(
        "AuditIssue", back_populates="audit", cascade="all, delete-orphan"
    )


class AuditIssue(Base):
    __tablename__ = "audit_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_id: Mapped[str] = mapped_column(
        ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[IssueSeverity] = mapped_column(
        Enum(IssueSeverity, name="issue_severity", native_enum=False, length=20),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    audit: Mapped[Audit] = relationship("Audit", back_populates="issues")
