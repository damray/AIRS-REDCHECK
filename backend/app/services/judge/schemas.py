from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ResponseVerdict = Literal["THREAT", "SAFE", "UNCERTAIN"]
ResponseBehavior = Literal[
    "SAFE_REFUSAL",
    "SAFE_REDIRECT",
    "SAFE_COMPLETION",
    "UNSAFE_COMPLETION",
    "AMBIGUOUS",
]


class JudgeRequest(BaseModel):
    system_prompt: str
    prompt: str
    output: str
    rubric: str
    goal: str | None = None


class JudgeResult(BaseModel):
    response_verdict: ResponseVerdict
    confidence: float = Field(ge=0, le=1)
    response_behavior: ResponseBehavior
    risk_category: str
    explanation: str
    evidence_excerpt: str | None = None


class JudgeAdapterResponse(BaseModel):
    result: JudgeResult
    raw_response: dict[str, Any]
    latency_ms: int | None = None
    token_usage: dict[str, Any] | None = None
    cost: float | None = None


class JudgeAdapterError(Exception):
    def __init__(self, error_code: str, message: str, raw_response: Any | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.raw_response = raw_response


class EvaluationErrorCreate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    dataset_id: str
    stream_id: str
    attempt_id: str
    error_code: str
    message: str
    raw_response: Any | None = None
    portkey_gateway_profile_id: str | None = None
