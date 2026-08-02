from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from src.aquarium_measurement_repository import (
    AquariumMeasurementRepository,
    DuplicateAquariumMeasurementError,
)
from src.aquarium_repository import AquariumRepository
from src.auth import get_current_user
from src.db import get_session
from src.models import AquariumMeasurement
from src.parameter_repository import ParameterRepository
from src.responses import success_response
from src.schemas.aquarium_measurements import (
    CreateMeasurementRequest,
    MeasurementListResponse,
    MeasurementResponse,
)
from src.services.parameter_rules import (
    canonicalize_measurement,
    normalize_parameter,
    validate_measurement_payload,
)
from src.unit_repository import UnitRepository
from src.user_service import AuthenticatedUser


def _normalize_timestamp(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(microsecond=0)


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
        "unit": measurement.unit.unit,
        "raw_value": measurement.raw_value,
        "raw_unit": measurement.raw_unit.unit,
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
        normalized_parameter = normalize_parameter(parameter, parameter_repo)
        raw_unit_row = validate_measurement_payload(
            normalized_parameter, payload.value, payload.unit, unit_repo
        )

        measurement_repo = AquariumMeasurementRepository(session)
        normalized_measured_at = _normalize_timestamp(payload.measured_at)
        canonical_value, canonical_unit_notation = canonicalize_measurement(
            normalized_parameter.slug,
            payload.value,
            payload.unit,
        )
        canonical_unit_row = unit_repo.get_by_unit(canonical_unit_notation)
        if canonical_unit_row is None:
            raise RuntimeError(
                f"Canonical unit '{canonical_unit_notation}' missing from unit catalog"
            )

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
        normalized_parameter = normalize_parameter(parameter, parameter_repo)

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
        normalized_parameter = normalize_parameter(parameter, parameter_repo)
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
