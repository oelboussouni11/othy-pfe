from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.projects import (
    Forbidden,
    NotFound,
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_(db: Session = Depends(get_db), viewer: User = Depends(get_current_user)):
    return list_projects(db, viewer)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    return create_project(db, viewer, payload)


@router.get("/{project_id}", response_model=ProjectOut)
def get_(
    project_id: str,
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    try:
        return get_project(db, viewer, project_id)
    except NotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.patch("/{project_id}", response_model=ProjectOut)
def patch(
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    try:
        return update_project(db, viewer, project_id, payload)
    except NotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Forbidden as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    project_id: str,
    db: Session = Depends(get_db),
    viewer: User = Depends(get_current_user),
):
    try:
        delete_project(db, viewer, project_id)
    except NotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Forbidden as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
