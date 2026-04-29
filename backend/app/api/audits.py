from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Audit, AuditEnvironment, AuditStatus, Role, User
from app.db.session import get_db
from app.schemas.audit import AuditCreate, AuditDetail, AuditOut
from app.services.projects import NotFound, get_project
from app.workers.audit_task import run_audit
from app.workers.queue import get_queue

router = APIRouter(tags=["audits"])


@router.post(
    "/projects/{project_id}/audits",
    response_model=AuditOut,
    status_code=status.HTTP_201_CREATED,
)
def enqueue_audit(
    project_id: str,
    payload: AuditCreate,
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
    queue=Depends(get_queue),
):
    try:
        project = get_project(db, viewer, project_id)
    except NotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    if payload.environment == AuditEnvironment.staging and not project.staging_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project has no staging_url configured",
        )

    audit = Audit(
        project_id=project.id,
        environment=payload.environment,
        status=AuditStatus.queued,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    queue.enqueue(run_audit, audit.id)
    return audit


@router.get("/audits/{audit_id}", response_model=AuditDetail)
def get_audit(
    audit_id: str,
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    audit = db.get(Audit, audit_id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="audit not found")

    project = audit.project
    if viewer.role != Role.admin and project.owner_id != viewer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="audit not found")

    return audit


@router.get("/projects/{project_id}/audits", response_model=list[AuditOut])
def list_audits(
    project_id: str,
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    """List a project's audits, newest first. Same access rules as get_project."""
    try:
        project = get_project(db, viewer, project_id)
    except NotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return db.scalars(
        select(Audit).where(Audit.project_id == project.id).order_by(Audit.created_at.desc())
    ).all()
