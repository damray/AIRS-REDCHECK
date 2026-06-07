from app.parsers.agent_json import AgentJsonParser


def test_agent_parser_decodes_iterations_into_attempts() -> None:
    result = AgentJsonParser().parse(
        {
            "goal": "g",
            "stream_id": "s1",
            "stream_threat": False,
            "iteration_2": '{"iteration": 2, "prompt": "p2", "output": "o2", "threat": true}',
            "iteration_1": '{"iteration": 1, "prompt": "p1", "output": "o1", "score": 0}',
        }
    )

    assert result.errors == []
    assert len(result.streams) == 1
    assert [attempt.attempt_index for attempt in result.streams[0].attempts] == [1, 2]
    assert result.streams[0].attempts[0].source_threat_normalized == "SAFE"
    assert result.streams[0].attempts[1].source_threat_normalized == "THREAT"


def test_agent_parser_reports_missing_fields() -> None:
    result = AgentJsonParser().parse({"goal": "g", "iteration_1": "{}"})

    assert result.streams == []
    assert result.errors[0].error_code == "invalid_agent_stream"


def test_agent_parser_reports_malformed_iteration_json_without_dropping_valid_iteration() -> None:
    result = AgentJsonParser().parse(
        {
            "goal": "g",
            "stream_id": "s1",
            "stream_threat": False,
            "iteration_1": '{"prompt": "p1", "output": "o1"}',
            "iteration_2": "{bad json",
        }
    )

    assert len(result.streams) == 1
    assert len(result.streams[0].attempts) == 1
    assert len(result.errors) == 1
    assert result.errors[0].iteration_key == "iteration_2"
    assert result.errors[0].error_code == "invalid_iteration_json"


def test_agent_parser_accepts_empty_output_string() -> None:
    result = AgentJsonParser().parse(
        {
            "goal": "g",
            "stream_id": "s1",
            "stream_threat": False,
            "iteration_1": '{"prompt": "p1", "output": "", "threat": false}',
        }
    )

    assert result.errors == []
    assert len(result.streams) == 1
    assert result.streams[0].attempts[0].output == ""


def test_agent_parser_reports_mixed_iteration_validity() -> None:
    result = AgentJsonParser().parse(
        {
            "goal": "g",
            "stream_id": "s1",
            "stream_threat": True,
            "iteration_1": '{"prompt": "p1", "output": "o1"}',
            "iteration_2": '{"prompt": "", "output": "o2"}',
        }
    )

    assert len(result.streams[0].attempts) == 1
    assert result.errors[0].error_code == "invalid_prompt"
