from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


class NormalizedAttempt(BaseModel):
    attempt_index: int
    prompt: str
    output: str
    source_threat_raw: str
    source_threat_normalized: str | None = None
    source_score_raw: Any | None = None
    source_reasoning: str | None = None
    raw_payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedStream(BaseModel):
    external_stream_id: str | None = None
    input_type: Literal["static", "agent"]
    goal: str | None = None
    stream_threat_raw: str | None = None
    stream_threat_normalized: str | None = None
    raw_payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    attempts: list[NormalizedAttempt] = Field(default_factory=list)


class ImportParseError(BaseModel):
    record_index: int | None = None
    iteration_key: str | None = None
    error_code: str
    message: str
    raw_payload: Any | None = None


class ParseResult(BaseModel):
    detected_format: str
    parser_version: str
    streams: list[NormalizedStream] = Field(default_factory=list)
    errors: list[ImportParseError] = Field(default_factory=list)


class SourceParser(Protocol):
    parser_version: str
    detected_format: str

    def can_parse(self, payload: object) -> bool: ...

    def parse(self, payload: object) -> ParseResult: ...
