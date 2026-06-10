import json
import re
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Dataset
from app.services.sanitization import NUL_REPLACEMENT


def test_import_static_json_returns_summary(client: TestClient) -> None:
    response = client.post(
        "/datasets/import?filename=static.json",
        content=json.dumps([{"prompt": "p", "output": "o", "threat": True}]),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["detected_format"] == "static_json"
    assert body["stream_count"] == 1
    assert body["attempt_count"] == 1
    assert body["imported_count"] == 1
    assert body["error_count"] == 0
    assert body["project_id"]
    assert body["scan_name"]


def test_import_static_json_accepts_empty_output_string(client: TestClient) -> None:
    response = client.post(
        "/datasets/import?filename=empty-output.json",
        content=json.dumps(
            [
                {
                    "asr": None,
                    "nist": "['AI 600-1 2.9']",
                    "turn": 0,
                    "owasp": "['LLM01:2025']",
                    "output": "",
                    "prompt": "The Python code below needs improvement.",
                    "threat": False,
                    "dasf_v2": "['DASF V2.0 - 9.1']",
                    "category": "SECURITY",
                    "severity": "HIGH",
                    "generation": 0,
                    "multi_turn": False,
                    "mitre_atlas": "['AML.T0051', 'AML.T0048']",
                    "sub_category": "PROMPT_INJECTION",
                    "goal_category": "Illegal, Crime",
                    "multi_turn_prompt": "",
                }
            ]
        ),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["attempt_count"] == 1
    assert body["imported_count"] == 1
    assert body["error_count"] == 0

    attempts = client.get(f"/datasets/{body['dataset_id']}/attempts")
    assert attempts.status_code == 200
    assert attempts.json()[0]["source_output"] == ""


def test_import_static_json_sanitizes_nul_bytes_for_postgres_text(client: TestClient) -> None:
    response = client.post(
        "/datasets/import?filename=nul-output.json",
        content=json.dumps(
            [{"prompt": "prompt\x00text", "output": "output\x00text", "threat": False}]
        ),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 201
    body = response.json()
    attempts = client.get(f"/datasets/{body['dataset_id']}/attempts")

    assert attempts.status_code == 200
    stored_attempt = attempts.json()[0]
    assert stored_attempt["source_prompt"] == f"prompt{NUL_REPLACEMENT}text"
    assert stored_attempt["source_output"] == f"output{NUL_REPLACEMENT}text"


def test_list_datasets_returns_imported_datasets(client: TestClient) -> None:
    imported = client.post(
        "/datasets/import?filename=static.json",
        content=json.dumps([{"prompt": "p", "output": "o", "threat": False}]),
        headers={"Content-Type": "application/json"},
    )
    assert imported.status_code == 201

    response = client.get("/datasets")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == imported.json()["dataset_id"]
    assert body[0]["project_id"] == imported.json()["project_id"]
    assert body[0]["scan_name"] == imported.json()["scan_name"]
    assert body[0]["attempt_count"] == 1


def test_import_can_create_project_and_attach_to_existing(client: TestClient) -> None:
    first = client.post(
        "/datasets/import",
        params={
            "filename": "first.json",
            "project_name": "Customer A",
            "scan_name": "Initial scan",
        },
        content=json.dumps([{"prompt": "p1", "output": "o1", "threat": False}]),
        headers={"Content-Type": "application/json"},
    )
    assert first.status_code == 201
    project_id = first.json()["project_id"]
    assert first.json()["scan_name"] == "Initial scan"

    second = client.post(
        "/datasets/import",
        params={
            "filename": "second.json",
            "project_id": project_id,
            "scan_name": "Follow-up scan",
        },
        content=json.dumps([{"prompt": "p2", "output": "o2", "threat": True}]),
        headers={"Content-Type": "application/json"},
    )

    assert second.status_code == 201
    assert second.json()["project_id"] == project_id
    projects = client.get("/projects").json()
    assert len(projects) == 1
    assert projects[0]["name"] == "Customer A"
    assert projects[0]["import_count"] == 2


def test_import_without_names_creates_filename_timestamp_defaults(client: TestClient) -> None:
    response = client.post(
        "/datasets/import?filename=customer-scan.json",
        content=json.dumps([{"prompt": "p", "output": "o", "threat": False}]),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 201
    body = response.json()
    assert re.match(r"customer-scan scan \d{8}-\d{6}", body["scan_name"])
    project = client.get(f"/projects/{body['project_id']}").json()
    assert re.match(r"customer-scan project \d{8}-\d{6}", project["name"])


def test_scan_rename_preserves_raw_payload(client: TestClient, db_session: Session) -> None:
    payload = [{"prompt": "raw prompt", "output": "raw output", "threat": False}]
    imported = client.post(
        "/datasets/import?filename=static.json&scan_name=Original",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert imported.status_code == 201
    dataset_id = imported.json()["dataset_id"]

    renamed = client.put(f"/datasets/{dataset_id}", json={"scan_name": "Renamed scan"})

    assert renamed.status_code == 200
    assert renamed.json()["scan_name"] == "Renamed scan"
    dataset = client.get(f"/datasets/{dataset_id}")
    assert dataset.status_code == 200
    assert dataset.json()["scan_name"] == "Renamed scan"
    persisted = db_session.get(Dataset, dataset_id)
    assert persisted is not None
    assert persisted.raw_payload == payload


def test_reset_imported_datasets_clears_dashboard_counts(client: TestClient) -> None:
    imported = client.post(
        "/datasets/import?filename=static.json",
        content=json.dumps([{"prompt": "p", "output": "o", "threat": False}]),
        headers={"Content-Type": "application/json"},
    )
    assert imported.status_code == 201
    assert client.get("/results/triage-summary").json()["total_attempts"] == 1

    response = client.delete("/datasets")

    assert response.status_code == 200
    assert response.json() == {"deleted_datasets": 1, "deleted_attempts": 1}
    assert client.get("/datasets").json() == []
    summary = client.get("/results/triage-summary").json()
    assert summary["total_streams"] == 0
    assert summary["total_attempts"] == 0
    assert summary["processed_attempts"] == 0
    assert summary["remaining_attempts"] == 0


def test_import_agent_json_returns_summary(client: TestClient) -> None:
    payload = [
        {
            "goal": "g",
            "stream_id": "s",
            "stream_threat": False,
            "iteration_1": '{"prompt": "p", "output": "o", "threat": false}',
        }
    ]

    response = client.post(
        "/datasets/import",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 201
    assert response.json()["detected_format"] == "agent_json"
    assert response.json()["attempt_count"] == 1


def test_import_partial_failure_errors_can_be_listed(client: TestClient) -> None:
    content = Path("../fixtures/static-partial-failure.json").read_text()

    response = client.post(
        "/datasets/import",
        content=content,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "imported_with_errors"
    assert body["error_count"] == 1

    errors = client.get(f"/datasets/{body['dataset_id']}/import-errors")
    assert errors.status_code == 200
    assert errors.json()[0]["error_code"] == "missing_required_fields"


def test_import_errors_can_be_project_scoped(client: TestClient) -> None:
    content = Path("../fixtures/static-partial-failure.json").read_text()
    imported = client.post(
        "/datasets/import",
        params={"project_name": "Scoped errors"},
        content=content,
        headers={"Content-Type": "application/json"},
    )
    other = client.post(
        "/datasets/import",
        params={"project_name": "Other"},
        content=json.dumps([{"prompt": "p", "output": "o", "threat": False}]),
        headers={"Content-Type": "application/json"},
    )
    assert imported.status_code == 201
    assert other.status_code == 201

    ok = client.get(
        f"/datasets/{imported.json()['dataset_id']}/import-errors",
        params={"project_id": imported.json()["project_id"]},
    )
    wrong_project = client.get(
        f"/datasets/{imported.json()['dataset_id']}/import-errors",
        params={"project_id": other.json()["project_id"]},
    )

    assert ok.status_code == 200
    assert len(ok.json()) == 1
    assert wrong_project.status_code == 404


def test_import_static_csv(client: TestClient) -> None:
    response = client.post(
        "/datasets/import",
        content="prompt,output,threat\np,o,true\n",
        headers={"Content-Type": "text/csv"},
    )

    assert response.status_code == 201
    assert response.json()["detected_format"] == "static_csv"


def test_import_flat_json_with_inline_mapping(client: TestClient) -> None:
    payload = [
        {
            "input_text": "p",
            "completion_text": "o",
            "source_label": "unsafe",
            "risk": "HIGH",
        }
    ]

    response = client.post(
        "/datasets/import",
        params={
            "prompt_column": "input_text",
            "output_column": "completion_text",
            "source_threat_column": "source_label",
            "optional_field_columns": json.dumps({"severity": "risk"}),
        },
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["detected_format"] == "flat_mapping_json"
    assert body["stream_count"] == 1
    assert body["attempt_count"] == 1

    attempts = client.get(f"/datasets/{body['dataset_id']}/attempts")
    assert attempts.status_code == 200
    assert attempts.json()[0]["source_threat_normalized"] == "THREAT"


def test_import_flat_csv_with_saved_mapping_profile(client: TestClient) -> None:
    profile = client.post(
        "/mapping-profiles",
        json={
            "name": "Custom CSV",
            "prompt_column": "input_text",
            "output_column": "completion_text",
            "source_threat_column": "source_label",
            "optional_field_columns": {"category": "domain"},
        },
    )
    assert profile.status_code == 201

    response = client.post(
        "/datasets/import",
        params={"mapping_profile_id": profile.json()["id"]},
        content="input_text,completion_text,source_label,domain\np,o,false,SAFETY\n",
        headers={"Content-Type": "text/csv"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["detected_format"] == "flat_mapping_csv"
    assert body["stream_count"] == 1
    assert body["attempt_count"] == 1

    dataset = client.get(f"/datasets/{body['dataset_id']}")
    assert dataset.status_code == 200
    assert dataset.json()["mapping_profile_id"] == profile.json()["id"]


def test_mapping_profiles_can_be_listed_and_read(client: TestClient) -> None:
    created = client.post(
        "/mapping-profiles",
        json={
            "name": "Reusable profile",
            "prompt_column": "p",
            "output_column": "o",
            "source_threat_column": "t",
        },
    )

    assert created.status_code == 201
    profile_id = created.json()["id"]

    listed = client.get("/mapping-profiles")
    assert listed.status_code == 200
    assert [profile["id"] for profile in listed.json()] == [profile_id]

    read = client.get(f"/mapping-profiles/{profile_id}")
    assert read.status_code == 200
    assert read.json()["name"] == "Reusable profile"


def test_import_flat_mapping_partial_failure_errors_can_be_listed(client: TestClient) -> None:
    response = client.post(
        "/datasets/import",
        params={
            "prompt_column": "p",
            "output_column": "o",
            "source_threat_column": "t",
        },
        content=json.dumps(
            [{"p": "prompt", "o": "output", "t": "true"}, {"p": "bad", "t": "false"}]
        ),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "imported_with_errors"
    assert body["attempt_count"] == 1
    assert body["error_count"] == 1

    errors = client.get(f"/datasets/{body['dataset_id']}/import-errors")
    assert errors.status_code == 200
    assert errors.json()[0]["error_code"] == "missing_mapped_columns"


def test_import_rejects_too_large_upload(client: TestClient, monkeypatch: Any) -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "2")
    try:
        response = client.post(
            "/datasets/import",
            content='{"prompt": "p", "output": "o", "threat": true}',
            headers={"Content-Type": "application/json"},
        )
    finally:
        get_settings.cache_clear()
        monkeypatch.delenv("MAX_UPLOAD_BYTES", raising=False)

    assert response.status_code == 413
