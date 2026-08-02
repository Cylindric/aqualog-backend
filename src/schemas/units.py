from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UnitPayload(BaseModel):
    slug: str
    unit: str
    display_name: str
    description: str | None
    created_at: str
    updated_at: str


class UnitResponse(BaseModel):
    success: bool
    request_id: str
    data: UnitPayload


class UnitListResponse(BaseModel):
    success: bool
    request_id: str
    data: list[UnitPayload]


class DeleteUnitPayload(BaseModel):
    slug: str
    deleted: bool


class DeleteUnitResponse(BaseModel):
    success: bool
    request_id: str
    data: DeleteUnitPayload


def _validate_unit(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("unit must not be empty")
    return trimmed


def _validate_display_name(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("display_name must not be empty")
    return trimmed


class CreateUnitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit: str = Field(..., min_length=1, max_length=16)
    display_name: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        return _validate_unit(value)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        return _validate_display_name(value)


class UpdateUnitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_display_name(value)
