from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import MappingProfile
from app.schemas.mapping_profile import MappingProfileCreate, MappingProfileRead

router = APIRouter(prefix="/mapping-profiles", tags=["mapping-profiles"])


@router.post("", response_model=MappingProfileRead, status_code=status.HTTP_201_CREATED)
def create_mapping_profile(
    profile: MappingProfileCreate,
    db: Annotated[Session, Depends(get_db)],
) -> MappingProfile:
    mapping_profile = MappingProfile(
        name=profile.name,
        prompt_column=profile.prompt_column,
        output_column=profile.output_column,
        source_threat_column=profile.source_threat_column,
        optional_field_columns=profile.optional_field_columns,
    )
    db.add(mapping_profile)
    db.commit()
    db.refresh(mapping_profile)
    return mapping_profile


@router.get("", response_model=list[MappingProfileRead])
def list_mapping_profiles(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MappingProfile]:
    return list(
        db.execute(
            select(MappingProfile)
            .order_by(MappingProfile.created_at, MappingProfile.id)
            .limit(limit)
            .offset(offset)
        ).scalars()
    )


@router.get("/{profile_id}", response_model=MappingProfileRead)
def get_mapping_profile(profile_id: str, db: Annotated[Session, Depends(get_db)]) -> MappingProfile:
    mapping_profile = db.get(MappingProfile, profile_id)
    if mapping_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping profile not found.",
        )
    return mapping_profile
