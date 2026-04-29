from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Project, Role, User
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectError(Exception):
    """Domain error — caller maps to HTTP."""


class NotFound(ProjectError):
    pass


class Forbidden(ProjectError):
    pass


def _can_modify(user: User, project: Project) -> bool:
    return user.role == Role.admin or project.owner_id == user.id


def list_projects(db: Session, viewer: User) -> Sequence[Project]:
    stmt = select(Project).order_by(Project.created_at.desc())
    if viewer.role != Role.admin:
        stmt = stmt.where(Project.owner_id == viewer.id)
    return db.scalars(stmt).all()


def get_project(db: Session, viewer: User, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFound("project not found")
    if viewer.role != Role.admin and project.owner_id != viewer.id:
        raise NotFound("project not found")  # don't leak existence
    return project


def create_project(db: Session, owner: User, payload: ProjectCreate) -> Project:
    data = payload.model_dump(mode="json")
    project = Project(
        name=data["name"],
        client_name=data.get("client_name"),
        production_url=data["production_url"],
        staging_url=data.get("staging_url"),
        status=payload.status,
        owner_id=owner.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, viewer: User, project_id: str, payload: ProjectUpdate) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFound("project not found")
    if not _can_modify(viewer, project):
        raise Forbidden("not allowed to modify this project")

    data = payload.model_dump(mode="json", exclude_unset=True)
    for field, value in data.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, viewer: User, project_id: str) -> None:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFound("project not found")
    if not _can_modify(viewer, project):
        raise Forbidden("not allowed to delete this project")
    db.delete(project)
    db.commit()
