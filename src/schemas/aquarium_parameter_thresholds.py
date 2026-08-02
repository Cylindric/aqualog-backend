from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class SetThresholdRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: float | None = None
    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def validate_ordering(self) -> SetThresholdRequest:
        if self.min is not None and self.target is not None and self.min > self.target:
            raise ValueError("min must be less than or equal to target")
        if self.target is not None and self.max is not None and self.target > self.max:
            raise ValueError("target must be less than or equal to max")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must be less than or equal to max")
        return self


class ThresholdPayload(BaseModel):
    aquarium_id: str
    parameter: str
    target: float | None
    min: float | None
    max: float | None
    unit: str


class ThresholdResponse(BaseModel):
    success: bool
    request_id: str
    data: ThresholdPayload
