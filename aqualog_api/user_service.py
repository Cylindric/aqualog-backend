from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aqualog_api.models import User
from aqualog_api.user_repository import UserRepository


@dataclass
class AuthenticatedUser:
    claims: dict[str, Any]
    user: User


def resolve_or_create_authenticated_user(
    claims: dict[str, Any],
    repository: UserRepository,
) -> AuthenticatedUser:
    issuer = str(claims.get("iss", "")).rstrip("/")
    subject = str(claims.get("sub", ""))
    if not issuer or not subject:
        raise ValueError("Token missing required identity claims")

    user = repository.resolve_or_create(oauth_issuer=issuer, oauth_subject=subject)
    return AuthenticatedUser(claims=claims, user=user)
