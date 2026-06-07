from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvaluationJobCreate(BaseModel):
    dataset_id: str
    portkey_gateway_profile_id: str
    judge_prompt_profile_id: str | None = None
    retry_limit: int = Field(default=2, ge=0, le=10)
    attempt_ids: list[str] | None = None


class EvaluationJobRetryFailed(BaseModel):
    attempt_ids: list[str] | None = None


class EvaluationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    portkey_gateway_profile_id: str
    judge_prompt_profile_id: str | None
    prompt_hash: str | None
    model_name: str | None
    routing_mode: str | None
    provider_slug: str | None
    config_id: str | None
    timeout_seconds: int | None
    temperature: float | None
    status: str
    retry_limit: int
    total_attempts: int
    processed_attempts: int
    succeeded_attempts: int
    failed_attempts: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class EvaluationJobAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    attempt_id: str
    status: str
    retry_count: int
    max_retries: int
    last_error_code: str | None
    last_error_message: str | None
    latency_ms: int | None
    token_usage: object | None
    cost: float | None


class EvaluationJobStatusRead(EvaluationJobRead):
    job_attempts: list[EvaluationJobAttemptRead]
