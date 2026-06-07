from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import PortkeyGatewayProfile
from app.schemas.portkey_gateway_profile import (
    PortkeyConnectionTestResult,
    PortkeyGatewayProfileCreate,
    PortkeyGatewayProfileRead,
    PortkeyGatewayProfileUpdate,
)
from app.services.portkey_gateway import PortkeyGatewayService, profile_to_read_dict

router = APIRouter(prefix="/portkey-gateway-profiles", tags=["portkey-gateway-profiles"])


@router.post("", response_model=PortkeyGatewayProfileRead, status_code=status.HTTP_201_CREATED)
def create_portkey_gateway_profile(
    profile: PortkeyGatewayProfileCreate,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    gateway_profile = PortkeyGatewayProfile(
        profile_name=profile.profile_name,
        gateway_base_url=str(profile.gateway_base_url).rstrip("/"),
        portkey_api_key=profile.portkey_api_key.get_secret_value(),
        routing_mode=profile.routing_mode,
        provider_slug=profile.provider_slug,
        config_id=profile.config_id,
        judge_model=profile.judge_model,
        temperature=profile.temperature,
        legacy_virtual_key=(
            profile.legacy_virtual_key.get_secret_value()
            if profile.legacy_virtual_key is not None
            else None
        ),
        timeout_seconds=profile.timeout_seconds,
        metadata_tags=profile.metadata_tags,
    )
    db.add(gateway_profile)
    db.commit()
    db.refresh(gateway_profile)
    return profile_to_read_dict(gateway_profile)


@router.get("", response_model=list[PortkeyGatewayProfileRead])
def list_portkey_gateway_profiles(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict[str, object]]:
    profiles = db.execute(
        select(PortkeyGatewayProfile)
        .order_by(PortkeyGatewayProfile.created_at, PortkeyGatewayProfile.id)
        .limit(limit)
        .offset(offset)
    ).scalars()
    return [profile_to_read_dict(profile) for profile in profiles]


@router.get("/{profile_id}", response_model=PortkeyGatewayProfileRead)
def get_portkey_gateway_profile(
    profile_id: str, db: Annotated[Session, Depends(get_db)]
) -> dict[str, object]:
    return profile_to_read_dict(_get_profile(db, profile_id))


@router.put("/{profile_id}", response_model=PortkeyGatewayProfileRead)
def update_portkey_gateway_profile(
    profile_id: str,
    profile: PortkeyGatewayProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    gateway_profile = _get_profile(db, profile_id)
    gateway_profile.profile_name = profile.profile_name
    gateway_profile.gateway_base_url = str(profile.gateway_base_url).rstrip("/")
    if profile.portkey_api_key is not None:
        gateway_profile.portkey_api_key = profile.portkey_api_key.get_secret_value()
    gateway_profile.routing_mode = profile.routing_mode
    gateway_profile.provider_slug = profile.provider_slug
    gateway_profile.config_id = profile.config_id
    gateway_profile.judge_model = profile.judge_model
    gateway_profile.temperature = profile.temperature
    gateway_profile.legacy_virtual_key = (
        profile.legacy_virtual_key.get_secret_value()
        if profile.legacy_virtual_key is not None
        else gateway_profile.legacy_virtual_key
    )
    gateway_profile.timeout_seconds = profile.timeout_seconds
    gateway_profile.metadata_tags = profile.metadata_tags
    db.commit()
    db.refresh(gateway_profile)
    return profile_to_read_dict(gateway_profile)


@router.post("/{profile_id}/test-connection", response_model=PortkeyConnectionTestResult)
def test_portkey_gateway_connection(
    profile_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> PortkeyConnectionTestResult:
    profile = _get_profile(db, profile_id)
    result = PortkeyGatewayService().test_connection(profile)
    return PortkeyConnectionTestResult(
        status=result.status,
        message=result.message,
        status_code=result.status_code,
    )


def _get_profile(db: Session, profile_id: str) -> PortkeyGatewayProfile:
    profile = db.get(PortkeyGatewayProfile, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portkey gateway profile not found.",
        )
    return profile
