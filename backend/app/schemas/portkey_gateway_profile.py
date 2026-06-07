from datetime import datetime
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

RoutingMode = Literal["provider_slug", "config_id"]


class PortkeyGatewayProfileCreate(BaseModel):
    profile_name: str = Field(min_length=1, max_length=255)
    gateway_base_url: AnyHttpUrl
    portkey_api_key: SecretStr = Field(min_length=1)
    routing_mode: RoutingMode
    provider_slug: str | None = Field(default=None, max_length=255)
    config_id: str | None = Field(default=None, max_length=255)
    judge_model: str = Field(min_length=1, max_length=255)
    temperature: float = Field(default=0.0, ge=0, le=2)
    legacy_virtual_key: SecretStr | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    metadata_tags: dict[str, str] = Field(default_factory=dict)

    @field_validator("profile_name", "provider_slug", "config_id", "judge_model", mode="before")
    @classmethod
    def strip_optional_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def routing_target_must_match_mode(self) -> "PortkeyGatewayProfileCreate":
        if self.routing_mode == "provider_slug":
            if not self.provider_slug:
                raise ValueError("provider_slug is required when routing_mode is provider_slug.")
            if self.config_id:
                raise ValueError("config_id must be omitted when routing_mode is provider_slug.")
        if self.routing_mode == "config_id":
            if not self.config_id:
                raise ValueError("config_id is required when routing_mode is config_id.")
            if self.provider_slug:
                raise ValueError("provider_slug must be omitted when routing_mode is config_id.")
        return self


class PortkeyGatewayProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_name: str
    gateway_base_url: str
    portkey_api_key_masked: str
    routing_mode: str
    provider_slug: str | None
    config_id: str | None
    judge_model: str
    temperature: float
    legacy_virtual_key_masked: str | None
    timeout_seconds: int
    metadata_tags: dict[str, str]
    created_at: datetime
    updated_at: datetime


class PortkeyConnectionTestResult(BaseModel):
    status: Literal["ok", "failed"]
    message: str
    status_code: int | None = None


class PortkeyGatewayProfileUpdate(BaseModel):
    profile_name: str = Field(min_length=1, max_length=255)
    gateway_base_url: AnyHttpUrl
    portkey_api_key: SecretStr | None = None
    routing_mode: RoutingMode
    provider_slug: str | None = Field(default=None, max_length=255)
    config_id: str | None = Field(default=None, max_length=255)
    judge_model: str = Field(min_length=1, max_length=255)
    temperature: float = Field(default=0.0, ge=0, le=2)
    legacy_virtual_key: SecretStr | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    metadata_tags: dict[str, str] = Field(default_factory=dict)

    @field_validator("profile_name", "provider_slug", "config_id", "judge_model", mode="before")
    @classmethod
    def strip_optional_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def routing_target_must_match_mode(self) -> "PortkeyGatewayProfileUpdate":
        if self.routing_mode == "provider_slug":
            if not self.provider_slug:
                raise ValueError("provider_slug is required when routing_mode is provider_slug.")
            if self.config_id:
                raise ValueError("config_id must be omitted when routing_mode is provider_slug.")
        if self.routing_mode == "config_id":
            if not self.config_id:
                raise ValueError("config_id is required when routing_mode is config_id.")
            if self.provider_slug:
                raise ValueError("provider_slug must be omitted when routing_mode is config_id.")
        return self
