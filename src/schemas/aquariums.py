from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

SUPPORTED_VOLUME_UNITS = {"L", "gal_us"}


class VolumeInput(BaseModel):
    value: float = Field(..., gt=0)
    unit: str

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        if value not in SUPPORTED_VOLUME_UNITS:
            raise ValueError("Volume unit must be one of: L, gal_us")
        return value


class AquariumPayload(BaseModel):
    id: str
    name: str
    type: str
    volume_liters: float
    created_at: str
    updated_at: str


class AquariumResponse(BaseModel):
    success: bool
    request_id: str
    data: AquariumPayload


class AquariumListResponse(BaseModel):
    success: bool
    request_id: str
    data: list[AquariumPayload]


class DeleteAquariumPayload(BaseModel):
    id: str
    deleted: bool


class DeleteAquariumResponse(BaseModel):
    success: bool
    request_id: str
    data: DeleteAquariumPayload


class CreateAquariumRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)
    type: str
    volume: VolumeInput

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Name must not be empty")
        return trimmed

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 3 or len(trimmed) > 24:
            raise ValueError("Type length must be between 3 and 24 characters")
        return trimmed


class UpdateAquariumRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: str | None = None
    volume: VolumeInput | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Name must not be empty")
        return trimmed

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if len(trimmed) < 3 or len(trimmed) > 24:
            raise ValueError("Type length must be between 3 and 24 characters")
        return trimmed
