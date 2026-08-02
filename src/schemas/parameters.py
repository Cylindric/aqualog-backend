from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ParameterPayload(BaseModel):
    slug: str
    display_name: str
    description: str | None
    unit: str | None
    created_at: str
    updated_at: str


class ParameterResponse(BaseModel):
    success: bool
    request_id: str
    data: ParameterPayload


class ParameterListResponse(BaseModel):
    success: bool
    request_id: str
    data: list[ParameterPayload]


class ParameterUnitPayload(BaseModel):
    slug: str
    unit: str
    display_name: str
    description: str | None
    is_canonical: bool


class ParameterDetailPayload(BaseModel):
    slug: str
    display_name: str
    description: str | None
    unit: str | None
    units: list[ParameterUnitPayload]
    created_at: str
    updated_at: str


class ParameterDetailResponse(BaseModel):
    success: bool
    request_id: str
    data: ParameterDetailPayload


class DeleteParameterPayload(BaseModel):
    slug: str
    deleted: bool


class DeleteParameterResponse(BaseModel):
    success: bool
    request_id: str
    data: DeleteParameterPayload


def _validate_slug(value: str) -> str:
    trimmed = value.strip().lower()
    if not trimmed:
        raise ValueError("slug must not be empty")
    return trimmed


def _validate_display_name(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("display_name must not be empty")
    return trimmed


class CreateParameterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., min_length=1, max_length=32)
    display_name: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        return _validate_slug(value)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        return _validate_display_name(value)


class UpdateParameterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_display_name(value)
