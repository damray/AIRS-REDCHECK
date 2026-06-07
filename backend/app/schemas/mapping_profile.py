from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.parsers.normalization import STATIC_METADATA_FIELDS


class MappingProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    prompt_column: str = Field(min_length=1, max_length=255)
    output_column: str = Field(min_length=1, max_length=255)
    source_threat_column: str = Field(min_length=1, max_length=255)
    optional_field_columns: dict[str, str] = Field(default_factory=dict)

    @field_validator("name", "prompt_column", "output_column", "source_threat_column")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value must not be blank.")
        return stripped

    @field_validator("optional_field_columns")
    @classmethod
    def optional_fields_must_be_supported(cls, value: dict[str, str]) -> dict[str, str]:
        unsupported = sorted(set(value) - STATIC_METADATA_FIELDS)
        if unsupported:
            raise ValueError(f"Unsupported optional fields: {', '.join(unsupported)}.")
        return {field: column.strip() for field, column in value.items() if column.strip()}


class MappingProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    prompt_column: str
    output_column: str
    source_threat_column: str
    optional_field_columns: dict[str, str]
    created_at: datetime
    updated_at: datetime
