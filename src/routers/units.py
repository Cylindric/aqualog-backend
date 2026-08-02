from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.auth import get_current_user
from src.db import get_session
from src.models import Unit
from src.responses import success_response
from src.schemas.units import (
    CreateUnitRequest,
    DeleteUnitResponse,
    UnitListResponse,
    UnitResponse,
    UpdateUnitRequest,
)
from src.unit_repository import DuplicateUnitSlugError, UnitInUseError, UnitRepository
from src.user_service import AuthenticatedUser


def _to_payload(unit: Unit) -> dict[str, str | None]:
    return {
        "slug": unit.slug,
        "unit": unit.unit,
        "display_name": unit.display_name,
        "description": unit.description,
        "created_at": unit.created_at.isoformat(),
        "updated_at": unit.updated_at.isoformat(),
    }


def _duplicate_slug_http_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Unit slug already exists",
    )


def _not_found_http_error() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")


def build_unit_router() -> APIRouter:
    router = APIRouter(prefix="/units", tags=["units"])

    @router.get("", response_model=UnitListResponse, summary="List unit catalog")
    async def list_units(
        request: Request,
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        repository = UnitRepository(session)
        units = repository.list_all()
        return success_response([_to_payload(u) for u in units], request_id=request_id)

    @router.get("/{slug}", response_model=UnitResponse)
    async def get_unit(
        slug: str,
        request: Request,
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        repository = UnitRepository(session)
        unit = repository.get_by_slug(slug.strip())
        if unit is None:
            raise _not_found_http_error()
        return success_response(_to_payload(unit), request_id=request_id)

    @router.post("", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
    async def create_unit(
        request: Request,
        payload: CreateUnitRequest = Body(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        repository = UnitRepository(session)
        try:
            unit = repository.create(
                unit=payload.unit,
                display_name=payload.display_name,
                description=payload.description,
            )
        except DuplicateUnitSlugError as exc:
            raise _duplicate_slug_http_error() from exc

        return success_response(
            _to_payload(unit), request_id=request_id, status_code=status.HTTP_201_CREATED
        )

    @router.patch("/{slug}", response_model=UnitResponse)
    async def update_unit(
        slug: str,
        request: Request,
        payload: UpdateUnitRequest = Body(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        updates = payload.model_dump(exclude_unset=True)

        repository = UnitRepository(session)
        unit = repository.update_by_slug(slug.strip(), updates)
        if unit is None:
            raise _not_found_http_error()

        return success_response(_to_payload(unit), request_id=request_id)

    @router.delete("/{slug}", response_model=DeleteUnitResponse)
    async def delete_unit(
        slug: str,
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        normalized_slug = slug.strip().lower()
        repository = UnitRepository(session)
        try:
            deleted = repository.delete_by_slug(normalized_slug)
        except UnitInUseError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unit is still referenced by measurements or parameter associations",
            ) from exc

        if not deleted:
            raise _not_found_http_error()

        return success_response({"slug": normalized_slug, "deleted": True}, request_id=request_id)

    return router
