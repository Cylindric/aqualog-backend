from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from aqualog_api.auth import get_current_user
from aqualog_api.db import get_session
from aqualog_api.models import User
from aqualog_api.responses import success_response
from aqualog_api.user_repository import UserRepository
from aqualog_api.user_service import AuthenticatedUser


class UserProfile(BaseModel):
    id: str
    display_name: str | None
    bio: str | None
    created_at: str
    updated_at: str


class UserProfileResponse(BaseModel):
    success: bool
    request_id: str
    data: UserProfile


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=500)


def _to_profile_payload(user: User) -> dict[str, str | None]:
    return {
        "id": user.id,
        "display_name": user.display_name,
        "bio": user.bio,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def build_profile_router() -> APIRouter:
    router = APIRouter(tags=["profile"])

    @router.get("/me", response_model=UserProfileResponse)
    async def get_my_profile(
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        return success_response(_to_profile_payload(current_user.user), request_id=request_id)

    @router.patch("/me", response_model=UserProfileResponse)
    async def update_my_profile(
        request: Request,
        payload: UpdateProfileRequest = Body(...),
        current_user: AuthenticatedUser = Depends(get_current_user),
        session: Session = Depends(get_session),
    ):
        request_id = getattr(request.state, "request_id", "unknown")

        updates = payload.model_dump(exclude_unset=True)
        if updates:
            repository = UserRepository(session)
            updated_user = repository.update_profile(current_user.user, updates)
        else:
            updated_user = current_user.user

        return success_response(_to_profile_payload(updated_user), request_id=request_id)

    return router
