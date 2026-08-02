from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.aquarium_parameter_threshold_repository import AquariumParameterThresholdRepository
from src.aquarium_repository import AquariumRepository
from src.auth import get_current_user
from src.db import get_session
from src.models import AquariumParameterThreshold
from src.parameter_repository import ParameterRepository
from src.responses import success_response
from src.schemas.aquarium_parameter_thresholds import SetThresholdRequest, ThresholdResponse
from src.services.parameter_rules import PARAMETER_RULES, normalize_parameter
from src.user_service import AuthenticatedUser


def _validate_threshold_values(parameter: str, payload: SetThresholdRequest) -> None:
    low, high = PARAMETER_RULES[parameter].canonical_range
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


def _empty_payload(aquarium_id: uuid.UUID, parameter: str) -> dict[str, str | float | None]:
    return {
        "aquarium_id": str(aquarium_id),
        "parameter": parameter,
        "target": None,
        "min": None,
        "max": None,
        "unit": PARAMETER_RULES[parameter].canonical_unit,
    }


def _to_payload(
    threshold: AquariumParameterThreshold, parameter_slug: str
) -> dict[str, str | float | None]:
    return {
        "aquarium_id": str(threshold.aquarium_id),
        "parameter": parameter_slug,
        "target": threshold.target,
        "min": threshold.min,
        "max": threshold.max,
        "unit": threshold.unit,
    }


def build_aquarium_parameter_threshold_router() -> APIRouter:
    router = APIRouter(prefix="/aquariums", tags=["aquarium-parameter-thresholds"])

    @router.put("/{aquarium_id}/thresholds/{parameter}", response_model=ThresholdResponse)
    async def set_threshold(
        aquarium_id: uuid.UUID,
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

        parameter_repo = ParameterRepository(session)
        normalized_parameter = normalize_parameter(parameter, parameter_repo)
        _validate_threshold_values(normalized_parameter.slug, payload)

        threshold_repo = AquariumParameterThresholdRepository(session)
        threshold = threshold_repo.upsert(
            aquarium_id=aquarium.id,
            owner_user_id=current_user.user.id,
            parameter_id=normalized_parameter.id,
            target=payload.target,
            min=payload.min,
            max=payload.max,
            unit=PARAMETER_RULES[normalized_parameter.slug].canonical_unit,
        )

        return success_response(
            _to_payload(threshold, normalized_parameter.slug), request_id=request_id
        )

    @router.get("/{aquarium_id}/thresholds/{parameter}", response_model=ThresholdResponse)
    async def get_threshold(
        aquarium_id: uuid.UUID,
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

        parameter_repo = ParameterRepository(session)
        normalized_parameter = normalize_parameter(parameter, parameter_repo)
        threshold_repo = AquariumParameterThresholdRepository(session)
        threshold = threshold_repo.get_by_aquarium_and_parameter(
            aquarium_id=aquarium.id,
            owner_user_id=current_user.user.id,
            parameter_id=normalized_parameter.id,
        )
        if threshold is None:
            return success_response(
                _empty_payload(aquarium.id, normalized_parameter.slug), request_id=request_id
            )

        return success_response(
            _to_payload(threshold, normalized_parameter.slug), request_id=request_id
        )

    return router
