import json
from typing import Any, cast

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Dataset, EvaluationJob, PortkeyGatewayProfile


def _import_dataset(client: TestClient, project_name: str) -> dict[str, Any]:
    response = client.post(
        "/datasets/import",
        params={"filename": f"{project_name}.json", "project_name": project_name},
        content=json.dumps([{"prompt": "p", "output": "o", "threat": False}]),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def test_project_list_rename_and_archive_hide_default_views(
    client: TestClient, db_session: Session
) -> None:
    imported = _import_dataset(client, "Customer A")
    project_id = str(imported["project_id"])
    dataset_id = str(imported["dataset_id"])
    raw_payload = db_session.get(Dataset, dataset_id).raw_payload  # type: ignore[union-attr]

    listed = client.get("/projects")
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "Customer A"
    assert listed.json()[0]["import_count"] == 1
    assert listed.json()[0]["latest_activity_at"] is not None

    renamed = client.put(f"/projects/{project_id}", json={"name": "Customer A renamed"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Customer A renamed"

    archived = client.delete(f"/projects/{project_id}")
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True
    assert client.get("/projects").json() == []
    assert client.get("/datasets").json() == []
    assert client.get("/results/triage-summary").json()["total_attempts"] == 0
    assert client.get("/results/export/normalized.csv").text.count("\n") == 1
    persisted = db_session.get(Dataset, dataset_id)
    assert persisted is not None
    assert persisted.raw_payload == raw_payload


def test_project_archive_blocks_running_evaluation_jobs(
    client: TestClient, db_session: Session
) -> None:
    imported = _import_dataset(client, "Blocked")
    project_id = str(imported["project_id"])
    dataset_id = str(imported["dataset_id"])
    profile = PortkeyGatewayProfile(
        profile_name="test profile",
        gateway_base_url="https://example.test/v1/chat/completions",
        portkey_api_key="pk-test-value",
        routing_mode="direct",
        judge_model="judge-model",
    )
    db_session.add(profile)
    db_session.flush()
    db_session.add(
        EvaluationJob(
            dataset_id=dataset_id,
            portkey_gateway_profile_id=profile.id,
            status="RUNNING",
            retry_limit=0,
            total_attempts=1,
            processed_attempts=0,
            succeeded_attempts=0,
            failed_attempts=0,
        )
    )
    db_session.commit()

    response = client.delete(f"/projects/{project_id}")

    assert response.status_code == 409
    assert "running evaluation jobs" in response.json()["detail"]
