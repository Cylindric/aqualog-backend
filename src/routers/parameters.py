from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.auth import get_current_user
from src.db import get_session
from src.models import Parameter, Unit
from src.parameter_repository import (
    DuplicateParameterSlugError,
    ParameterInUseError,
    ParameterRepository,
)
from src.responses import success_response
from src.schemas.parameters import (
    CreateParameterRequest,
    DeleteParameterResponse,
    ParameterDetailResponse,
    ParameterListResponse,
    ParameterResponse,
    UpdateParameterRequest,
)
from src.unit_repository import UnitRepository
from src.user_service import AuthenticatedUser


def _to_payload(parameter: Parameter, canonical_unit: Unit | None) -> dict[str, str | None]:
    return {
        "slug": parameter.slug,
        "display_name": parameter.display_name,
        "description": parameter.description,
        "unit": canonical_unit.unit if canonical_unit is not None else None,
        "created_at": parameter.created_at.isoformat(),
        "updated_at": parameter.updated_at.isoformat(),
    }


def _to_detail_payload(parameter: Parameter, units: list[tuple[Unit, bool]]) -> dict[str, object]:
    canonical_unit = next((unit for unit, is_canonical in units if is_canonical), None)
    return {
        "slug": parameter.slug,
        "display_name": parameter.display_name,
        "description": parameter.description,
        "unit": canonical_unit.unit if canonical_unit is not None else None,
        "units": [
            {
                "slug": unit.slug,
                "unit": unit.unit,
                "display_name": unit.display_name,
                "description": unit.description,
                "is_canonical": is_canonical,
            }
            for unit, is_canonical in units
        ],
        "created_at": parameter.created_at.isoformat(),
        "updated_at": parameter.updated_at.isoformat(),
    }


def _duplicate_slug_http_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Parameter slug already exists",
    )


def _not_found_http_error() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found")


def build_parameter_router() -> APIRouter:
    router = APIRouter(prefix="/parameters", tags=["parameters"])

    @router.get("", response_model=ParameterListResponse, summary="List parameter catalog")
    async def list_parameters(
        request: Request,
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        repository = ParameterRepository(session)
        unit_repository = UnitRepository(session)
        parameters = repository.list_all()
        payload = [_to_payload(p, unit_repository.get_canonical_unit(p.id)) for p in parameters]
        return success_response(payload, request_id=request_id)

    @router.get("/{slug}", response_model=ParameterDetailResponse)
    async def get_parameter(
        slug: str,
        request: Request,
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        repository = ParameterRepository(session)
        parameter = repository.get_by_slug(slug.strip().lower())
        if parameter is None:
            raise _not_found_http_error()
        unit_repository = UnitRepository(session)
        units = unit_repository.list_units_for_parameter_with_canonical(parameter.id)
        return success_response(_to_detail_payload(parameter, units), request_id=request_id)

    @router.post("", response_model=ParameterResponse, status_code=status.HTTP_201_CREATED)
    async def create_parameter(
        request: Request,
        payload: CreateParameterRequest = Body(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        repository = ParameterRepository(session)
        try:
            parameter = repository.create(
                slug=payload.slug,
                display_name=payload.display_name,
                description=payload.description,
            )
        except DuplicateParameterSlugError as exc:
            raise _duplicate_slug_http_error() from exc

        return success_response(
            _to_payload(parameter, None),
            request_id=request_id,
            status_code=status.HTTP_201_CREATED,
        )

    @router.patch("/{slug}", response_model=ParameterResponse)
    async def update_parameter(
        slug: str,
        request: Request,
        payload: UpdateParameterRequest = Body(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        updates = payload.model_dump(exclude_unset=True)

        repository = ParameterRepository(session)
        parameter = repository.update_by_slug(slug.strip().lower(), updates)
        if parameter is None:
            raise _not_found_http_error()

        unit_repository = UnitRepository(session)
        canonical_unit = unit_repository.get_canonical_unit(parameter.id)
        return success_response(_to_payload(parameter, canonical_unit), request_id=request_id)

    @router.delete("/{slug}", response_model=DeleteParameterResponse)
    async def delete_parameter(
        slug: str,
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        normalized_slug = slug.strip().lower()
        repository = ParameterRepository(session)
        try:
            deleted = repository.delete_by_slug(normalized_slug)
        except ParameterInUseError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Parameter is still referenced by measurements or thresholds",
            ) from exc

        if not deleted:
            raise _not_found_http_error()

        return success_response({"slug": normalized_slug, "deleted": True}, request_id=request_id)

    return router
