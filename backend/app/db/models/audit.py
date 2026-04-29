import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional

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


class DiffChangeType(StrEnum):
    added_in_production = "added_in_production"
    removed_in_production = "removed_in_production"
    modified = "modified"


class Verdict(StrEnum):
    go = "go"
    no_go = "no_go"


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

    # Pairs the staging and production audits of the same run.
    companion_audit_id: Mapped[str | None] = mapped_column(
        ForeignKey("audits.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Set on the production audit once the diff has run; null until then.
    verdict: Mapped[Verdict | None] = mapped_column(
        Enum(Verdict, name="audit_verdict", native_enum=False, length=10), nullable=True
    )

    project: Mapped[Project] = relationship("Project")
    issues: Mapped[list["AuditIssue"]] = relationship(
        "AuditIssue", back_populates="audit", cascade="all, delete-orphan"
    )
    diffs: Mapped[list["AuditDiff"]] = relationship(
        "AuditDiff", back_populates="audit", cascade="all, delete-orphan"
    )
    companion: Mapped[Optional["Audit"]] = relationship(
        "Audit", remote_side="Audit.id", uselist=False, post_update=True
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


class AuditDiff(Base):
    __tablename__ = "audit_diffs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # The "primary" (production) audit holds the diff rows.
    audit_id: Mapped[str] = mapped_column(
        ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    field: Mapped[str] = mapped_column(String(80), nullable=False)
    staging_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    production_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_type: Mapped[DiffChangeType] = mapped_column(
        Enum(DiffChangeType, name="diff_change_type", native_enum=False, length=30),
        nullable=False,
    )
    severity: Mapped[IssueSeverity] = mapped_column(
        Enum(IssueSeverity, name="issue_severity", native_enum=False, length=20),
        nullable=False,
    )

    audit: Mapped[Audit] = relationship("Audit", back_populates="diffs")
