from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from src.aquarium_measurement_repository import (
    AquariumMeasurementRepository,
    DuplicateAquariumMeasurementError,
)
from src.aquarium_repository import AquariumRepository
from src.auth import get_current_user
from src.db import get_session
from src.models import AquariumMeasurement
from src.responses import success_response
from src.user_service import AuthenticatedUser

SUPPORTED_SALINITY_UNITS = {"ppt", "sg"}
SUPPORTED_PHOSPHATE_UNITS = {"ppm"}
SALINITY_PARAMETER = "salinity"
PHOSPHATE_PARAMETER = "phosphate"
SUPPORTED_PARAMETERS = {SALINITY_PARAMETER, PHOSPHATE_PARAMETER}
SG_TO_PPT_FACTOR = 1325.76 # conversion factor valid at a typical reef aquarium temperature of 25°C
MAX_SALINITY_PPT = 100.0
MIN_SALINITY_SG = 1.0
MAX_SALINITY_SG = 1.04
MAX_PHOSPHATE_PPM = 100.0


class CreateSalinityMeasurementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit: str
    value: float
    measured_at: datetime

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_SALINITY_UNITS:
            raise ValueError("Salinity unit must be one of: ppt, sg")
        return normalized

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: float, info) -> float:
        unit = (info.data.get("unit") or "").lower()
        if value <= 0:
            raise ValueError("Salinity value must be greater than 0")
        if unit == "ppt" and value > MAX_SALINITY_PPT:
            raise ValueError("Salinity value in ppt must be less than or equal to 100")
        if unit == "sg" and not (MIN_SALINITY_SG <= value <= MAX_SALINITY_SG):
            raise ValueError("Salinity value in sg must be between 1.0 and 1.04")
        return value

    @field_validator("measured_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("measured_at must include timezone information")
        return value


class CreateMeasurementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit: str
    value: float
    measured_at: datetime

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        normalized = value.strip().lower()
        return normalized

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


def _to_ppt(value: float, unit: str) -> float:
    if unit == "ppt":
        return value
    return (value - 1.0) * SG_TO_PPT_FACTOR


def _normalize_timestamp(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _canonicalize_measurement(parameter: str, value: float, unit: str) -> tuple[float, str]:
    if parameter == SALINITY_PARAMETER:
        return _to_ppt(value, unit), "ppt"
    return value, "ppm"


def _validate_measurement_payload(parameter: str, value: float, unit: str) -> None:
    if parameter == SALINITY_PARAMETER:
        if unit not in SUPPORTED_SALINITY_UNITS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Salinity unit must be one of: ppt, sg",
            )
        if unit == "ppt" and value > MAX_SALINITY_PPT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Salinity value in ppt must be less than or equal to 100",
            )
        if unit == "sg" and not (MIN_SALINITY_SG <= value <= MAX_SALINITY_SG):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Salinity value in sg must be between 1.0 and 1.04",
            )
        return

    if unit not in SUPPORTED_PHOSPHATE_UNITS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Phosphate unit must be: ppm",
        )
    if value > MAX_PHOSPHATE_PPM:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Phosphate value in ppm must be less than or equal to 100",
        )


def _normalize_parameter(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_PARAMETERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Parameter must be one of: salinity, phosphate",
        )
    return normalized


def _to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _to_payload(measurement: AquariumMeasurement) -> dict[str, str | float]:
    return {
        "id": measurement.id,
        "aquarium_id": measurement.aquarium_id,
        "parameter": measurement.parameter,
        "value": measurement.value,
        "unit": measurement.unit,
        "raw_value": measurement.raw_value,
        "raw_unit": measurement.raw_unit,
        "measured_at": _to_utc_iso(measurement.measured_at),
        "created_at": _to_utc_iso(measurement.created_at),
    }


def build_aquarium_measurement_router() -> APIRouter:
    router = APIRouter(prefix="/aquariums", tags=["aquarium-measurements"])

    @router.post(
        "/{aquarium_id}/measurements/{parameter}",
        response_model=MeasurementResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_measurement(
        aquarium_id: str,
        parameter: str,
        request: Request,
        payload: CreateMeasurementRequest = Body(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        aquarium_repo = AquariumRepository(session)
        aquarium = aquarium_repo.get_by_id_and_owner(aquarium_id, current_user.user.id)
        if aquarium is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aquarium not found")

        normalized_parameter = _normalize_parameter(parameter)
        _validate_measurement_payload(normalized_parameter, payload.value, payload.unit)

        measurement_repo = AquariumMeasurementRepository(session)
        normalized_measured_at = _normalize_timestamp(payload.measured_at)
        canonical_value, canonical_unit = _canonicalize_measurement(
            normalized_parameter,
            payload.value,
            payload.unit,
        )

        try:
            measurement = measurement_repo.create_measurement(
                aquarium_id=aquarium.id,
                owner_user_id=current_user.user.id,
                parameter=normalized_parameter,
                value=canonical_value,
                unit=canonical_unit,
                raw_value=payload.value,
                raw_unit=payload.unit,
                measured_at=normalized_measured_at,
            )
        except DuplicateAquariumMeasurementError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate {normalized_parameter} reading timestamp for aquarium",
            ) from exc

        return success_response(_to_payload(measurement), request_id=request_id, status_code=status.HTTP_201_CREATED)

    @router.get("/{aquarium_id}/measurements/{parameter}", response_model=MeasurementListResponse)
    async def list_measurements(
        aquarium_id: str,
        parameter: str,
        request: Request,
        measured_from: datetime | None = Query(default=None, alias="from"),
        measured_to: datetime | None = Query(default=None, alias="to"),
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        aquarium_repo = AquariumRepository(session)
        aquarium = aquarium_repo.get_by_id_and_owner(aquarium_id, current_user.user.id)
        if aquarium is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aquarium not found")

        normalized_parameter = _normalize_parameter(parameter)

        measurement_repo = AquariumMeasurementRepository(session)
        if measured_from is not None:
            measured_from = _normalize_timestamp(measured_from)
        if measured_to is not None:
            measured_to = _normalize_timestamp(measured_to)

        measurements = measurement_repo.list_measurements(
            aquarium_id=aquarium.id,
            owner_user_id=current_user.user.id,
            measured_from=measured_from,
            measured_to=measured_to,
            parameter=normalized_parameter,
        )
        return success_response([_to_payload(item) for item in measurements], request_id=request_id)

    @router.delete("/{aquarium_id}/measurements/{parameter}/{id}")
    async def delete_measurement(
        aquarium_id: str,
        parameter: str,
        id: str,
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
        measurement_repo = AquariumMeasurementRepository(session)
        deleted = measurement_repo.delete_measurement(
            aquarium_id=aquarium.id,
            parameter=normalized_parameter,
            measurement_id=id,
        )
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measurement not found")

        return success_response({"id": id, "deleted": True}, request_id=request_id)

    return router
