from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserProfile(BaseModel):
    id: str
    username: str | None
    display_name: str | None
    bio: str | None
    created_at: str
    updated_at: str
    groups: list[str] = Field(default_factory=list)


class UserProfileResponse(BaseModel):
    success: bool
    request_id: str
    data: UserProfile


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=500)
