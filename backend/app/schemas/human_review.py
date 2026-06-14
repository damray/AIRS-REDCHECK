from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

HumanReviewDecision = Literal["CONFIRM_SOURCE", "CONFIRM_JUDGE", "ALARM_THREAT"]


class HumanReviewCreate(BaseModel):
    decision: HumanReviewDecision
    reviewer_identity: str = Field(min_length=1, max_length=255)
    comment: str | None = None


class HumanReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    stream_id: str
    attempt_id: str
    decision: str
    reviewer_identity: str
    comment: str | None
    reviewed_at: datetime
    created_at: datetime
    updated_at: datetime


class ReviewedQualityMetrics(BaseModel):
    total_attempts: int
    reviewed_cases: int
    alarm_threat_cases: int
    metric_cases: int
    review_coverage: float
    confirmed_tp: int
    confirmed_tn: int
    confirmed_fp: int
    confirmed_fn: int
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1_score: float | None
