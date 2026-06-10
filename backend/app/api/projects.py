from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Dataset, EvaluationJob, Project
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])
RUNNING_JOB_STATUSES = {"PENDING", "RUNNING", "RETRYING"}


@router.get("", response_model=list[ProjectRead])
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    include_archived: Annotated[bool, Query()] = False,
) -> list[ProjectRead]:
    statement = (
        select(
            Project,
            func.count(Dataset.id).label("import_count"),
            func.max(Dataset.updated_at).label("latest_activity_at"),
        )
        .outerjoin(Dataset, Dataset.project_id == Project.id)
        .group_by(Project.id)
        .order_by(func.max(Dataset.updated_at).desc().nullslast(), Project.created_at.desc())
    )
    if not include_archived:
        statement = statement.where(Project.is_archived.is_(False))
    return [_project_row_to_read(*row) for row in db.execute(statement).all()]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Annotated[Session, Depends(get_db)]) -> ProjectRead:
    project = Project(name=payload.name.strip())
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_row_to_read(project, 0, None)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Annotated[Session, Depends(get_db)]) -> ProjectRead:
    project = _get_project(db, project_id)
    import_count, latest_activity_at = _project_stats(db, project.id)
    return _project_row_to_read(project, import_count, latest_activity_at)


@router.put("/{project_id}", response_model=ProjectRead)
def rename_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> ProjectRead:
    project = _get_project(db, project_id)
    project.name = payload.name.strip()
    db.commit()
    db.refresh(project)
    import_count, latest_activity_at = _project_stats(db, project.id)
    return _project_row_to_read(project, import_count, latest_activity_at)


@router.delete("/{project_id}", response_model=ProjectRead)
def archive_project(project_id: str, db: Annotated[Session, Depends(get_db)]) -> ProjectRead:
    project = _get_project(db, project_id)
    running_jobs = db.scalar(
        select(func.count())
        .select_from(EvaluationJob)
        .join(Dataset, Dataset.id == EvaluationJob.dataset_id)
        .where(
            Dataset.project_id == project_id,
            EvaluationJob.status.in_(RUNNING_JOB_STATUSES),
        )
    )
    if running_jobs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project has running evaluation jobs.",
        )

    project.is_archived = True
    project.archived_at = datetime.now(UTC)
    db.commit()
    db.refresh(project)
    import_count, latest_activity_at = _project_stats(db, project.id)
    return _project_row_to_read(project, import_count, latest_activity_at)


def _get_project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return project


def _project_stats(db: Session, project_id: str) -> tuple[int, datetime | None]:
    row = db.execute(
        select(func.count(Dataset.id), func.max(Dataset.updated_at)).where(
            Dataset.project_id == project_id
        )
    ).one()
    return int(row[0]), row[1]


def _project_row_to_read(
    project: Project,
    import_count: int,
    latest_activity_at: datetime | None,
) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        name=project.name,
        is_archived=project.is_archived,
        import_count=int(import_count),
        latest_activity_at=latest_activity_at,
        archived_at=project.archived_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
