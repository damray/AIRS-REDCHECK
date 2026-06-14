import csv
import json
from datetime import UTC, datetime
from io import StringIO
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    Attempt,
    Dataset,
    EvaluationError,
    HumanReview,
    JudgeResultRecord,
    Project,
    Stream,
)
from app.schemas.human_review import HumanReviewCreate, HumanReviewRead, ReviewedQualityMetrics
from app.schemas.result_explorer import (
    AutomatedTriageSummary,
    PaginatedResults,
    ResultAttemptRead,
    StreamTimelineRead,
)

router = APIRouter(prefix="/results", tags=["results"])
RESULT_TEXT_EXCERPT_CHARS = 500

EXPORT_COLUMNS = [
    "attempt_id",
    "dataset_id",
    "stream_id",
    "external_stream_id",
    "input_type",
    "attempt_index",
    "source_prompt",
    "source_output",
    "source_verdict",
    "judge_verdict",
    "comparison_status",
    "review_decision",
    "reviewer_identity",
    "reviewed_at",
    "severity",
    "category",
    "technique",
    "created_at",
]


@router.get("/attempts", response_model=PaginatedResults)
def list_result_attempts(
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str | None, Query()] = None,
    comparison_status: Annotated[list[str] | None, Query()] = None,
    source_verdict: Annotated[str | None, Query()] = None,
    judge_verdict: Annotated[str | None, Query()] = None,
    input_type: Annotated[str | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
    severity: Annotated[str | None, Query()] = None,
    technique: Annotated[str | None, Query()] = None,
    reviewed: Annotated[bool | None, Query()] = None,
    review_decision: Annotated[str | None, Query()] = None,
    stream_id: Annotated[str | None, Query()] = None,
    source_prompt_contains: Annotated[str | None, Query()] = None,
    source_output_contains: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResults:
    statement = _filtered_statement(
        comparison_status=comparison_status,
        source_verdict=source_verdict,
        judge_verdict=judge_verdict,
        input_type=input_type,
        category=category,
        severity=severity,
        technique=technique,
        reviewed=reviewed,
        review_decision=review_decision,
        stream_id=stream_id,
        source_prompt_contains=source_prompt_contains,
        source_output_contains=source_output_contains,
        q=q,
        project_id=project_id,
    )
    total = db.execute(select(func.count()).select_from(statement.subquery())).scalar_one()
    rows = db.execute(
        statement.order_by(Attempt.created_at, Attempt.id).limit(limit).offset(offset)
    ).all()

    return PaginatedResults(
        total=total,
        limit=limit,
        offset=offset,
        items=[_row_to_result(*row, full_text=False) for row in rows],
    )


@router.get("/export/normalized.csv")
def export_normalized_results(
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str | None, Query()] = None,
) -> Response:
    return _csv_export_response(
        filename="airs-redcheck-normalized-results.csv",
        rows=_export_rows(db, _base_statement(project_id=project_id)),
    )


@router.get("/export/disagreements.csv")
def export_disagreements(
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str | None, Query()] = None,
) -> Response:
    statement = _filtered_statement(
        comparison_status=[
            "SOURCE_STRICTER_THAN_JUDGE",
            "JUDGE_STRICTER_THAN_SOURCE",
            "REVIEW_REQUIRED",
        ],
        source_verdict=None,
        judge_verdict=None,
        input_type=None,
        category=None,
        severity=None,
        technique=None,
        reviewed=None,
        review_decision=None,
        stream_id=None,
        source_prompt_contains=None,
        source_output_contains=None,
        q=None,
        project_id=project_id,
    )
    return _csv_export_response(
        filename="airs-redcheck-disagreements.csv",
        rows=_export_rows(db, statement),
    )


@router.get("/export/reviewed.csv")
def export_reviewed_cases(
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str | None, Query()] = None,
) -> Response:
    statement = _filtered_statement(
        comparison_status=None,
        source_verdict=None,
        judge_verdict=None,
        input_type=None,
        category=None,
        severity=None,
        technique=None,
        reviewed=True,
        review_decision=None,
        stream_id=None,
        source_prompt_contains=None,
        source_output_contains=None,
        q=None,
        project_id=project_id,
    )
    return _csv_export_response(
        filename="airs-redcheck-reviewed-cases.csv",
        rows=_export_rows(db, statement),
    )


@router.get("/export/current.csv")
def export_filtered_results(
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str | None, Query()] = None,
    comparison_status: Annotated[list[str] | None, Query()] = None,
    source_verdict: Annotated[str | None, Query()] = None,
    judge_verdict: Annotated[str | None, Query()] = None,
    input_type: Annotated[str | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
    severity: Annotated[str | None, Query()] = None,
    technique: Annotated[str | None, Query()] = None,
    reviewed: Annotated[bool | None, Query()] = None,
    review_decision: Annotated[str | None, Query()] = None,
    stream_id: Annotated[str | None, Query()] = None,
    source_prompt_contains: Annotated[str | None, Query()] = None,
    source_output_contains: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
) -> Response:
    statement = _filtered_statement(
        comparison_status=comparison_status,
        source_verdict=source_verdict,
        judge_verdict=judge_verdict,
        input_type=input_type,
        category=category,
        severity=severity,
        technique=technique,
        reviewed=reviewed,
        review_decision=review_decision,
        stream_id=stream_id,
        source_prompt_contains=source_prompt_contains,
        source_output_contains=source_output_contains,
        q=q,
        project_id=project_id,
    )
    return _csv_export_response(
        filename="airs-redcheck-filtered-results.csv",
        rows=_export_rows(db, statement),
    )


@router.get("/streams/{stream_id}/timeline", response_model=StreamTimelineRead)
def get_stream_timeline(
    stream_id: str,
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str | None, Query()] = None,
) -> StreamTimelineRead:
    stream = db.scalar(
        select(Stream)
        .join(Dataset, Dataset.id == Stream.dataset_id)
        .join(Project, Project.id == Dataset.project_id)
        .where(
            Stream.id == stream_id,
            Project.is_archived.is_(False),
            *([Dataset.project_id == project_id] if project_id is not None else []),
        )
    )
    if stream is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found.")

    statement = _base_statement(project_id=project_id).where(Attempt.stream_id == stream_id)
    rows = db.execute(
        statement.order_by(Attempt.attempt_index, Attempt.created_at, Attempt.id)
    ).all()
    return StreamTimelineRead(
        stream_id=stream.id,
        external_stream_id=stream.external_stream_id,
        input_type=stream.input_type,
        goal=stream.goal,
        attempts=[_row_to_result(*row, full_text=False) for row in rows],
    )


@router.get("/attempts/{attempt_id}", response_model=ResultAttemptRead)
def get_result_attempt_detail(
    attempt_id: str,
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str | None, Query()] = None,
) -> ResultAttemptRead:
    row = db.execute(_base_statement(project_id=project_id).where(Attempt.id == attempt_id)).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found.")
    return _row_to_result(*row, full_text=True)


@router.put(
    "/attempts/{attempt_id}/review",
    response_model=HumanReviewRead,
    status_code=status.HTTP_200_OK,
)
def upsert_attempt_review(
    attempt_id: str,
    review_input: HumanReviewCreate,
    db: Annotated[Session, Depends(get_db)],
) -> HumanReview:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found.")

    review = db.scalar(select(HumanReview).where(HumanReview.attempt_id == attempt_id))
    if review is None:
        review = HumanReview(
            dataset_id=attempt.dataset_id,
            stream_id=attempt.stream_id,
            attempt_id=attempt.id,
            decision=review_input.decision,
            reviewer_identity=review_input.reviewer_identity,
            comment=review_input.comment,
        )
        db.add(review)
    else:
        review.decision = review_input.decision
        review.reviewer_identity = review_input.reviewer_identity
        review.comment = review_input.comment
        review.reviewed_at = datetime.now(UTC)

    db.commit()
    db.refresh(review)
    return review


@router.get("/attempts/{attempt_id}/review", response_model=HumanReviewRead)
def get_attempt_review(
    attempt_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> HumanReview:
    review = db.scalar(select(HumanReview).where(HumanReview.attempt_id == attempt_id))
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")
    return review


@router.get("/reviewed-quality", response_model=ReviewedQualityMetrics)
def get_reviewed_quality_metrics(
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str | None, Query()] = None,
) -> ReviewedQualityMetrics:
    base_attempt_ids = _active_attempt_ids_statement(project_id)
    rows = db.execute(
        select(Attempt, HumanReview)
        .join(HumanReview, HumanReview.attempt_id == Attempt.id)
        .where(Attempt.id.in_(base_attempt_ids))
    ).all()
    total_attempts = db.execute(
        select(func.count()).select_from(Attempt).where(Attempt.id.in_(base_attempt_ids))
    ).scalar_one()

    counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    alarm_threat_cases = 0
    metric_cases = 0
    for attempt, review in rows:
        if review.decision in {"ALARM_THREAT", "AMBIGUOUS"}:
            alarm_threat_cases += 1
        judge_result = _latest_judge_result(db, attempt.id)
        actual_verdict = _human_confirmed_verdict(attempt, judge_result, review)
        source_verdict = _normalized_binary_verdict(attempt.source_threat_normalized)
        if source_verdict is None or actual_verdict is None:
            continue
        metric_cases += 1
        if source_verdict == "THREAT" and actual_verdict == "THREAT":
            counts["tp"] += 1
        elif source_verdict == "SAFE" and actual_verdict == "SAFE":
            counts["tn"] += 1
        elif source_verdict == "THREAT" and actual_verdict == "SAFE":
            counts["fp"] += 1
        elif source_verdict == "SAFE" and actual_verdict == "THREAT":
            counts["fn"] += 1

    reviewed_cases = len(rows)
    accuracy = _safe_divide(counts["tp"] + counts["tn"], metric_cases)
    precision = _safe_divide(counts["tp"], counts["tp"] + counts["fp"])
    recall = _safe_divide(counts["tp"], counts["tp"] + counts["fn"])
    f1_score = (
        None
        if precision is None or recall is None or precision + recall == 0
        else 2 * precision * recall / (precision + recall)
    )

    return ReviewedQualityMetrics(
        total_attempts=total_attempts,
        reviewed_cases=reviewed_cases,
        alarm_threat_cases=alarm_threat_cases,
        metric_cases=metric_cases,
        review_coverage=_safe_divide(reviewed_cases, total_attempts) or 0.0,
        confirmed_tp=counts["tp"],
        confirmed_tn=counts["tn"],
        confirmed_fp=counts["fp"],
        confirmed_fn=counts["fn"],
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=f1_score,
    )


@router.get("/triage-summary", response_model=AutomatedTriageSummary)
def get_automated_triage_summary(
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str | None, Query()] = None,
) -> AutomatedTriageSummary:
    active_stream_ids = _active_stream_ids_statement(project_id)
    active_attempt_ids = _active_attempt_ids_statement(project_id)
    total_streams = db.execute(
        select(func.count()).select_from(Stream).where(Stream.id.in_(active_stream_ids))
    ).scalar_one()
    total_attempts = db.execute(
        select(func.count()).select_from(Attempt).where(Attempt.id.in_(active_attempt_ids))
    ).scalar_one()
    judge_statuses = list(
        db.execute(
            select(JudgeResultRecord.comparison_status).where(
                JudgeResultRecord.comparison_status.is_not(None),
                JudgeResultRecord.attempt_id.in_(active_attempt_ids),
            )
        ).scalars()
    )
    error_count = db.execute(
        select(func.count())
        .select_from(EvaluationError)
        .where(EvaluationError.attempt_id.in_(active_attempt_ids))
    ).scalar_one()
    error_statuses = list(
        db.execute(
            select(EvaluationError.comparison_status).where(
                EvaluationError.comparison_status.is_not(None),
                EvaluationError.attempt_id.in_(active_attempt_ids),
            )
        ).scalars()
    )
    processed_attempt_ids = set(
        db.execute(
            select(JudgeResultRecord.attempt_id)
            .where(JudgeResultRecord.attempt_id.in_(active_attempt_ids))
            .distinct()
        ).scalars()
    ) | set(
        db.execute(
            select(EvaluationError.attempt_id)
            .where(EvaluationError.attempt_id.in_(active_attempt_ids))
            .distinct()
        ).scalars()
    )
    agent_streams = db.execute(
        select(func.count())
        .select_from(Stream)
        .where(Stream.input_type == "agent", Stream.id.in_(active_stream_ids))
    ).scalar_one()
    static_streams = db.execute(
        select(func.count())
        .select_from(Stream)
        .where(Stream.input_type == "static", Stream.id.in_(active_stream_ids))
    ).scalar_one()
    statuses = judge_statuses + error_statuses
    agreement_count = statuses.count("AGREEMENT_THREAT") + statuses.count("AGREEMENT_SAFE")
    source_stricter = statuses.count("SOURCE_STRICTER_THAN_JUDGE")
    judge_stricter = statuses.count("JUDGE_STRICTER_THAN_SOURCE")
    review_required = statuses.count("REVIEW_REQUIRED")

    return AutomatedTriageSummary(
        total_streams=total_streams,
        total_attempts=total_attempts,
        processed_attempts=len(processed_attempt_ids),
        remaining_attempts=max(total_attempts - len(processed_attempt_ids), 0),
        errors=error_count,
        agreements=agreement_count,
        disagreements=source_stricter + judge_stricter,
        source_stricter_than_judge=source_stricter,
        judge_stricter_than_source=judge_stricter,
        uncertain=review_required,
        review_required=review_required,
        agent_streams=agent_streams,
        static_streams=static_streams,
        average_attempts_per_stream=_safe_divide(total_attempts, total_streams) or 0.0,
    )


def _base_statement(project_id: str | None = None) -> Select[Any]:
    statement = (
        select(Attempt, Stream, JudgeResultRecord, EvaluationError, HumanReview)
        .join(Stream, Stream.id == Attempt.stream_id)
        .join(Dataset, Dataset.id == Attempt.dataset_id)
        .join(Project, Project.id == Dataset.project_id)
        .outerjoin(JudgeResultRecord, JudgeResultRecord.attempt_id == Attempt.id)
        .outerjoin(EvaluationError, EvaluationError.attempt_id == Attempt.id)
        .outerjoin(HumanReview, HumanReview.attempt_id == Attempt.id)
        .where(Project.is_archived.is_(False))
    )
    if project_id is not None:
        statement = statement.where(Dataset.project_id == project_id)
    return statement


def _filtered_statement(
    *,
    comparison_status: list[str] | None,
    source_verdict: str | None,
    judge_verdict: str | None,
    input_type: str | None,
    category: str | None,
    severity: str | None,
    technique: str | None,
    reviewed: bool | None,
    review_decision: str | None,
    stream_id: str | None,
    source_prompt_contains: str | None,
    source_output_contains: str | None,
    q: str | None,
    project_id: str | None,
) -> Select[Any]:
    statement = _base_statement(project_id=project_id)
    if comparison_status:
        statement = statement.where(
            or_(
                JudgeResultRecord.comparison_status.in_(comparison_status),
                EvaluationError.comparison_status.in_(comparison_status),
            )
        )
    if source_verdict is not None:
        statement = statement.where(Attempt.source_threat_normalized == source_verdict)
    if judge_verdict is not None:
        statement = statement.where(JudgeResultRecord.response_verdict == judge_verdict)
    if input_type is not None:
        statement = statement.where(Stream.input_type == input_type)
    if category is not None:
        statement = statement.where(Attempt.attempt_metadata["category"].as_string() == category)
    if severity is not None:
        statement = statement.where(Attempt.attempt_metadata["severity"].as_string() == severity)
    if technique is not None:
        techniques = Attempt.attempt_metadata["techniques"]
        statement = statement.where(
            or_(
                techniques.as_string() == technique,
                cast(techniques, String).like(f'%"{technique}"%'),
            )
        )
    if reviewed is not None:
        statement = statement.where(
            HumanReview.id.is_not(None) if reviewed else HumanReview.id.is_(None)
        )
    if review_decision is not None:
        statement = statement.where(HumanReview.decision == review_decision)
    if stream_id is not None:
        statement = statement.where(Attempt.stream_id == stream_id)
    if source_prompt_contains is not None:
        statement = statement.where(
            Attempt.source_prompt.ilike(_contains_pattern(source_prompt_contains), escape="\\")
        )
    if source_output_contains is not None:
        statement = statement.where(
            Attempt.source_output.ilike(_contains_pattern(source_output_contains), escape="\\")
        )
    if q is not None:
        pattern = _contains_pattern(q)
        statement = statement.where(
            or_(
                Attempt.source_prompt.ilike(pattern, escape="\\"),
                Attempt.source_output.ilike(pattern, escape="\\"),
            )
        )
    return statement


def _active_attempt_ids_statement(project_id: str | None) -> Select[tuple[str]]:
    statement = (
        select(Attempt.id)
        .join(Dataset, Dataset.id == Attempt.dataset_id)
        .join(Project, Project.id == Dataset.project_id)
        .where(Project.is_archived.is_(False))
    )
    if project_id is not None:
        statement = statement.where(Dataset.project_id == project_id)
    return statement


def _active_stream_ids_statement(project_id: str | None) -> Select[tuple[str]]:
    statement = (
        select(Stream.id)
        .join(Dataset, Dataset.id == Stream.dataset_id)
        .join(Project, Project.id == Dataset.project_id)
        .where(Project.is_archived.is_(False))
    )
    if project_id is not None:
        statement = statement.where(Dataset.project_id == project_id)
    return statement


def _contains_pattern(value: str) -> str:
    escaped = value.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _row_to_result(
    attempt: Attempt,
    stream: Stream,
    judge_result: JudgeResultRecord | None,
    evaluation_error: EvaluationError | None,
    human_review: HumanReview | None,
    *,
    full_text: bool,
) -> ResultAttemptRead:
    metadata = attempt.attempt_metadata
    comparison_status = (
        judge_result.comparison_status
        if judge_result is not None
        else evaluation_error.comparison_status
        if evaluation_error is not None
        else None
    )
    return ResultAttemptRead(
        attempt_id=attempt.id,
        dataset_id=attempt.dataset_id,
        stream_id=stream.id,
        external_stream_id=stream.external_stream_id,
        input_type=stream.input_type,
        attempt_index=attempt.attempt_index,
        source_prompt=(
            attempt.source_prompt if full_text else _text_excerpt(attempt.source_prompt)
        ),
        source_output=(
            attempt.source_output if full_text else _text_excerpt(attempt.source_output)
        ),
        source_verdict=attempt.source_threat_normalized,
        judge_verdict=judge_result.response_verdict if judge_result is not None else None,
        comparison_status=comparison_status,
        review_decision=human_review.decision if human_review is not None else None,
        reviewer_identity=human_review.reviewer_identity if human_review is not None else None,
        reviewed_at=human_review.reviewed_at if human_review is not None else None,
        evaluation_error_code=(
            evaluation_error.error_code if evaluation_error is not None else None
        ),
        evaluation_error_message=(
            evaluation_error.message if evaluation_error is not None else None
        ),
        evaluation_error_created_at=(
            evaluation_error.created_at if evaluation_error is not None else None
        ),
        severity=metadata.get("severity"),
        category=metadata.get("category"),
        technique=metadata.get("techniques"),
        created_at=attempt.created_at,
    )


def _export_rows(db: Session, statement: Select[Any]) -> list[ResultAttemptRead]:
    rows = db.execute(statement.order_by(Attempt.created_at, Attempt.id)).all()
    return [_row_to_result(*row, full_text=True) for row in rows]


def _csv_export_response(filename: str, rows: list[ResultAttemptRead]) -> Response:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow(_export_row(row))
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _export_row(row: ResultAttemptRead) -> dict[str, str]:
    dumped = row.model_dump()
    return {column: _csv_value(dumped[column]) for column in EXPORT_COLUMNS}


def _csv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list | dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _text_excerpt(value: str) -> str:
    if len(value) <= RESULT_TEXT_EXCERPT_CHARS:
        return value
    return f"{value[: RESULT_TEXT_EXCERPT_CHARS - 3]}..."


def _human_confirmed_verdict(
    attempt: Attempt,
    judge_result: JudgeResultRecord | None,
    review: HumanReview,
) -> str | None:
    if review.decision == "CONFIRM_SOURCE":
        return _normalized_binary_verdict(attempt.source_threat_normalized)
    if review.decision == "CONFIRM_JUDGE" and judge_result is not None:
        return _normalized_binary_verdict(judge_result.response_verdict)
    if review.decision in {"ALARM_THREAT", "AMBIGUOUS"}:
        return "THREAT"
    return None


def _latest_judge_result(db: Session, attempt_id: str) -> JudgeResultRecord | None:
    return db.scalar(
        select(JudgeResultRecord)
        .where(JudgeResultRecord.attempt_id == attempt_id)
        .order_by(JudgeResultRecord.created_at.desc(), JudgeResultRecord.id.desc())
        .limit(1)
    )


def _normalized_binary_verdict(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized if normalized in {"THREAT", "SAFE"} else None


def _safe_divide(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator
