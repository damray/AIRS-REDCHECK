import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import Attempt, Dataset, ImportErrorRecord, MappingProfile, Stream
from app.parsers.csv_loader import load_csv_payload
from app.parsers.detection import detect_parser
from app.parsers.flat_mapping import FlatMappingConfig, FlatMappingParser
from app.services.sanitization import sanitize_json_for_postgres, sanitize_text_for_postgres


@dataclass(frozen=True)
class ImportRequest:
    content: bytes
    content_type: str
    name: str | None = None
    filename: str | None = None
    mapping_profile_id: str | None = None
    flat_mapping: FlatMappingConfig | None = None


class ImportServiceError(Exception):
    pass


class ImportService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def import_dataset(self, request: ImportRequest) -> Dataset:
        payload = sanitize_json_for_postgres(
            self._load_payload(request.content, request.content_type)
        )
        mapping = self._resolve_mapping(request)
        parser = FlatMappingParser(mapping) if mapping is not None else detect_parser(payload)
        if parser is None:
            raise ImportServiceError("Unsupported import format.")

        result = parser.parse(payload)
        if result.detected_format == FlatMappingParser.detected_format:
            detected_format = self._mapped_detected_format(request.content_type)
        elif request.content_type.startswith("text/csv"):
            detected_format = result.detected_format.replace("_json", "_csv")
        else:
            detected_format = result.detected_format

        status = self._status(stream_count=len(result.streams), error_count=len(result.errors))
        dataset = Dataset(
            name=request.name,
            source_filename=request.filename,
            source_content_type=request.content_type,
            mapping_profile_id=request.mapping_profile_id,
            detected_format=detected_format,
            parser_version=result.parser_version,
            raw_payload=sanitize_json_for_postgres(payload),
            import_status=status,
            stream_count=len(result.streams),
            attempt_count=sum(len(stream.attempts) for stream in result.streams),
            error_count=len(result.errors),
        )
        self.session.add(dataset)
        self.session.flush()

        for normalized_stream in result.streams:
            stream = Stream(
                dataset_id=dataset.id,
                external_stream_id=sanitize_text_for_postgres(normalized_stream.external_stream_id),
                input_type=normalized_stream.input_type,
                goal=sanitize_text_for_postgres(normalized_stream.goal),
                stream_threat_raw=sanitize_text_for_postgres(normalized_stream.stream_threat_raw),
                stream_threat_normalized=sanitize_text_for_postgres(
                    normalized_stream.stream_threat_normalized
                ),
                raw_payload=sanitize_json_for_postgres(normalized_stream.raw_payload),
                stream_metadata=sanitize_json_for_postgres(normalized_stream.metadata),
            )
            self.session.add(stream)
            self.session.flush()

            for normalized_attempt in normalized_stream.attempts:
                self.session.add(
                    Attempt(
                        dataset_id=dataset.id,
                        stream_id=stream.id,
                        attempt_index=normalized_attempt.attempt_index,
                        source_prompt=sanitize_text_for_postgres(normalized_attempt.prompt) or "",
                        source_output=sanitize_text_for_postgres(normalized_attempt.output) or "",
                        source_threat_raw=sanitize_text_for_postgres(
                            normalized_attempt.source_threat_raw
                        )
                        or "",
                        source_threat_normalized=sanitize_text_for_postgres(
                            normalized_attempt.source_threat_normalized
                        ),
                        source_score_raw=sanitize_json_for_postgres(
                            normalized_attempt.source_score_raw
                        ),
                        source_reasoning=sanitize_text_for_postgres(
                            normalized_attempt.source_reasoning
                        ),
                        raw_payload=sanitize_json_for_postgres(normalized_attempt.raw_payload),
                        attempt_metadata=sanitize_json_for_postgres(normalized_attempt.metadata),
                    )
                )

        for error in result.errors:
            self.session.add(
                ImportErrorRecord(
                    dataset_id=dataset.id,
                    record_index=error.record_index,
                    iteration_key=sanitize_text_for_postgres(error.iteration_key),
                    error_code=sanitize_text_for_postgres(error.error_code) or "",
                    message=sanitize_text_for_postgres(error.message) or "",
                    raw_payload=sanitize_json_for_postgres(error.raw_payload),
                )
            )

        self.session.commit()
        self.session.refresh(dataset)
        return dataset

    def _load_payload(self, content: bytes, content_type: str) -> Any:
        normalized_content_type = content_type.split(";")[0].strip().lower()
        if normalized_content_type in {"application/json", "application/octet-stream"}:
            try:
                return json.loads(content.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ImportServiceError("Malformed JSON upload.") from exc
        if normalized_content_type in {"text/csv", "application/csv"}:
            try:
                return load_csv_payload(content)
            except UnicodeDecodeError as exc:
                raise ImportServiceError("Malformed CSV upload.") from exc
        raise ImportServiceError(f"Unsupported content type: {content_type}.")

    def _status(self, stream_count: int, error_count: int) -> str:
        if stream_count == 0:
            return "failed"
        if error_count:
            return "imported_with_errors"
        return "imported"

    def _resolve_mapping(self, request: ImportRequest) -> FlatMappingConfig | None:
        if request.flat_mapping is not None and request.mapping_profile_id is not None:
            raise ImportServiceError(
                "Use either inline mapping columns or mapping_profile_id, not both."
            )
        if request.flat_mapping is not None:
            return request.flat_mapping
        if request.mapping_profile_id is None:
            return None

        mapping_profile = self.session.get(MappingProfile, request.mapping_profile_id)
        if mapping_profile is None:
            raise ImportServiceError("Mapping profile not found.")
        try:
            return FlatMappingConfig(
                prompt_column=mapping_profile.prompt_column,
                output_column=mapping_profile.output_column,
                source_threat_column=mapping_profile.source_threat_column,
                optional_field_columns={
                    str(field): str(column)
                    for field, column in mapping_profile.optional_field_columns.items()
                },
            )
        except ValidationError as exc:
            raise ImportServiceError("Stored mapping profile is invalid.") from exc

    def _mapped_detected_format(self, content_type: str) -> str:
        normalized_content_type = content_type.split(";")[0].strip().lower()
        if normalized_content_type in {"text/csv", "application/csv"}:
            return "flat_mapping_csv"
        return "flat_mapping_json"
