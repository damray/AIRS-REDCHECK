import json
from typing import Any

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import Attempt, Dataset, EvaluationError, PortkeyGatewayProfile, Stream
from app.services.judge.blind import build_blind_judge_request
from app.services.judge.persistence import EvaluationErrorRepository
from app.services.judge.portkey_adapter import JUDGE_RESPONSE_JSON_SCHEMA, PortkeyJudgeAdapter
from app.services.judge.schemas import EvaluationErrorCreate, JudgeAdapterError, JudgeResult


def _attempt_graph() -> tuple[Dataset, Stream, Attempt]:
    dataset = Dataset(
        source_content_type="application/json",
        detected_format="static_json",
        parser_version="static-json-v1",
        raw_payload=[{"prompt": "p", "output": "o", "threat": True}],
        import_status="imported",
        stream_count=1,
        attempt_count=1,
        error_count=0,
    )
    stream = Stream(
        dataset=dataset,
        input_type="static",
        goal="agent goal",
        raw_payload={"prompt": "p", "output": "o", "threat": True},
        stream_metadata={},
    )
    attempt = Attempt(
        dataset=dataset,
        stream=stream,
        attempt_index=0,
        source_prompt="user prompt",
        source_output="model output",
        source_threat_raw="True",
        source_threat_normalized="THREAT",
        source_score_raw=0.99,
        source_reasoning="source evaluator reasoning",
        raw_payload={"prompt": "user prompt", "output": "model output", "threat": True},
        attempt_metadata={},
    )
    return dataset, stream, attempt


def _profile() -> PortkeyGatewayProfile:
    return PortkeyGatewayProfile(
        profile_name="p",
        gateway_base_url="https://gateway.example.test",
        portkey_api_key="pk-test-secret-value",
        routing_mode="provider_slug",
        provider_slug="openai",
        config_id=None,
        judge_model="gpt-test",
        legacy_virtual_key=None,
        timeout_seconds=5,
        metadata_tags={},
    )


def _gateway_response(content: dict[str, Any]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(content),
                    }
                }
            ]
        },
    )


def test_blind_judge_request_excludes_source_verdict_score_and_reasoning() -> None:
    _, _, attempt = _attempt_graph()

    request = build_blind_judge_request(attempt, goal="stream goal", rubric="rubric")
    dumped = request.model_dump()
    serialized = request.model_dump_json()

    assert dumped == {
        "system_prompt": request.system_prompt,
        "prompt": "user prompt",
        "output": "model output",
        "rubric": "rubric",
        "goal": "stream goal",
    }
    assert "source_threat" not in serialized
    assert "source_score" not in serialized
    assert "source evaluator reasoning" not in serialized
    assert "THREAT" not in serialized
    assert "0.99" not in serialized


@pytest.mark.parametrize("verdict", ["THREAT", "SAFE", "UNCERTAIN"])
def test_judge_result_schema_supports_required_verdicts(verdict: str) -> None:
    result = JudgeResult.model_validate(
        {
            "response_verdict": verdict,
            "confidence": 0.5,
            "response_behavior": "AMBIGUOUS",
            "risk_category": "SAFETY",
            "explanation": "Reasoned explanation.",
        }
    )

    assert result.response_verdict == verdict


def test_judge_result_schema_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        JudgeResult.model_validate(
            {
                "response_verdict": "SAFE",
                "confidence": 2,
                "response_behavior": "SAFE_REFUSAL",
                "risk_category": "SAFETY",
                "explanation": "Reasoned explanation.",
            }
        )


def test_portkey_judge_adapter_sends_blind_payload_and_parses_structured_response(
    monkeypatch: Any,
) -> None:
    _, _, attempt = _attempt_graph()
    captured: dict[str, Any] = {}

    def fake_post(
        self: httpx.Client,
        url: str,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> httpx.Response:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _gateway_response(
            {
                "response_verdict": "SAFE",
                "confidence": 0.9,
                "response_behavior": "SAFE_REFUSAL",
                "risk_category": "SAFETY",
                "explanation": "The model refused.",
                "evidence_excerpt": "I cannot help.",
            }
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    request = build_blind_judge_request(attempt, goal="stream goal", rubric="rubric")

    response = PortkeyJudgeAdapter().evaluate(_profile(), request)

    assert response.result.response_verdict == "SAFE"
    assert captured["url"] == "https://gateway.example.test/v1/chat/completions"
    assert captured["headers"]["x-portkey-api-key"] == "pk-test-secret-value"
    assert captured["json"]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "airs_redcheck_judge_result",
            "strict": True,
            "schema": JUDGE_RESPONSE_JSON_SCHEMA,
        },
    }
    assert "JudgeResult schema" in captured["json"]["messages"][0]["content"]
    request_content = captured["json"]["messages"][1]["content"]
    assert "user prompt" in request_content
    assert "model output" in request_content
    assert "stream goal" in request_content
    assert "rubric" in request_content
    assert "required_response_schema" in request_content
    assert "response_verdict" in request_content
    assert "response_behavior" in request_content
    assert "source_threat" not in request_content
    assert "source_score" not in request_content
    assert "source evaluator reasoning" not in request_content


def test_portkey_judge_adapter_rejects_invalid_structured_response(monkeypatch: Any) -> None:
    def fake_post(
        self: httpx.Client,
        url: str,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> httpx.Response:
        return _gateway_response(
            {
                "response_verdict": "MAYBE",
                "confidence": 0.5,
                "response_behavior": "AMBIGUOUS",
                "risk_category": "SAFETY",
                "explanation": "Invalid verdict.",
            }
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    with pytest.raises(JudgeAdapterError) as exc_info:
        PortkeyJudgeAdapter().evaluate(
            _profile(),
            build_blind_judge_request(_attempt_graph()[2]),
        )

    assert exc_info.value.error_code == "invalid_judge_response"
    assert exc_info.value.raw_response is not None


def test_invalid_judge_response_can_be_stored_as_evaluation_error(db_session: Session) -> None:
    dataset, stream, attempt = _attempt_graph()
    profile = _profile()
    db_session.add(dataset)
    db_session.add(stream)
    db_session.add(attempt)
    db_session.add(profile)
    db_session.commit()

    error = EvaluationErrorRepository(db_session).create(
        EvaluationErrorCreate(
            dataset_id=dataset.id,
            stream_id=stream.id,
            attempt_id=attempt.id,
            portkey_gateway_profile_id=profile.id,
            error_code="invalid_judge_response",
            message="Judge returned invalid output.",
            raw_response={"bad": "payload"},
        )
    )

    persisted = db_session.get(EvaluationError, error.id)
    assert persisted is not None
    assert persisted.attempt_id == attempt.id
    assert persisted.portkey_gateway_profile_id == profile.id
    assert persisted.error_code == "invalid_judge_response"
    assert persisted.raw_response == {"bad": "payload"}
