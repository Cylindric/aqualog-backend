from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
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
from src.models import AquariumMeasurement, Parameter, Unit
from src.parameter_repository import ParameterRepository
from src.responses import success_response
from src.unit_repository import UnitRepository
from src.user_service import AuthenticatedUser

SUPPORTED_SALINITY_UNITS = {"ppt", "sg"}
SUPPORTED_PHOSPHATE_UNITS = {"ppm"}
SUPPORTED_TEMPERATURE_UNITS = {"celsius", "fahrenheit"}
SUPPORTED_CALCIUM_UNITS = {"ppm"}
SUPPORTED_AMMONIA_UNITS = {"mg/l"}
SUPPORTED_NITRITE_UNITS = {"ppm"}
SUPPORTED_NITRATE_UNITS = {"ppm"}
SUPPORTED_PH_UNITS = {"ph"}
SUPPORTED_ALKALINITY_UNITS = {"dkh"}
SUPPORTED_MAGNESIUM_UNITS = {"ppm"}

SALINITY_PARAMETER = "salinity"
PHOSPHATE_PARAMETER = "phosphate"
TEMPERATURE_PARAMETER = "temperature"
CALCIUM_PARAMETER = "calcium"
AMMONIA_PARAMETER = "ammonia"
NITRITE_PARAMETER = "nitrite"
NITRATE_PARAMETER = "nitrate"
PH_PARAMETER = "ph"
ALKALINITY_PARAMETER = "alkalinity"
MAGNESIUM_PARAMETER = "magnesium"

SG_TO_PPT_FACTOR = 1325.76  # conversion factor valid at a typical reef aquarium temperature of 25°C
MAX_SALINITY_PPT = 100.0
MIN_SALINITY_SG = 1.0
MAX_SALINITY_SG = 1.04
MAX_PHOSPHATE_PPM = 100.0
MIN_TEMPERATURE_CELSIUS = 0.0
MAX_TEMPERATURE_CELSIUS = 45.0
MIN_CALCIUM_PPM = 0.0
MAX_CALCIUM_PPM = 1000.0
MIN_AMMONIA_MGL = 0.0
MAX_AMMONIA_MGL = 50.0
MIN_NITRITE_PPM = 0.0
MAX_NITRITE_PPM = 50.0
MIN_NITRATE_PPM = 0.0
MAX_NITRATE_PPM = 500.0
MIN_PH = 0.0
MAX_PH = 14.0
MIN_ALKALINITY_DKH = 0.0
MAX_ALKALINITY_DKH = 30.0
MIN_MAGNESIUM_PPM = 0.0
MAX_MAGNESIUM_PPM = 2000.0


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


def fahrenheit_to_celsius(value: float) -> float:
    return (value - 32.0) * 5.0 / 9.0


def _to_celsius(value: float, unit: str) -> float:
    if unit == "celsius":
        return value
    return fahrenheit_to_celsius(value)


def _identity(value: float, unit: str) -> float:
    return value


def _validate_salinity_value(value: float, unit: str) -> None:
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


def _validate_temperature_value(value: float, unit: str) -> None:
    canonical_value = _to_celsius(value, unit)
    if not (MIN_TEMPERATURE_CELSIUS <= canonical_value <= MAX_TEMPERATURE_CELSIUS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Temperature value must be between 0 and 45 degrees Celsius",
        )


def _range_validator(
    min_value: float, max_value: float, error_detail: str
) -> Callable[[float, str], None]:
    def _validate(value: float, unit: str) -> None:
        if not (min_value <= value <= max_value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=error_detail,
            )

    return _validate


@dataclass(frozen=True)
class ParameterRule:
    supported_units: frozenset[str]
    canonical_unit: str
    canonicalize: Callable[[float, str], float]
    validate_value: Callable[[float, str], None]
    unit_error: str


PARAMETER_RULES: dict[str, ParameterRule] = {
    SALINITY_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_SALINITY_UNITS),
        canonical_unit="ppt",
        canonicalize=_to_ppt,
        validate_value=_validate_salinity_value,
        unit_error="Salinity unit must be one of: ppt, sg",
    ),
    TEMPERATURE_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_TEMPERATURE_UNITS),
        canonical_unit="celsius",
        canonicalize=_to_celsius,
        validate_value=_validate_temperature_value,
        unit_error="Temperature unit must be one of: celsius, fahrenheit",
    ),
    PHOSPHATE_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_PHOSPHATE_UNITS),
        canonical_unit="ppm",
        canonicalize=_identity,
        validate_value=_range_validator(
            0.0, MAX_PHOSPHATE_PPM, "Phosphate value in ppm must be less than or equal to 100"
        ),
        unit_error="Phosphate unit must be: ppm",
    ),
    CALCIUM_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_CALCIUM_UNITS),
        canonical_unit="ppm",
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_CALCIUM_PPM,
            MAX_CALCIUM_PPM,
            f"Calcium value in ppm must be between {MIN_CALCIUM_PPM} and {MAX_CALCIUM_PPM}",
        ),
        unit_error="Calcium unit must be: ppm",
    ),
    AMMONIA_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_AMMONIA_UNITS),
        canonical_unit="mg/L",
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_AMMONIA_MGL,
            MAX_AMMONIA_MGL,
            f"Ammonia value in mg/L must be between {MIN_AMMONIA_MGL} and {MAX_AMMONIA_MGL}",
        ),
        unit_error="Ammonia unit must be: mg/L",
    ),
    NITRITE_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_NITRITE_UNITS),
        canonical_unit="ppm",
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_NITRITE_PPM,
            MAX_NITRITE_PPM,
            f"Nitrite value in ppm must be between {MIN_NITRITE_PPM} and {MAX_NITRITE_PPM}",
        ),
        unit_error="Nitrite unit must be: ppm",
    ),
    NITRATE_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_NITRATE_UNITS),
        canonical_unit="ppm",
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_NITRATE_PPM,
            MAX_NITRATE_PPM,
            f"Nitrate value in ppm must be between {MIN_NITRATE_PPM} and {MAX_NITRATE_PPM}",
        ),
        unit_error="Nitrate unit must be: ppm",
    ),
    PH_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_PH_UNITS),
        canonical_unit="pH",
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_PH, MAX_PH, f"pH value must be between {MIN_PH} and {MAX_PH}"
        ),
        unit_error="pH unit must be: pH",
    ),
    ALKALINITY_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_ALKALINITY_UNITS),
        canonical_unit="dKH",
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_ALKALINITY_DKH,
            MAX_ALKALINITY_DKH,
            f"Alkalinity value in dKH must be between {MIN_ALKALINITY_DKH} and {MAX_ALKALINITY_DKH}",
        ),
        unit_error="Alkalinity unit must be: dKH",
    ),
    MAGNESIUM_PARAMETER: ParameterRule(
        supported_units=frozenset(SUPPORTED_MAGNESIUM_UNITS),
        canonical_unit="ppm",
        canonicalize=_identity,
        validate_value=_range_validator(
            MIN_MAGNESIUM_PPM,
            MAX_MAGNESIUM_PPM,
            f"Magnesium value in ppm must be between {MIN_MAGNESIUM_PPM} and {MAX_MAGNESIUM_PPM}",
        ),
        unit_error="Magnesium unit must be: ppm",
    ),
}

SUPPORTED_PARAMETERS = frozenset(PARAMETER_RULES.keys())


def _normalize_timestamp(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _canonicalize_measurement(parameter: str, value: float, unit: str) -> tuple[float, str]:
    rule = PARAMETER_RULES[parameter]
    return rule.canonicalize(value, unit), rule.canonical_unit


def _validate_measurement_payload(
    parameter: Parameter, value: float, unit: str, unit_repo: UnitRepository
) -> Unit:
    rule = PARAMETER_RULES[parameter.slug]
    unit_row = unit_repo.get_by_slug(unit)
    if unit_row is None or not unit_repo.is_unit_valid_for_parameter(parameter.id, unit_row.id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=rule.unit_error,
        )
    rule.validate_value(value, unit)
    return unit_row


def _normalize_parameter(value: str, parameter_repo: ParameterRepository) -> Parameter:
    normalized = value.strip().lower()
    parameter = parameter_repo.get_by_slug(normalized)
    if parameter is None or normalized not in PARAMETER_RULES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Parameter must be one of: {', '.join(PARAMETER_RULES)}",
        )
    return parameter


def _to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _to_payload(measurement: AquariumMeasurement, parameter_slug: str) -> dict[str, str | float]:
    return {
        "id": str(measurement.id),
        "aquarium_id": str(measurement.aquarium_id),
        "parameter": parameter_slug,
        "value": measurement.value,
        "unit": measurement.unit.slug,
        "raw_value": measurement.raw_value,
        "raw_unit": measurement.raw_unit.slug,
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
        aquarium_id: uuid.UUID,
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

        parameter_repo = ParameterRepository(session)
        unit_repo = UnitRepository(session)
        normalized_parameter = _normalize_parameter(parameter, parameter_repo)
        raw_unit_row = _validate_measurement_payload(
            normalized_parameter, payload.value, payload.unit, unit_repo
        )

        measurement_repo = AquariumMeasurementRepository(session)
        normalized_measured_at = _normalize_timestamp(payload.measured_at)
        canonical_value, canonical_unit_slug = _canonicalize_measurement(
            normalized_parameter.slug,
            payload.value,
            payload.unit,
        )
        canonical_unit_row = unit_repo.get_by_slug(canonical_unit_slug)
        if canonical_unit_row is None:
            raise RuntimeError(f"Canonical unit '{canonical_unit_slug}' missing from unit catalog")

        try:
            measurement = measurement_repo.create_measurement(
                aquarium_id=aquarium.id,
                owner_user_id=current_user.user.id,
                parameter_id=normalized_parameter.id,
                value=canonical_value,
                unit_id=canonical_unit_row.id,
                raw_value=payload.value,
                raw_unit_id=raw_unit_row.id,
                measured_at=normalized_measured_at,
            )
        except DuplicateAquariumMeasurementError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate {normalized_parameter.slug} reading timestamp for aquarium",
            ) from exc

        return success_response(
            _to_payload(measurement, normalized_parameter.slug),
            request_id=request_id,
            status_code=status.HTTP_201_CREATED,
        )

    @router.get("/{aquarium_id}/measurements/{parameter}", response_model=MeasurementListResponse)
    async def list_measurements(
        aquarium_id: uuid.UUID,
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

        parameter_repo = ParameterRepository(session)
        normalized_parameter = _normalize_parameter(parameter, parameter_repo)

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
            parameter_id=normalized_parameter.id,
        )
        return success_response(
            [_to_payload(item, normalized_parameter.slug) for item in measurements],
            request_id=request_id,
        )

    @router.delete("/{aquarium_id}/measurements/{parameter}/{id}")
    async def delete_measurement(
        aquarium_id: uuid.UUID,
        parameter: str,
        id: uuid.UUID,
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        aquarium_repo = AquariumRepository(session)
        aquarium = aquarium_repo.get_by_id_and_owner(aquarium_id, current_user.user.id)
        if aquarium is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aquarium not found")

        parameter_repo = ParameterRepository(session)
        normalized_parameter = _normalize_parameter(parameter, parameter_repo)
        measurement_repo = AquariumMeasurementRepository(session)
        deleted = measurement_repo.delete_measurement(
            aquarium_id=aquarium.id,
            parameter_id=normalized_parameter.id,
            measurement_id=id,
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Measurement not found"
            )

        return success_response({"id": str(id), "deleted": True}, request_id=request_id)

    return router
