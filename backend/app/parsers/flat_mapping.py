from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.parsers.base import ImportParseError, NormalizedAttempt, NormalizedStream, ParseResult
from app.parsers.normalization import STATIC_METADATA_FIELDS, normalize_threat, stringify_raw


class FlatMappingConfig(BaseModel):
    prompt_column: str
    output_column: str
    source_threat_column: str
    optional_field_columns: dict[str, str] = Field(default_factory=dict)

    @field_validator("prompt_column", "output_column", "source_threat_column")
    @classmethod
    def required_column_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Column names must not be blank.")
        return value

    @field_validator("optional_field_columns")
    @classmethod
    def optional_fields_must_be_supported(cls, value: dict[str, str]) -> dict[str, str]:
        unsupported = sorted(set(value) - STATIC_METADATA_FIELDS)
        if unsupported:
            raise ValueError(f"Unsupported optional fields: {', '.join(unsupported)}.")
        blank_columns = sorted(field for field, column in value.items() if not column.strip())
        if blank_columns:
            raise ValueError(
                f"Optional field mappings must not use blank columns: {', '.join(blank_columns)}."
            )
        return value


class FlatMappingParser:
    parser_version = "flat-mapping-v1"
    detected_format = "flat_mapping"

    def __init__(self, mapping: FlatMappingConfig) -> None:
        self.mapping = mapping

    def parse(self, payload: object) -> ParseResult:
        records = self._records(payload)
        streams: list[NormalizedStream] = []
        errors: list[ImportParseError] = []

        if not records:
            return ParseResult(
                detected_format=self.detected_format,
                parser_version=self.parser_version,
                errors=[
                    ImportParseError(
                        error_code="invalid_top_level",
                        message="Mapped flat import must be an object or an array of objects.",
                        raw_payload=payload,
                    )
                ],
            )

        for index, record in enumerate(records):
            if not isinstance(record, dict):
                errors.append(
                    ImportParseError(
                        record_index=index,
                        error_code="invalid_record_type",
                        message="Record must be a flat object.",
                        raw_payload=record,
                    )
                )
                continue

            missing = self._missing_required_columns(record)
            if missing:
                errors.append(
                    ImportParseError(
                        record_index=index,
                        error_code="missing_mapped_columns",
                        message=f"Missing mapped columns: {', '.join(missing)}.",
                        raw_payload=record,
                    )
                )
                continue

            prompt = record[self.mapping.prompt_column]
            output = record[self.mapping.output_column]
            threat = record[self.mapping.source_threat_column]
            if not isinstance(prompt, str) or not prompt.strip():
                errors.append(
                    ImportParseError(
                        record_index=index,
                        error_code="invalid_prompt",
                        message="Mapped prompt must be a non-empty string.",
                        raw_payload=record,
                    )
                )
                continue
            if not isinstance(output, str):
                errors.append(
                    ImportParseError(
                        record_index=index,
                        error_code="invalid_output",
                        message="Mapped output must be a string.",
                        raw_payload=record,
                    )
                )
                continue

            metadata = self._metadata(record)
            attempt = NormalizedAttempt(
                attempt_index=0,
                prompt=prompt,
                output=output,
                source_threat_raw=stringify_raw(threat),
                source_threat_normalized=normalize_threat(threat),
                raw_payload=record,
                metadata=metadata,
            )
            streams.append(
                NormalizedStream(
                    input_type="static",
                    raw_payload=record,
                    metadata=metadata,
                    attempts=[attempt],
                )
            )

        return ParseResult(
            detected_format=self.detected_format,
            parser_version=self.parser_version,
            streams=streams,
            errors=errors,
        )

    def _records(self, payload: object) -> list[Any]:
        if isinstance(payload, dict):
            return [payload]
        if isinstance(payload, list):
            return payload
        return []

    def _missing_required_columns(self, record: dict[str, Any]) -> list[str]:
        return [
            column
            for column in (
                self.mapping.prompt_column,
                self.mapping.output_column,
                self.mapping.source_threat_column,
            )
            if column not in record
        ]

    def _metadata(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            field: record[column]
            for field, column in self.mapping.optional_field_columns.items()
            if column in record
        }
