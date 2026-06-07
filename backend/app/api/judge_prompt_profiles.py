from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import JudgePromptProfile
from app.schemas.judge_prompt_profile import JudgePromptProfileCreate, JudgePromptProfileRead
from app.services.judge.prompt_profiles import ensure_default_prompt_profile, prompt_hash

router = APIRouter(prefix="/judge-prompt-profiles", tags=["judge-prompt-profiles"])


@router.post("", response_model=JudgePromptProfileRead, status_code=status.HTTP_201_CREATED)
def create_judge_prompt_profile(
    profile: JudgePromptProfileCreate,
    db: Annotated[Session, Depends(get_db)],
) -> JudgePromptProfile:
    prompt_profile = JudgePromptProfile(
        name=profile.name,
        system_prompt=profile.system_prompt,
        rubric=profile.rubric,
        prompt_hash=prompt_hash(profile.system_prompt, profile.rubric),
        is_default=profile.is_default,
    )
    db.add(prompt_profile)
    if profile.is_default:
        _clear_other_defaults(db, except_profile=prompt_profile)
    db.commit()
    db.refresh(prompt_profile)
    return prompt_profile


@router.get("", response_model=list[JudgePromptProfileRead])
def list_judge_prompt_profiles(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[JudgePromptProfile]:
    ensure_default_prompt_profile(db)
    db.commit()
    return list(
        db.execute(
            select(JudgePromptProfile)
            .order_by(JudgePromptProfile.is_default.desc(), JudgePromptProfile.created_at)
            .limit(limit)
            .offset(offset)
        ).scalars()
    )


@router.get("/{profile_id}", response_model=JudgePromptProfileRead)
def get_judge_prompt_profile(
    profile_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> JudgePromptProfile:
    return _get_prompt_profile(db, profile_id)


@router.put("/{profile_id}", response_model=JudgePromptProfileRead)
def update_judge_prompt_profile(
    profile_id: str,
    profile: JudgePromptProfileCreate,
    db: Annotated[Session, Depends(get_db)],
) -> JudgePromptProfile:
    prompt_profile = _get_prompt_profile(db, profile_id)
    prompt_profile.name = profile.name
    prompt_profile.system_prompt = profile.system_prompt
    prompt_profile.rubric = profile.rubric
    prompt_profile.prompt_hash = prompt_hash(profile.system_prompt, profile.rubric)
    prompt_profile.is_default = profile.is_default
    if profile.is_default:
        _clear_other_defaults(db, except_profile=prompt_profile)
    db.commit()
    db.refresh(prompt_profile)
    return prompt_profile


@router.post("/{profile_id}/make-default", response_model=JudgePromptProfileRead)
def make_default_prompt_profile(
    profile_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> JudgePromptProfile:
    prompt_profile = _get_prompt_profile(db, profile_id)
    prompt_profile.is_default = True
    _clear_other_defaults(db, except_profile=prompt_profile)
    db.commit()
    db.refresh(prompt_profile)
    return prompt_profile


def _get_prompt_profile(db: Session, profile_id: str) -> JudgePromptProfile:
    profile = db.get(JudgePromptProfile, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Judge prompt profile not found.",
        )
    return profile


def _clear_other_defaults(db: Session, *, except_profile: JudgePromptProfile) -> None:
    for profile in db.execute(select(JudgePromptProfile)).scalars():
        if profile is not except_profile and profile.id != except_profile.id:
            profile.is_default = False
