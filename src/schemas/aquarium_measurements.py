from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class CreateMeasurementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit: str
    value: float
    measured_at: datetime

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Measurement value must be greater than 0")
        return value

    @field_validator("measured_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("measured_at must include timezone information")
        return value


class MeasurementPayload(BaseModel):
    id: str
    aquarium_id: str
    parameter: str
    value: float
    unit: str
    raw_value: float
    raw_unit: str
    measured_at: str
    created_at: str


class MeasurementResponse(BaseModel):
    success: bool
    request_id: str
    data: MeasurementPayload


class MeasurementListResponse(BaseModel):
    success: bool
    request_id: str
    data: list[MeasurementPayload]
