import logging
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import PortkeyGatewayProfile
from app.services.portkey_gateway import PortkeyConnectionResult, PortkeyGatewayService


def _profile_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "profile_name": "Portkey profile",
        "gateway_base_url": "https://gateway.example.test",
        "portkey_api_key": "pk-test-secret-value",
        "routing_mode": "provider_slug",
        "provider_slug": "openai",
        "judge_model": "gpt-test",
        "temperature": 0,
        "legacy_virtual_key": "vk-legacy-secret",
        "timeout_seconds": 5,
        "metadata_tags": {"env": "test"},
    }
    payload.update(overrides)
    return payload


def test_portkey_profile_read_responses_mask_api_keys(
    client: TestClient, db_session: Session
) -> None:
    response = client.post("/portkey-gateway-profiles", json=_profile_payload())

    assert response.status_code == 201
    body = response.json()
    assert "portkey_api_key" not in body
    assert "legacy_virtual_key" not in body
    assert body["portkey_api_key_masked"] == "pk-t...alue"
    assert body["legacy_virtual_key_masked"] == "vk-l...cret"

    profile = db_session.get(PortkeyGatewayProfile, body["id"])
    assert profile is not None
    assert profile.portkey_api_key == "pk-test-secret-value"
    assert profile.legacy_virtual_key == "vk-legacy-secret"

    read = client.get(f"/portkey-gateway-profiles/{body['id']}")
    assert read.status_code == 200
    assert "pk-test-secret-value" not in read.text
    assert "vk-legacy-secret" not in read.text

    listed = client.get("/portkey-gateway-profiles")
    assert listed.status_code == 200
    assert "pk-test-secret-value" not in listed.text
    assert "vk-legacy-secret" not in listed.text


def test_portkey_profile_supports_config_id_routing(client: TestClient) -> None:
    response = client.post(
        "/portkey-gateway-profiles",
        json=_profile_payload(
            routing_mode="config_id",
            provider_slug=None,
            config_id="pc-test-config",
            legacy_virtual_key=None,
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["routing_mode"] == "config_id"
    assert body["config_id"] == "pc-test-config"
    assert body["provider_slug"] is None
    assert body["legacy_virtual_key_masked"] is None


def test_portkey_profile_can_be_updated_without_exposing_or_requiring_secret(
    client: TestClient, db_session: Session
) -> None:
    created = client.post("/portkey-gateway-profiles", json=_profile_payload())

    response = client.put(
        f"/portkey-gateway-profiles/{created.json()['id']}",
        json=_profile_payload(
            profile_name="updated profile",
            portkey_api_key=None,
            judge_model="gpt-updated",
            temperature=0.2,
            timeout_seconds=12,
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile_name"] == "updated profile"
    assert body["judge_model"] == "gpt-updated"
    assert body["temperature"] == 0.2
    assert "portkey_api_key" not in body
    assert "pk-test-secret-value" not in response.text
    profile = db_session.get(PortkeyGatewayProfile, created.json()["id"])
    assert profile is not None
    assert profile.portkey_api_key == "pk-test-secret-value"
    assert profile.temperature == 0.2


def test_portkey_profile_rejects_missing_routing_target(client: TestClient) -> None:
    response = client.post(
        "/portkey-gateway-profiles",
        json=_profile_payload(provider_slug=None),
    )

    assert response.status_code == 422


def test_test_connection_uses_provider_routing_and_returns_success(
    client: TestClient, monkeypatch: Any
) -> None:
    def fake_test_connection(
        self: PortkeyGatewayService, profile: PortkeyGatewayProfile
    ) -> PortkeyConnectionResult:
        assert profile.portkey_api_key == "pk-test-secret-value"
        assert profile.provider_slug == "openai"
        return PortkeyConnectionResult(
            status="ok",
            message="Gateway connection succeeded.",
            status_code=200,
        )

    monkeypatch.setattr(PortkeyGatewayService, "test_connection", fake_test_connection)
    created = client.post("/portkey-gateway-profiles", json=_profile_payload())

    response = client.post(f"/portkey-gateway-profiles/{created.json()['id']}/test-connection")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "message": "Gateway connection succeeded.",
        "status_code": 200,
    }


def test_portkey_service_headers_provider_slug_not_in_headers() -> None:
    profile = PortkeyGatewayProfile(
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

    headers = PortkeyGatewayService()._headers(profile)

    assert headers["x-portkey-api-key"] == "pk-test-secret-value"
    assert "x-portkey-provider" not in headers


def test_portkey_service_resolve_model_with_provider_slug() -> None:
    profile = PortkeyGatewayProfile(
        profile_name="p",
        gateway_base_url="https://gateway.example.test",
        portkey_api_key="pk-test",
        routing_mode="provider_slug",
        provider_slug="vertex",
        config_id=None,
        judge_model="mistralai.mistral-small-2503",
        timeout_seconds=5,
        metadata_tags={},
    )

    model = PortkeyGatewayService().resolve_model(profile)

    assert model == "@vertex/mistralai.mistral-small-2503"


def test_portkey_service_resolve_model_strips_leading_at() -> None:
    profile = PortkeyGatewayProfile(
        profile_name="p",
        gateway_base_url="https://gateway.example.test",
        portkey_api_key="pk-test",
        routing_mode="provider_slug",
        provider_slug="@vertex",
        config_id=None,
        judge_model="gpt-test",
        timeout_seconds=5,
        metadata_tags={},
    )

    model = PortkeyGatewayService().resolve_model(profile)

    assert model == "@vertex/gpt-test"


def test_portkey_service_headers_support_config_id_routing() -> None:
    profile = PortkeyGatewayProfile(
        profile_name="p",
        gateway_base_url="https://gateway.example.test",
        portkey_api_key="pk-test-secret-value",
        routing_mode="config_id",
        provider_slug=None,
        config_id="pc-test-config",
        judge_model="gpt-test",
        legacy_virtual_key=None,
        timeout_seconds=5,
        metadata_tags={},
    )

    headers = PortkeyGatewayService()._headers(profile)

    assert headers["x-portkey-config"] == "pc-test-config"
    assert "x-portkey-provider" not in headers
    assert "x-portkey-virtual-key" not in headers


def test_test_connection_returns_actionable_error_without_secret_leak(
    client: TestClient, monkeypatch: Any, caplog: Any
) -> None:
    def fake_test_connection(
        self: PortkeyGatewayService, profile: PortkeyGatewayProfile
    ) -> PortkeyConnectionResult:
        return PortkeyConnectionResult(
            status="failed",
            message="Gateway rejected the credentials or routing configuration.",
            status_code=401,
        )

    monkeypatch.setattr(PortkeyGatewayService, "test_connection", fake_test_connection)
    created = client.post("/portkey-gateway-profiles", json=_profile_payload())

    with caplog.at_level(logging.INFO):
        response = client.post(f"/portkey-gateway-profiles/{created.json()['id']}/test-connection")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["status_code"] == 401
    assert body["message"] == "Gateway rejected the credentials or routing configuration."
    assert "pk-test-secret-value" not in response.text
    assert "pk-test-secret-value" not in caplog.text


def test_test_connection_timeout_error_is_actionable(client: TestClient, monkeypatch: Any) -> None:
    def fake_test_connection(
        self: PortkeyGatewayService, profile: PortkeyGatewayProfile
    ) -> PortkeyConnectionResult:
        return PortkeyConnectionResult(
            status="failed",
            message="Connection timed out. Check the gateway URL and timeout.",
        )

    monkeypatch.setattr(PortkeyGatewayService, "test_connection", fake_test_connection)
    created = client.post("/portkey-gateway-profiles", json=_profile_payload())

    response = client.post(f"/portkey-gateway-profiles/{created.json()['id']}/test-connection")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["message"] == "Connection timed out. Check the gateway URL and timeout."
    assert "pk-test-secret-value" not in response.text
