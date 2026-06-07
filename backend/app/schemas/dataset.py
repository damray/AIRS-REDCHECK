from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str | None
    source_filename: str | None
    source_content_type: str
    mapping_profile_id: str | None
    detected_format: str
    parser_version: str
    import_status: str
    stream_count: int
    attempt_count: int
    error_count: int
    created_at: datetime
    updated_at: datetime


class StreamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    external_stream_id: str | None
    input_type: str
    goal: str | None
    stream_threat_raw: str | None
    stream_threat_normalized: str | None


class AttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    stream_id: str
    attempt_index: int
    source_prompt: str
    source_output: str
    source_threat_raw: str
    source_threat_normalized: str | None
    source_score_raw: object | None
    source_reasoning: str | None
