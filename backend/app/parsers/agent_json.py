import json
import re
from typing import Any

from app.parsers.base import ImportParseError, NormalizedAttempt, NormalizedStream, ParseResult
from app.parsers.normalization import (
    AGENT_ATTEMPT_METADATA_FIELDS,
    normalize_threat,
    select_metadata,
    stringify_raw,
)

ITERATION_KEY_RE = re.compile(r"^iteration_(\d+)$")


class AgentJsonParser:
    parser_version = "agent-json-v1"
    detected_format = "agent_json"
    required_fields = {"goal", "stream_id", "stream_threat"}

    def can_parse(self, payload: object) -> bool:
        records = self._records(payload)
        return any(
            isinstance(record, dict)
            and self.required_fields <= record.keys()
            and bool(self._iteration_keys(record))
            for record in records
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
                        message="Agent JSON import must be an object or an array of objects.",
                        raw_payload=payload,
                    )
                ],
            )

        for record_index, record in enumerate(records):
            if not isinstance(record, dict):
                errors.append(
                    ImportParseError(
                        record_index=record_index,
                        error_code="invalid_record_type",
                        message="Record must be a JSON object.",
                        raw_payload=record,
                    )
                )
                continue

            missing = sorted(self.required_fields - record.keys())
            iteration_keys = self._iteration_keys(record)
            if missing or not iteration_keys:
                parts = []
                if missing:
                    parts.append(f"missing required fields: {', '.join(missing)}")
                if not iteration_keys:
                    parts.append("missing iteration_N fields")
                errors.append(
                    ImportParseError(
                        record_index=record_index,
                        error_code="invalid_agent_stream",
                        message="; ".join(parts) + ".",
                        raw_payload=record,
                    )
                )
                continue

            attempts: list[NormalizedAttempt] = []
            for fallback_index, iteration_key in enumerate(iteration_keys):
                raw_iteration = record[iteration_key]
                iteration = self._decode_iteration(raw_iteration)
                if not isinstance(iteration, dict):
                    errors.append(
                        ImportParseError(
                            record_index=record_index,
                            iteration_key=iteration_key,
                            error_code="invalid_iteration_json",
                            message="Iteration value must be a serialized JSON object.",
                            raw_payload=raw_iteration,
                        )
                    )
                    continue

                prompt = iteration.get("prompt")
                output = iteration.get("output")
                threat = iteration.get("threat", record.get("stream_threat"))
                if not isinstance(prompt, str) or not prompt.strip():
                    errors.append(
                        ImportParseError(
                            record_index=record_index,
                            iteration_key=iteration_key,
                            error_code="invalid_prompt",
                            message="iteration prompt must be a non-empty string.",
                            raw_payload=iteration,
                        )
                    )
                    continue
                if not isinstance(output, str):
                    errors.append(
                        ImportParseError(
                            record_index=record_index,
                            iteration_key=iteration_key,
                            error_code="invalid_output",
                            message="iteration output must be a string.",
                            raw_payload=iteration,
                        )
                    )
                    continue

                attempts.append(
                    NormalizedAttempt(
                        attempt_index=self._attempt_index(iteration, fallback_index),
                        prompt=prompt,
                        output=output,
                        source_threat_raw=stringify_raw(threat),
                        source_threat_normalized=normalize_threat(threat),
                        source_score_raw=iteration.get("score"),
                        source_reasoning=(
                            iteration.get("judge_reasoning")
                            if isinstance(iteration.get("judge_reasoning"), str)
                            else None
                        ),
                        raw_payload=iteration,
                        metadata=select_metadata(iteration, AGENT_ATTEMPT_METADATA_FIELDS),
                    )
                )

            if attempts:
                streams.append(
                    NormalizedStream(
                        external_stream_id=stringify_raw(record.get("stream_id")),
                        input_type="agent",
                        goal=stringify_raw(record.get("goal")),
                        stream_threat_raw=stringify_raw(record.get("stream_threat")),
                        stream_threat_normalized=normalize_threat(record.get("stream_threat")),
                        raw_payload=record,
                        metadata={
                            key: value
                            for key, value in record.items()
                            if not ITERATION_KEY_RE.match(key)
                            and key not in {"goal", "stream_id", "stream_threat"}
                        },
                        attempts=sorted(attempts, key=lambda attempt: attempt.attempt_index),
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

    def _iteration_keys(self, record: dict[str, Any]) -> list[str]:
        keys = [key for key in record if ITERATION_KEY_RE.match(key)]
        return sorted(keys, key=lambda key: int(ITERATION_KEY_RE.match(key).group(1)))  # type: ignore[union-attr]

    def _decode_iteration(self, raw_iteration: Any) -> object:
        if isinstance(raw_iteration, str):
            try:
                return json.loads(raw_iteration)
            except json.JSONDecodeError:
                return None
        return raw_iteration

    def _attempt_index(self, iteration: dict[str, Any], fallback_index: int) -> int:
        value = iteration.get("iteration")
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return fallback_index
