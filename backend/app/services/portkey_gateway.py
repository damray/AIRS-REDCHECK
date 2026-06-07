from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.models import PortkeyGatewayProfile


@dataclass(frozen=True)
class PortkeyConnectionResult:
    status: Literal["ok", "failed"]
    message: str
    status_code: int | None = None


def mask_secret(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


class PortkeyGatewayService:
    def test_connection(self, profile: PortkeyGatewayProfile) -> PortkeyConnectionResult:
        url = self._chat_completions_url(profile.gateway_base_url)
        payload = {
            "model": self.resolve_model(profile),
            "messages": [{"role": "user", "content": "connection test"}],
            "max_tokens": 512,
        }
        try:
            with httpx.Client(timeout=profile.timeout_seconds) as client:
                response = client.post(url, headers=self._headers(profile), json=payload)
        except httpx.TimeoutException:
            return PortkeyConnectionResult(
                status="failed",
                message="Connection timed out. Check the gateway URL and timeout.",
            )
        except httpx.ConnectError:
            return PortkeyConnectionResult(
                status="failed",
                message="Could not connect to the gateway URL.",
            )
        except httpx.HTTPError:
            return PortkeyConnectionResult(
                status="failed",
                message="Gateway connection failed before a response was received.",
            )

        if 200 <= response.status_code < 300:
            return PortkeyConnectionResult(
                status="ok",
                message="Gateway connection succeeded.",
                status_code=response.status_code,
            )

        import json as _json
        import logging

        raw_text = response.text[:1000] if response.text else "(empty)"
        logging.getLogger("portkey_gateway").error(
            "Portkey error %s: %s", response.status_code, raw_text
        )
        detail = raw_text
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = _json.dumps(body, indent=2)[:800]
        except Exception:
            pass
        base_message = self._failure_message(response.status_code)
        message = f"{base_message} Detail: {detail}"

        return PortkeyConnectionResult(
            status="failed",
            message=message,
            status_code=response.status_code,
        )

    def _headers(self, profile: PortkeyGatewayProfile) -> dict[str, str]:
        headers = {
            "x-portkey-api-key": profile.portkey_api_key,
            "Content-Type": "application/json",
        }
        if profile.routing_mode == "config_id" and profile.config_id:
            headers["x-portkey-config"] = profile.config_id
        return headers

    def resolve_model(self, profile: PortkeyGatewayProfile) -> str:
        if profile.routing_mode == "provider_slug" and profile.provider_slug:
            slug = profile.provider_slug.lstrip("@")
            return f"@{slug}/{profile.judge_model}"
        return profile.judge_model

    def _chat_completions_url(self, gateway_base_url: str) -> str:
        base = gateway_base_url.rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    def _failure_message(self, status_code: int) -> str:
        if status_code in {401, 403}:
            return "Gateway rejected the credentials or routing configuration."
        if status_code == 404:
            return "Gateway endpoint was not found. Check the base URL."
        if status_code >= 500:
            return "Gateway returned a server error. Retry later or check provider routing."
        return "Gateway returned an unexpected response. Check profile configuration."


def profile_to_read_dict(profile: PortkeyGatewayProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "profile_name": profile.profile_name,
        "gateway_base_url": profile.gateway_base_url,
        "portkey_api_key_masked": mask_secret(profile.portkey_api_key) or "",
        "routing_mode": profile.routing_mode,
        "provider_slug": profile.provider_slug,
        "config_id": profile.config_id,
        "judge_model": profile.judge_model,
        "temperature": profile.temperature,
        "legacy_virtual_key_masked": mask_secret(profile.legacy_virtual_key),
        "timeout_seconds": profile.timeout_seconds,
        "metadata_tags": profile.metadata_tags,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }
