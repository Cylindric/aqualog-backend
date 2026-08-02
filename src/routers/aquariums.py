from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.aquarium_repository import AquariumRepository, DuplicateAquariumNameError
from src.auth import get_current_user
from src.db import get_session
from src.models import Aquarium
from src.responses import success_response
from src.schemas.aquariums import (
    AquariumListResponse,
    AquariumResponse,
    CreateAquariumRequest,
    DeleteAquariumResponse,
    UpdateAquariumRequest,
    VolumeInput,
)
from src.user_service import AuthenticatedUser

GALLON_US_TO_LITER = 3.785411784


def _to_liters(volume: VolumeInput) -> float:
    if volume.unit == "L":
        return volume.value
    return volume.value * GALLON_US_TO_LITER


def _to_payload(aquarium: Aquarium) -> dict[str, str | float]:
    return {
        "id": str(aquarium.id),
        "name": aquarium.name,
        "type": aquarium.type,
        "volume_liters": aquarium.volume_liters,
        "created_at": aquarium.created_at.isoformat(),
        "updated_at": aquarium.updated_at.isoformat(),
    }


def _duplicate_name_http_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Aquarium name already exists for this user",
    )


def build_aquarium_router() -> APIRouter:
    router = APIRouter(prefix="/aquariums", tags=["aquariums"])

    @router.get(
        "", response_model=AquariumListResponse, summary="List aquariums for the current user"
    )
    async def list_aquariums(
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        repository = AquariumRepository(session)
        aquariums = repository.list_by_owner(current_user.user.id)
        return success_response([_to_payload(a) for a in aquariums], request_id=request_id)

    @router.get("/{aquarium_id}", response_model=AquariumResponse)
    async def get_aquarium(
        aquarium_id: uuid.UUID,
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        repository = AquariumRepository(session)
        aquarium = repository.get_by_id_and_owner(aquarium_id, current_user.user.id)
        if aquarium is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aquarium not found")
        return success_response(_to_payload(aquarium), request_id=request_id)

    @router.post("", response_model=AquariumResponse, status_code=status.HTTP_201_CREATED)
    async def create_aquarium(
        request: Request,
        payload: CreateAquariumRequest = Body(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        logger = request.app.state.logger
        logger.info("aquarium.request")
        request_id = getattr(request.state, "request_id", "unknown")
        repository = AquariumRepository(session)
        volume_liters = _to_liters(payload.volume)

        logger.info(
            "aquarium.create.start",
            extra={
                "request_id": request_id,
                "owner_user_id": current_user.user.id,
                "aquarium_name": payload.name,
                "aquarium_type": payload.type,
                "volume_value": payload.volume.value,
                "volume_unit": payload.volume.unit,
                "volume_liters": volume_liters,
            },
        )
        try:
            aquarium = repository.create(
                owner_user_id=current_user.user.id,
                name=payload.name,
                aquarium_type=payload.type,
                volume_liters=volume_liters,
            )
        except DuplicateAquariumNameError as exc:
            logger.warning(
                "aquarium.create.duplicate_name",
                extra={
                    "request_id": request_id,
                    "owner_user_id": current_user.user.id,
                    "aquarium_name": payload.name,
                },
            )
            raise _duplicate_name_http_error() from exc

        logger.info(
            "aquarium.create.success",
            extra={
                "request_id": request_id,
                "owner_user_id": current_user.user.id,
                "aquarium_id": aquarium.id,
                "aquarium_name": aquarium.name,
            },
        )

        return success_response(
            _to_payload(aquarium), request_id=request_id, status_code=status.HTTP_201_CREATED
        )

    @router.patch("/{aquarium_id}", response_model=AquariumResponse)
    async def update_aquarium(
        aquarium_id: uuid.UUID,
        request: Request,
        payload: UpdateAquariumRequest = Body(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        updates = payload.model_dump(exclude_unset=True)
        if "volume" in updates:
            volume_payload = payload.volume
            if volume_payload is not None:
                updates["volume_liters"] = _to_liters(volume_payload)
            updates.pop("volume", None)

        repository = AquariumRepository(session)
        try:
            aquarium = repository.update_by_id_and_owner(
                aquarium_id=aquarium_id,
                owner_user_id=current_user.user.id,
                updates=updates,
            )
        except DuplicateAquariumNameError as exc:
            raise _duplicate_name_http_error() from exc

        if aquarium is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aquarium not found")

        return success_response(_to_payload(aquarium), request_id=request_id)

    @router.delete("/{aquarium_id}", response_model=DeleteAquariumResponse)
    async def delete_aquarium(
        aquarium_id: uuid.UUID,
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        repository = AquariumRepository(session)
        deleted = repository.delete_by_id_and_owner(aquarium_id, current_user.user.id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aquarium not found")
        return success_response({"id": str(aquarium_id), "deleted": True}, request_id=request_id)

    return router
