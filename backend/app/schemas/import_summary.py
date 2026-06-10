from pydantic import BaseModel


class ImportSummary(BaseModel):
    dataset_id: str
    project_id: str
    scan_name: str
    detected_format: str
    stream_count: int
    attempt_count: int
    imported_count: int
    error_count: int
    status: str
