import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import JudgePromptProfile
from app.services.judge.rubric import DEFAULT_RESPONSE_RUBRIC, DEFAULT_SYSTEM_PROMPT


def prompt_hash(system_prompt: str, rubric: str) -> str:
    payload = f"{system_prompt}\n---rubric---\n{rubric}".encode()
    return hashlib.sha256(payload).hexdigest()


def ensure_default_prompt_profile(session: Session) -> JudgePromptProfile:
    profile = session.execute(
        select(JudgePromptProfile)
        .where(JudgePromptProfile.is_default.is_(True))
        .order_by(JudgePromptProfile.created_at, JudgePromptProfile.id)
        .limit(1)
    ).scalar_one_or_none()
    if profile is not None:
        return profile

    profile = JudgePromptProfile(
        name="Default safety Judge",
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        rubric=DEFAULT_RESPONSE_RUBRIC,
        prompt_hash=prompt_hash(DEFAULT_SYSTEM_PROMPT, DEFAULT_RESPONSE_RUBRIC),
        is_default=True,
    )
    session.add(profile)
    session.flush()
    return profile
