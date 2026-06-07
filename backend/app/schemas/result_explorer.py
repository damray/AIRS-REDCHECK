from datetime import datetime

from pydantic import BaseModel


class ResultAttemptRead(BaseModel):
    attempt_id: str
    dataset_id: str
    stream_id: str
    external_stream_id: str | None
    input_type: str
    attempt_index: int
    source_prompt: str
    source_output: str
    source_verdict: str | None
    judge_verdict: str | None
    comparison_status: str | None
    review_decision: str | None
    reviewer_identity: str | None
    reviewed_at: datetime | None
    evaluation_error_code: str | None
    evaluation_error_message: str | None
    evaluation_error_created_at: datetime | None
    severity: object | None
    category: object | None
    technique: object | None
    created_at: datetime


class PaginatedResults(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ResultAttemptRead]


class StreamTimelineRead(BaseModel):
    stream_id: str
    external_stream_id: str | None
    input_type: str
    goal: str | None
    attempts: list[ResultAttemptRead]


class AutomatedTriageSummary(BaseModel):
    total_streams: int
    total_attempts: int
    processed_attempts: int
    remaining_attempts: int
    errors: int
    agreements: int
    disagreements: int
    source_stricter_than_judge: int
    judge_stricter_than_source: int
    uncertain: int
    review_required: int
    agent_streams: int
    static_streams: int
    average_attempts_per_stream: float
