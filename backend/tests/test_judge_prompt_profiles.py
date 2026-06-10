from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import JudgePromptProfile
from app.services.judge.prompt_profiles import prompt_hash


def test_prompt_profile_can_be_created_viewed_and_updated(
    client: TestClient, db_session: Session
) -> None:
    create = client.post(
        "/judge-prompt-profiles",
        json={
            "name": "strict judge",
            "system_prompt": "System v1",
            "rubric": "Rubric v1",
            "is_default": True,
        },
    )

    assert create.status_code == 201
    body = create.json()
    assert body["prompt_hash"] == prompt_hash("System v1", "Rubric v1")
    assert body["is_default"] is True

    update = client.put(
        f"/judge-prompt-profiles/{body['id']}",
        json={
            "name": "strict judge",
            "system_prompt": "System v2",
            "rubric": "Rubric v2",
            "is_default": True,
        },
    )

    assert update.status_code == 200
    updated = update.json()
    assert updated["system_prompt"] == "System v2"
    assert updated["rubric"] == "Rubric v2"
    assert updated["prompt_hash"] == prompt_hash("System v2", "Rubric v2")
    profile = db_session.get(JudgePromptProfile, body["id"])
    assert profile is not None
    assert profile.prompt_hash == updated["prompt_hash"]


def test_prompt_profile_list_creates_default_profile(client: TestClient) -> None:
    response = client.get("/judge-prompt-profiles")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["is_default"] is True
    assert "response_verdict" in body[0]["system_prompt"]
    assert "SAFE_REFUSAL" in body[0]["system_prompt"]
    assert "evidence_excerpt" in body[0]["system_prompt"]
    assert body[0]["rubric"]
    assert len(body[0]["prompt_hash"]) == 64
