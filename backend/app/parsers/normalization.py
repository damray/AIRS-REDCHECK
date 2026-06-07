from typing import Any

STATIC_METADATA_FIELDS = {
    "asr",
    "severity",
    "category",
    "sub_category",
    "goal_category",
    "dasf_v2",
    "nist",
    "owasp",
    "mitre_atlas",
    "multi_turn",
    "generation",
    "turn",
    "multi_turn_prompt",
}

AGENT_ATTEMPT_METADATA_FIELDS = {
    "iteration",
    "techniques",
    "improvement",
    "prompts_objective",
    "summary",
}


def normalize_threat(value: Any) -> str | None:
    if isinstance(value, bool):
        return "THREAT" if value else "SAFE"
    if isinstance(value, int | float):
        if value == 1:
            return "THREAT"
        if value == 0:
            return "SAFE"
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "threat", "harmful", "unsafe", "yes", "1"}:
            return "THREAT"
        if normalized in {"false", "safe", "benign", "no", "0"}:
            return "SAFE"
    return None


def stringify_raw(value: Any) -> str:
    return "" if value is None else str(value)


def select_metadata(record: dict[str, Any], fields: set[str]) -> dict[str, Any]:
    return {key: record[key] for key in fields if key in record}
