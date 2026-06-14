import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import (
    Attempt,
    Dataset,
    EvaluationError,
    EvaluationJob,
    EvaluationJobAttempt,
    HumanReview,
    ImportErrorRecord,
    JudgeResultRecord,
    Project,
    Stream,
)
from app.parsers.flat_mapping import FlatMappingConfig
from app.schemas.dataset import AttemptRead, DatasetRead, DatasetUpdate, StreamRead
from app.schemas.import_error import ImportErrorRead
from app.schemas.import_summary import ImportSummary
from app.services.import_service import ImportRequest, ImportService, ImportServiceError

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _format_bytes(size: int) -> str:
    if size % (1024 * 1024) == 0:
        return f"{size // (1024 * 1024)} MiB"
    if size % 1024 == 0:
        return f"{size // 1024} KiB"
    return f"{size} bytes"


@router.delete("", status_code=status.HTTP_200_OK)
def reset_imported_datasets(db: Annotated[Session, Depends(get_db)]) -> dict[str, int]:
    dataset_count = db.execute(select(func.count()).select_from(Dataset)).scalar_one()
    attempt_count = db.execute(select(func.count()).select_from(Attempt)).scalar_one()

    for model in (
        JudgeResultRecord,
        EvaluationError,
        EvaluationJobAttempt,
        HumanReview,
        EvaluationJob,
        ImportErrorRecord,
        Attempt,
        Stream,
        Dataset,
        Project,
    ):
        db.execute(delete(model))
    db.commit()

    return {"deleted_datasets": dataset_count, "deleted_attempts": attempt_count}


@router.get("", response_model=list[DatasetRead])
def list_datasets(
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str | None, Query()] = None,
    include_archived: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Dataset]:
    statement = select(Dataset).join(Project, Project.id == Dataset.project_id)
    if project_id is not None:
        statement = statement.where(Dataset.project_id == project_id)
    if not include_archived:
        statement = statement.where(Project.is_archived.is_(False))
    return list(
        db.execute(
            statement.order_by(Dataset.created_at.desc(), Dataset.id).limit(limit).offset(offset)
        ).scalars()
    )


@router.post("/import", response_model=ImportSummary, status_code=status.HTTP_201_CREATED)
async def import_dataset(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    content_type: Annotated[str, Header(alias="Content-Type")] = "application/json",
    name: Annotated[str | None, Query()] = None,
    scan_name: Annotated[str | None, Query()] = None,
    filename: Annotated[str | None, Query()] = None,
    project_id: Annotated[str | None, Query()] = None,
    project_name: Annotated[str | None, Query()] = None,
    mapping_profile_id: Annotated[str | None, Query()] = None,
    prompt_column: Annotated[str | None, Query()] = None,
    output_column: Annotated[str | None, Query()] = None,
    source_threat_column: Annotated[str | None, Query()] = None,
    optional_field_columns: Annotated[str | None, Query()] = None,
) -> ImportSummary:
    content = await request.body()
    settings = get_settings()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                "Upload exceeds configured maximum size "
                f"of {_format_bytes(settings.max_upload_bytes)}."
            ),
        )

    try:
        flat_mapping = _inline_mapping(
            prompt_column=prompt_column,
            output_column=output_column,
            source_threat_column=source_threat_column,
            optional_field_columns=optional_field_columns,
        )
        dataset = ImportService(db).import_dataset(
            ImportRequest(
                content=content,
                content_type=content_type,
                name=name,
                scan_name=scan_name,
                filename=filename,
                project_id=project_id,
                project_name=project_name,
                mapping_profile_id=mapping_profile_id,
                flat_mapping=flat_mapping,
            )
        )
    except ImportServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ImportSummary(
        dataset_id=dataset.id,
        project_id=dataset.project_id,
        scan_name=dataset.scan_name,
        detected_format=dataset.detected_format,
        stream_count=dataset.stream_count,
        attempt_count=dataset.attempt_count,
        imported_count=dataset.attempt_count,
        error_count=dataset.error_count,
        status=dataset.import_status,
    )


@router.get("/{dataset_id}", response_model=DatasetRead)
def get_dataset(dataset_id: str, db: Annotated[Session, Depends(get_db)]) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    return dataset


@router.put("/{dataset_id}", response_model=DatasetRead)
def rename_dataset_scan(
    dataset_id: str,
    payload: DatasetUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    dataset.scan_name = payload.scan_name.strip()
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("/{dataset_id}/streams", response_model=list[StreamRead])
def list_streams(
    dataset_id: str,
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Stream]:
    _ensure_dataset(db, dataset_id)
    return list(
        db.execute(
            select(Stream)
            .where(Stream.dataset_id == dataset_id)
            .order_by(Stream.created_at, Stream.id)
            .limit(limit)
            .offset(offset)
        ).scalars()
    )


@router.get("/{dataset_id}/attempts", response_model=list[AttemptRead])
def list_attempts(
    dataset_id: str,
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Attempt]:
    _ensure_dataset(db, dataset_id)
    return list(
        db.execute(
            select(Attempt)
            .where(Attempt.dataset_id == dataset_id)
            .order_by(Attempt.created_at, Attempt.id)
            .limit(limit)
            .offset(offset)
        ).scalars()
    )


@router.get("/{dataset_id}/import-errors", response_model=list[ImportErrorRead])
def list_import_errors(
    dataset_id: str,
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ImportErrorRecord]:
    _ensure_dataset(db, dataset_id, project_id=project_id)
    return list(
        db.execute(
            select(ImportErrorRecord)
            .where(ImportErrorRecord.dataset_id == dataset_id)
            .order_by(ImportErrorRecord.created_at, ImportErrorRecord.id)
            .limit(limit)
            .offset(offset)
        ).scalars()
    )


def _ensure_dataset(db: Session, dataset_id: str, project_id: str | None = None) -> None:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    if project_id is not None and dataset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")


def _inline_mapping(
    prompt_column: str | None,
    output_column: str | None,
    source_threat_column: str | None,
    optional_field_columns: str | None,
) -> FlatMappingConfig | None:
    supplied_required = [prompt_column, output_column, source_threat_column]
    if all(value is None for value in supplied_required) and optional_field_columns is None:
        return None
    if not all(supplied_required):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prompt_column, output_column, and source_threat_column are required together.",
        )

    try:
        optional_mapping = (
            json.loads(optional_field_columns) if optional_field_columns is not None else {}
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="optional_field_columns must be a JSON object.",
        ) from exc
    if not isinstance(optional_mapping, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="optional_field_columns must be a JSON object.",
        )

    try:
        return FlatMappingConfig(
            prompt_column=prompt_column or "",
            output_column=output_column or "",
            source_threat_column=source_threat_column or "",
            optional_field_columns={
                str(field): str(column) for field, column in optional_mapping.items()
            },
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
