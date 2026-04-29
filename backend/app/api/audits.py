from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Audit, AuditEnvironment, AuditStatus, Role, User
from app.db.session import get_db
from app.schemas.audit import (
    AuditCreate,
    AuditDetail,
    AuditDiffOut,
    AuditOut,
    DiffResponse,
)
from app.services.projects import NotFound, get_project
from app.workers.audit_task import run_audit
from app.workers.queue import get_queue

router = APIRouter(tags=["audits"])


@router.post(
    "/projects/{project_id}/audits",
    response_model=list[AuditOut],
    status_code=status.HTTP_201_CREATED,
)
def enqueue_audit(
    project_id: str,
    payload: AuditCreate,
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
    queue=Depends(get_queue),
):
    """Enqueue an audit. Returns a list because a project with both URLs runs as a pair.

    - environment=None (default): runs both if staging_url exists, else just production
    - environment=production or staging: runs only that one (no diff)
    """
    try:
        project = get_project(db, viewer, project_id)
    except NotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    if payload.environment == AuditEnvironment.staging and not project.staging_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project has no staging_url configured",
        )

    if payload.environment is None and project.staging_url:
        return _enqueue_pair(db, queue, project)

    env = payload.environment or AuditEnvironment.production
    audit = Audit(project_id=project.id, environment=env, status=AuditStatus.queued)
    db.add(audit)
    db.commit()
    db.refresh(audit)
    queue.enqueue(run_audit, audit.id)
    return [audit]


def _enqueue_pair(db: Session, queue, project) -> list[Audit]:
    staging_audit = Audit(
        project_id=project.id,
        environment=AuditEnvironment.staging,
        status=AuditStatus.queued,
    )
    production_audit = Audit(
        project_id=project.id,
        environment=AuditEnvironment.production,
        status=AuditStatus.queued,
    )
    db.add_all([staging_audit, production_audit])
    db.flush()
    staging_audit.companion_audit_id = production_audit.id
    production_audit.companion_audit_id = staging_audit.id
    db.commit()
    db.refresh(staging_audit)
    db.refresh(production_audit)

    queue.enqueue(run_audit, staging_audit.id)
    queue.enqueue(run_audit, production_audit.id)
    return [production_audit, staging_audit]


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


@router.get("/audits/{audit_id}/diff", response_model=DiffResponse)
def get_audit_diff(
    audit_id: str,
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    """Return the diff for a paired audit. Pending if either side hasn't completed."""
    audit = db.get(Audit, audit_id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="audit not found")

    project = audit.project
    if viewer.role != Role.admin and project.owner_id != viewer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="audit not found")

    # Always show the production-side view of the diff (where rows are stored).
    primary = audit
    if audit.environment != AuditEnvironment.production and audit.companion is not None:
        primary = audit.companion

    companion = primary.companion
    if companion is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="audit is not part of a staging/production pair",
        )

    pair_complete = (
        primary.status == AuditStatus.completed and companion.status == AuditStatus.completed
    )

    return DiffResponse(
        audit_id=primary.id,
        companion_audit_id=companion.id,
        pair_complete=pair_complete,
        verdict=primary.verdict,
        diffs=[AuditDiffOut.model_validate(d) for d in primary.diffs],
    )


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
