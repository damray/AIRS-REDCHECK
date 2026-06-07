from app.parsers.static_json import StaticJsonParser


def test_static_parser_accepts_single_object() -> None:
    result = StaticJsonParser().parse({"prompt": "p", "output": "o", "threat": True})

    assert result.detected_format == "static_json"
    assert len(result.streams) == 1
    assert result.streams[0].input_type == "static"
    assert result.streams[0].attempts[0].source_threat_normalized == "THREAT"


def test_static_parser_accepts_array_and_retains_optional_metadata() -> None:
    result = StaticJsonParser().parse(
        [{"prompt": "p", "output": "o", "threat": "safe", "severity": "LOW"}]
    )

    assert result.errors == []
    assert result.streams[0].metadata == {"severity": "LOW"}
    assert result.streams[0].attempts[0].metadata == {"severity": "LOW"}


def test_static_parser_accepts_empty_output_string() -> None:
    result = StaticJsonParser().parse({"prompt": "p", "output": "", "threat": False})

    assert result.errors == []
    assert len(result.streams) == 1
    assert result.streams[0].attempts[0].output == ""


def test_static_parser_keeps_valid_records_when_one_record_fails() -> None:
    result = StaticJsonParser().parse(
        [
            {"prompt": "p", "output": "o", "threat": False},
            {"prompt": "missing output", "threat": True},
        ]
    )

    assert len(result.streams) == 1
    assert len(result.errors) == 1
    assert result.errors[0].record_index == 1
    assert result.errors[0].error_code == "missing_required_fields"


def test_static_parser_reports_malformed_top_level() -> None:
    result = StaticJsonParser().parse("not-json-shape")

    assert result.streams == []
    assert result.errors[0].error_code == "invalid_top_level"
