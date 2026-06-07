from typing import Any

from app.parsers.base import ImportParseError, NormalizedAttempt, NormalizedStream, ParseResult
from app.parsers.normalization import (
    STATIC_METADATA_FIELDS,
    normalize_threat,
    select_metadata,
    stringify_raw,
)


class StaticJsonParser:
    parser_version = "static-json-v1"
    detected_format = "static_json"
    required_fields = {"prompt", "output", "threat"}

    def can_parse(self, payload: object) -> bool:
        records = self._records(payload)
        return any(
            isinstance(record, dict) and self.required_fields <= record.keys() for record in records
        )

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
                        message="Static JSON import must be an object or an array of objects.",
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
                        message="Record must be a JSON object.",
                        raw_payload=record,
                    )
                )
                continue

            missing = sorted(self.required_fields - record.keys())
            if missing:
                errors.append(
                    ImportParseError(
                        record_index=index,
                        error_code="missing_required_fields",
                        message=f"Missing required fields: {', '.join(missing)}.",
                        raw_payload=record,
                    )
                )
                continue

            prompt = record.get("prompt")
            output = record.get("output")
            if not isinstance(prompt, str) or not prompt.strip():
                errors.append(
                    ImportParseError(
                        record_index=index,
                        error_code="invalid_prompt",
                        message="prompt must be a non-empty string.",
                        raw_payload=record,
                    )
                )
                continue
            if not isinstance(output, str):
                errors.append(
                    ImportParseError(
                        record_index=index,
                        error_code="invalid_output",
                        message="output must be a string.",
                        raw_payload=record,
                    )
                )
                continue

            metadata = select_metadata(record, STATIC_METADATA_FIELDS)
            threat_raw = stringify_raw(record["threat"])
            attempt = NormalizedAttempt(
                attempt_index=0,
                prompt=prompt,
                output=output,
                source_threat_raw=threat_raw,
                source_threat_normalized=normalize_threat(record["threat"]),
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
