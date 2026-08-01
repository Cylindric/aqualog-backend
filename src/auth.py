"""OAuth2 authentication module for API endpoint protection."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, cast

import httpx2
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from joserfc import jwk, jwt
from joserfc.errors import JoseError
from sqlalchemy.orm import Session

from src.config import Settings
from src.db import get_session
from src.user_repository import UserRepository
from src.user_service import AuthenticatedUser, resolve_or_create_authenticated_user

logger = logging.getLogger(__name__)

# JWT and JWKS caching
_jwks_keys: dict[str, Any] | None = None
_jwks_expiry: datetime | None = None
JWKS_CACHE_TTL_SECONDS = 3600  # 1 hour


async def get_jwks_keys(settings: Settings) -> dict[str, Any]:
    """
    Fetch and cache JWKS keys from the OAuth2 provider's discovery endpoint.

    Implements caching to minimize external calls while supporting key rotation.
    Cache TTL is 1 hour by default.
    """
    global _jwks_keys, _jwks_expiry

    now = datetime.now(timezone.utc)

    # Return cached keys if still valid
    if _jwks_keys is not None and _jwks_expiry is not None and now < _jwks_expiry:
        return _jwks_keys

    try:
        # Fetch OIDC discovery document
        async with httpx2.AsyncClient() as client:
            # Discovery may need a different (e.g. internal-network) URL than the
            # issuer used for token validation, so fall back to oauth_issuer_url
            # only when oauth_discovery_url isn't explicitly configured.
            discovery_base = settings.oauth_discovery_url or settings.oauth_issuer_url
            if discovery_base is None:
                raise ValueError("OAuth issuer URL must be configured")
            discovery_url = f"{discovery_base.rstrip('/')}/.well-known/openid-configuration"

            logger.debug(f"Fetching OIDC discovery from {discovery_url}")
            discovery_response = await client.get(discovery_url, timeout=10.0)
            discovery_response.raise_for_status()
            discovery = discovery_response.json()

            jwks_uri = discovery.get("jwks_uri")
            if not jwks_uri:
                raise ValueError("JWKS URI not found in OIDC discovery document")

            # Fetch JWKS
            logger.debug(f"Fetching JWKS from {jwks_uri}")
            jwks_response = await client.get(jwks_uri, timeout=10.0)
            jwks_response.raise_for_status()
            jwks_data = jwks_response.json()

            # Cache the keys
            _jwks_keys = jwks_data
            _jwks_expiry = now + timedelta(seconds=JWKS_CACHE_TTL_SECONDS)

            logger.info("JWKS keys fetched and cached successfully")
            return _jwks_keys

    except httpx2.HTTPError as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching JWKS: {e}")
        raise


async def validate_token(
    token: str,
    settings: Settings,
) -> dict[str, Any]:
    """
    Validate JWT token signature, issuer, and audience claims.

    Returns the decoded token claims if valid.
    Raises HTTPException with 401 status if validation fails.
    """
    try:
        # Get JWKS keys for signature validation
        jwks = await get_jwks_keys(settings)
        # jwks is untyped JSON from the OIDC provider; its shape matches KeySetSerialization at runtime.
        key_set = jwk.KeySet.import_key_set(cast(jwk.KeySetSerialization, jwks))

        # Decode and validate token
        if settings.oauth_issuer_url is None:
            raise ValueError("OAuth issuer URL must be configured")
        issuer = settings.oauth_issuer_url.rstrip("/")
        decoded = jwt.decode(
            token,
            key_set,
            algorithms=["RS256"],
        )
        claims = decoded.claims

        # Validate issuer. Normalize trailing slash because providers may emit
        # issuer URLs with or without a final '/'.
        token_issuer = str(claims.get("iss", "")).rstrip("/")
        if token_issuer != issuer:
            logger.warning(f"Invalid issuer in token: {claims.get('iss')}")
            raise ValueError("Invalid issuer")

        # Validate audience
        aud = claims.get("aud")
        if isinstance(aud, list):
            if settings.oauth_audience not in aud:
                logger.warning(f"Audience not in token: {aud}")
                raise ValueError("Invalid audience")
        elif aud != settings.oauth_audience:
            logger.warning(f"Invalid audience in token: {aud}")
            raise ValueError("Invalid audience")

        # Validate expiration (authlib should already do this, but be explicit)
        exp = claims.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            logger.warning("Token is expired")
            raise ValueError("Token is expired")

        logger.debug(f"Token validated successfully for subject: {claims.get('sub')}")
        return claims

    except JoseError as e:
        logger.warning(f"JWT validation error: {e}")
        raise ValueError(f"Invalid token: {str(e)}") from e
    except ValueError as e:
        logger.warning(f"Token validation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}")
        raise ValueError(f"Token validation error: {str(e)}") from e


# OAuth2 security scheme
security = HTTPBearer(auto_error=False)


async def _authenticate_oauth(
    credentials: HTTPAuthorizationCredentials | None,
    session: Session,
    settings: Settings,
) -> AuthenticatedUser:
    if not settings.oauth_issuer_url or not settings.oauth_audience:
        logger.error("OAuth2 configuration is missing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service is not configured",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token = credentials.credentials
        claims = await validate_token(token, settings)
        repository = UserRepository(session)
        return resolve_or_create_authenticated_user(claims, repository)
    except ValueError as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        logger.error(f"Authentication context error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication context unavailable",
        ) from e


def _authenticate_impersonated(session: Session, settings: Settings) -> AuthenticatedUser:
    repository = UserRepository(session)
    user = (
        repository.get_by_id(settings.auth_impersonate_user_id)
        if settings.auth_impersonate_user_id
        else None
    )
    if user is None:
        logger.error("Configured impersonation user id does not exist")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service is not configured",
        )

    return AuthenticatedUser(claims={}, user=user)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: Session = Depends(get_session),
) -> AuthenticatedUser:
    """
    FastAPI dependency for protecting endpoints with configurable authentication.

    In `oauth` mode, validates a bearer token and resolves the local user.
    In `none` mode, bypasses token validation and resolves the configured
    impersonation user id instead.
    """
    settings = request.app.state.settings

    if settings.auth_mode == "none":
        return _authenticate_impersonated(session, settings)

    return await _authenticate_oauth(credentials, session, settings)
