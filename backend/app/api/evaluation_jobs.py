from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Dataset, EvaluationJob, Project
from app.schemas.evaluation_job import (
    EvaluationJobCreate,
    EvaluationJobRead,
    EvaluationJobRetryFailed,
    EvaluationJobStatusRead,
)
from app.services.evaluation_jobs import EvaluationJobService, EvaluationJobServiceError

router = APIRouter(prefix="/evaluation-jobs", tags=["evaluation-jobs"])


@router.get("", response_model=list[EvaluationJobRead])
def list_evaluation_jobs(
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str | None, Query()] = None,
    include_archived: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EvaluationJob]:
    statement = (
        select(EvaluationJob)
        .join(Dataset, Dataset.id == EvaluationJob.dataset_id)
        .join(Project, Project.id == Dataset.project_id)
    )
    if project_id is not None:
        statement = statement.where(Dataset.project_id == project_id)
    if not include_archived:
        statement = statement.where(Project.is_archived.is_(False))
    return list(
        db.execute(
            statement.order_by(EvaluationJob.created_at.desc(), EvaluationJob.id)
            .limit(limit)
            .offset(offset)
        ).scalars()
    )


@router.post("", response_model=EvaluationJobRead, status_code=status.HTTP_201_CREATED)
def create_evaluation_job(
    payload: EvaluationJobCreate,
    db: Annotated[Session, Depends(get_db)],
) -> EvaluationJob:
    try:
        return EvaluationJobService(db).create_job(
            dataset_id=payload.dataset_id,
            portkey_gateway_profile_id=payload.portkey_gateway_profile_id,
            judge_prompt_profile_id=payload.judge_prompt_profile_id,
            retry_limit=payload.retry_limit,
            attempt_ids=payload.attempt_ids,
        )
    except EvaluationJobServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{job_id}", response_model=EvaluationJobStatusRead)
def get_evaluation_job(job_id: str, db: Annotated[Session, Depends(get_db)]) -> EvaluationJob:
    job = db.get(EvaluationJob, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation job not found."
        )
    return job


@router.post("/{job_id}/retry-failed", response_model=EvaluationJobRead)
def retry_failed_attempts(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    payload: EvaluationJobRetryFailed | None = None,
) -> EvaluationJob:
    try:
        return EvaluationJobService(db).retry_failed_attempts(
            job_id=job_id,
            attempt_ids=payload.attempt_ids if payload is not None else None,
        )
    except EvaluationJobServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
