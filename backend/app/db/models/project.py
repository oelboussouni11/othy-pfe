import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.user import User


class ProjectStatus(StrEnum):
    draft = "draft"
    in_progress = "in_progress"
    completed = "completed"
    archived = "archived"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    staging_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    production_url: Mapped[str | None] = mapped_column(String(2048), nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status", native_enum=False, length=20),
        nullable=False,
        default=ProjectStatus.draft,
    )
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    owner: Mapped[User] = relationship("User")
