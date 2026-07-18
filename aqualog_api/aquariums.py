from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from aqualog_api.aquarium_repository import AquariumRepository, DuplicateAquariumNameError
from aqualog_api.auth import get_current_user
from aqualog_api.db import get_session
from aqualog_api.models import Aquarium
from aqualog_api.responses import success_response
from aqualog_api.user_service import AuthenticatedUser

GALLON_US_TO_LITER = 3.785411784
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


def _to_liters(volume: VolumeInput) -> float:
    if volume.unit == "L":
        return volume.value
    return volume.value * GALLON_US_TO_LITER


def _to_payload(aquarium: Aquarium) -> dict[str, str | float]:
    return {
        "id": aquarium.id,
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

    @router.get("", response_model=AquariumListResponse)
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
        aquarium_id: str,
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

        return success_response(_to_payload(aquarium), request_id=request_id, status_code=status.HTTP_201_CREATED)

    @router.patch("/{aquarium_id}", response_model=AquariumResponse)
    async def update_aquarium(
        aquarium_id: str,
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
        aquarium_id: str,
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        repository = AquariumRepository(session)
        deleted = repository.delete_by_id_and_owner(aquarium_id, current_user.user.id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aquarium not found")
        return success_response({"id": aquarium_id, "deleted": True}, request_id=request_id)

    return router
