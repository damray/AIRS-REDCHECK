from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JudgePromptProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    system_prompt: str = Field(min_length=1)
    rubric: str = Field(min_length=1)
    is_default: bool = False


class JudgePromptProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    system_prompt: str
    rubric: str
    prompt_hash: str
    is_default: bool
    created_at: datetime
    updated_at: datetime
