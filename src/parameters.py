from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from src.auth import get_current_user
from src.db import get_session
from src.models import Parameter
from src.parameter_repository import (
    DuplicateParameterSlugError,
    ParameterInUseError,
    ParameterRepository,
)
from src.responses import success_response
from src.user_service import AuthenticatedUser


class ParameterPayload(BaseModel):
    slug: str
    display_name: str
    description: str | None
    created_at: str
    updated_at: str


class ParameterResponse(BaseModel):
    success: bool
    request_id: str
    data: ParameterPayload


class ParameterListResponse(BaseModel):
    success: bool
    request_id: str
    data: list[ParameterPayload]


class DeleteParameterPayload(BaseModel):
    slug: str
    deleted: bool


class DeleteParameterResponse(BaseModel):
    success: bool
    request_id: str
    data: DeleteParameterPayload


def _validate_slug(value: str) -> str:
    trimmed = value.strip().lower()
    if not trimmed:
        raise ValueError("slug must not be empty")
    return trimmed


def _validate_display_name(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("display_name must not be empty")
    return trimmed


class CreateParameterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., min_length=1, max_length=32)
    display_name: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        return _validate_slug(value)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        return _validate_display_name(value)


class UpdateParameterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_display_name(value)


def _to_payload(parameter: Parameter) -> dict[str, str | None]:
    return {
        "slug": parameter.slug,
        "display_name": parameter.display_name,
        "description": parameter.description,
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
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        repository = ParameterRepository(session)
        parameters = repository.list_all()
        return success_response([_to_payload(p) for p in parameters], request_id=request_id)

    @router.get("/{slug}", response_model=ParameterResponse)
    async def get_parameter(
        slug: str,
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        repository = ParameterRepository(session)
        parameter = repository.get_by_slug(slug.strip().lower())
        if parameter is None:
            raise _not_found_http_error()
        return success_response(_to_payload(parameter), request_id=request_id)

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
            _to_payload(parameter), request_id=request_id, status_code=status.HTTP_201_CREATED
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

        return success_response(_to_payload(parameter), request_id=request_id)

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
