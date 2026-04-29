from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer

from app.db.models import ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    client_name: str | None = Field(default=None, max_length=120)
    production_url: HttpUrl
    staging_url: HttpUrl | None = None
    status: ProjectStatus = ProjectStatus.draft

    @field_serializer("production_url", "staging_url")
    def _url_str(self, v: HttpUrl | None) -> str | None:
        return str(v) if v else None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    client_name: str | None = Field(default=None, max_length=120)
    production_url: HttpUrl | None = None
    staging_url: HttpUrl | None = None
    status: ProjectStatus | None = None

    @field_serializer("production_url", "staging_url")
    def _url_str(self, v: HttpUrl | None) -> str | None:
        return str(v) if v else None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    client_name: str | None
    production_url: str
    staging_url: str | None
    status: ProjectStatus
    owner_id: str
    created_at: datetime
