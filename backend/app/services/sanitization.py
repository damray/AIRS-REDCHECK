from typing import Any

NUL_REPLACEMENT = "\ufffd"


def sanitize_text_for_postgres(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace("\x00", NUL_REPLACEMENT)


def sanitize_json_for_postgres(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text_for_postgres(value)
    if isinstance(value, list):
        return [sanitize_json_for_postgres(item) for item in value]
    if isinstance(value, dict):
        return {
            sanitize_text_for_postgres(str(key)): sanitize_json_for_postgres(item)
            for key, item in value.items()
        }
    return value
