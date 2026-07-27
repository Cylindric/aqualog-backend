from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy.orm import Session

from src.aquarium_measurements import (
    ALKALINITY_PARAMETER,
    AMMONIA_PARAMETER,
    CALCIUM_PARAMETER,
    MAGNESIUM_PARAMETER,
    MAX_ALKALINITY_DKH,
    MAX_AMMONIA_MGL,
    MAX_CALCIUM_PPM,
    MAX_MAGNESIUM_PPM,
    MAX_NITRATE_PPM,
    MAX_NITRITE_PPM,
    MAX_PH,
    MAX_PHOSPHATE_PPM,
    MAX_SALINITY_PPT,
    MAX_TEMPERATURE_CELSIUS,
    MIN_ALKALINITY_DKH,
    MIN_AMMONIA_MGL,
    MIN_CALCIUM_PPM,
    MIN_MAGNESIUM_PPM,
    MIN_NITRATE_PPM,
    MIN_NITRITE_PPM,
    MIN_PH,
    MIN_TEMPERATURE_CELSIUS,
    NITRATE_PARAMETER,
    NITRITE_PARAMETER,
    PH_PARAMETER,
    PHOSPHATE_PARAMETER,
    SALINITY_PARAMETER,
    TEMPERATURE_PARAMETER,
)
from src.aquarium_measurements import SUPPORTED_PARAMETERS as SUPPORTED_THRESHOLD_PARAMETERS
from src.aquarium_parameter_threshold_repository import AquariumParameterThresholdRepository
from src.aquarium_repository import AquariumRepository
from src.auth import get_current_user
from src.db import get_session
from src.models import AquariumParameterThreshold
from src.responses import success_response
from src.user_service import AuthenticatedUser

THRESHOLD_UNITS = {
    SALINITY_PARAMETER: "ppt",
    PHOSPHATE_PARAMETER: "ppm",
    TEMPERATURE_PARAMETER: "celsius",
    CALCIUM_PARAMETER: "ppm",
    AMMONIA_PARAMETER: "mg/L",
    NITRITE_PARAMETER: "ppm",
    NITRATE_PARAMETER: "ppm",
    PH_PARAMETER: "pH",
    ALKALINITY_PARAMETER: "dKH",
    MAGNESIUM_PARAMETER: "ppm",
}

THRESHOLD_SANITY_RANGES = {
    SALINITY_PARAMETER: (0.0, MAX_SALINITY_PPT),
    PHOSPHATE_PARAMETER: (0.0, MAX_PHOSPHATE_PPM),
    TEMPERATURE_PARAMETER: (MIN_TEMPERATURE_CELSIUS, MAX_TEMPERATURE_CELSIUS),
    CALCIUM_PARAMETER: (MIN_CALCIUM_PPM, MAX_CALCIUM_PPM),
    AMMONIA_PARAMETER: (MIN_AMMONIA_MGL, MAX_AMMONIA_MGL),
    NITRITE_PARAMETER: (MIN_NITRITE_PPM, MAX_NITRITE_PPM),
    NITRATE_PARAMETER: (MIN_NITRATE_PPM, MAX_NITRATE_PPM),
    PH_PARAMETER: (MIN_PH, MAX_PH),
    ALKALINITY_PARAMETER: (MIN_ALKALINITY_DKH, MAX_ALKALINITY_DKH),
    MAGNESIUM_PARAMETER: (MIN_MAGNESIUM_PPM, MAX_MAGNESIUM_PPM),
}


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


def _normalize_parameter(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_THRESHOLD_PARAMETERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Parameter must be one of: {', '.join(SUPPORTED_THRESHOLD_PARAMETERS)}",
        )
    return normalized


def _validate_threshold_values(parameter: str, payload: SetThresholdRequest) -> None:
    low, high = THRESHOLD_SANITY_RANGES[parameter]
    for field_name, value in (
        ("target", payload.target),
        ("min", payload.min),
        ("max", payload.max),
    ):
        if value is not None and not (low <= value <= high):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field_name} for {parameter} must be between {low} and {high}",
            )


def _empty_payload(aquarium_id: str, parameter: str) -> dict[str, str | float | None]:
    return {
        "aquarium_id": aquarium_id,
        "parameter": parameter,
        "target": None,
        "min": None,
        "max": None,
        "unit": THRESHOLD_UNITS[parameter],
    }


def _to_payload(threshold: AquariumParameterThreshold) -> dict[str, str | float | None]:
    return {
        "aquarium_id": threshold.aquarium_id,
        "parameter": threshold.parameter,
        "target": threshold.target,
        "min": threshold.min,
        "max": threshold.max,
        "unit": threshold.unit,
    }


def build_aquarium_parameter_threshold_router() -> APIRouter:
    router = APIRouter(prefix="/aquariums", tags=["aquarium-parameter-thresholds"])

    @router.put("/{aquarium_id}/thresholds/{parameter}", response_model=ThresholdResponse)
    async def set_threshold(
        aquarium_id: str,
        parameter: str,
        request: Request,
        payload: SetThresholdRequest = Body(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        aquarium_repo = AquariumRepository(session)
        aquarium = aquarium_repo.get_by_id_and_owner(aquarium_id, current_user.user.id)
        if aquarium is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aquarium not found")

        normalized_parameter = _normalize_parameter(parameter)
        _validate_threshold_values(normalized_parameter, payload)

        threshold_repo = AquariumParameterThresholdRepository(session)
        threshold = threshold_repo.upsert(
            aquarium_id=aquarium.id,
            owner_user_id=current_user.user.id,
            parameter=normalized_parameter,
            target=payload.target,
            min=payload.min,
            max=payload.max,
            unit=THRESHOLD_UNITS[normalized_parameter],
        )

        return success_response(_to_payload(threshold), request_id=request_id)

    @router.get("/{aquarium_id}/thresholds/{parameter}", response_model=ThresholdResponse)
    async def get_threshold(
        aquarium_id: str,
        parameter: str,
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        aquarium_repo = AquariumRepository(session)
        aquarium = aquarium_repo.get_by_id_and_owner(aquarium_id, current_user.user.id)
        if aquarium is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aquarium not found")

        normalized_parameter = _normalize_parameter(parameter)
        threshold_repo = AquariumParameterThresholdRepository(session)
        threshold = threshold_repo.get_by_aquarium_and_parameter(
            aquarium_id=aquarium.id,
            owner_user_id=current_user.user.id,
            parameter=normalized_parameter,
        )
        if threshold is None:
            return success_response(
                _empty_payload(aquarium.id, normalized_parameter), request_id=request_id
            )

        return success_response(_to_payload(threshold), request_id=request_id)

    return router
