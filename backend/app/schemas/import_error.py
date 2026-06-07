from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportErrorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    stream_id: str | None
    record_index: int | None
    iteration_key: str | None
    error_code: str
    message: str
    raw_payload: object | None
    created_at: datetime
