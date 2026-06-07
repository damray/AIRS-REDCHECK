from app.parsers.flat_mapping import FlatMappingConfig, FlatMappingParser


def test_flat_mapping_parser_maps_required_columns() -> None:
    parser = FlatMappingParser(
        FlatMappingConfig(
            prompt_column="user_prompt",
            output_column="model_reply",
            source_threat_column="source_flag",
        )
    )

    result = parser.parse([{"user_prompt": "p", "model_reply": "o", "source_flag": "unsafe"}])

    assert result.errors == []
    assert result.detected_format == "flat_mapping"
    assert result.streams[0].input_type == "static"
    assert result.streams[0].attempts[0].prompt == "p"
    assert result.streams[0].attempts[0].source_threat_normalized == "THREAT"


def test_flat_mapping_parser_maps_optional_fields() -> None:
    parser = FlatMappingParser(
        FlatMappingConfig(
            prompt_column="p",
            output_column="o",
            source_threat_column="t",
            optional_field_columns={"severity": "risk_level", "category": "domain"},
        )
    )

    result = parser.parse(
        [{"p": "prompt", "o": "output", "t": "safe", "risk_level": "LOW", "domain": "SAFETY"}]
    )

    assert result.errors == []
    assert result.streams[0].metadata == {"severity": "LOW", "category": "SAFETY"}
    assert result.streams[0].attempts[0].metadata == {
        "severity": "LOW",
        "category": "SAFETY",
    }


def test_flat_mapping_parser_accepts_empty_output_string() -> None:
    parser = FlatMappingParser(
        FlatMappingConfig(
            prompt_column="p",
            output_column="o",
            source_threat_column="t",
        )
    )

    result = parser.parse([{"p": "prompt", "o": "", "t": "false"}])

    assert result.errors == []
    assert len(result.streams) == 1
    assert result.streams[0].attempts[0].output == ""


def test_flat_mapping_parser_preserves_valid_records_when_mapped_record_fails() -> None:
    parser = FlatMappingParser(
        FlatMappingConfig(
            prompt_column="p",
            output_column="o",
            source_threat_column="t",
        )
    )

    result = parser.parse(
        [
            {"p": "prompt", "o": "output", "t": "true"},
            {"p": "missing output", "t": "false"},
        ]
    )

    assert len(result.streams) == 1
    assert len(result.errors) == 1
    assert result.errors[0].record_index == 1
    assert result.errors[0].error_code == "missing_mapped_columns"
