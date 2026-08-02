from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.orm import Session

from src.auth import get_current_user
from src.db import get_session
from src.models import User
from src.responses import success_response
from src.schemas.profile import UpdateProfileRequest, UserProfileResponse
from src.user_repository import UserRepository
from src.user_service import AuthenticatedUser


def _to_profile_payload(user: User) -> dict[str, str | None]:
    return {
        "id": str(user.id),
        "username": user.username,
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
