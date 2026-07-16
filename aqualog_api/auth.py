"""OAuth2 authentication module for API endpoint protection."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from authlib.jose import JsonWebToken
from authlib.jose.errors import JoseError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from aqualog_api.config import Settings, load_settings
from aqualog_api.db import get_session
from aqualog_api.user_repository import UserRepository
from aqualog_api.user_service import AuthenticatedUser, resolve_or_create_authenticated_user

logger = logging.getLogger(__name__)

# JWT and JWKS caching
_jwt_instance: JsonWebToken | None = None
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
        async with httpx.AsyncClient() as client:
            # Ensure issuer URL ends without trailing slash for discovery
            issuer = settings.oauth_issuer_url.rstrip("/")
            discovery_url = f"{issuer}/.well-known/openid-configuration"
            
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
            
    except httpx.HTTPError as e:
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
    global _jwt_instance
    
    if _jwt_instance is None:
        _jwt_instance = JsonWebToken(algorithms=["RS256"])
    
    try:
        # Get JWKS keys for signature validation
        jwks = await get_jwks_keys(settings)
        
        # Decode and validate token
        issuer = settings.oauth_issuer_url.rstrip("/")
        claims = _jwt_instance.decode(
            token,
            jwks,
        )
        
        # Validate issuer. Normalize trailing slash because providers may emit
        # issuer URLs with or without a final '/'.
        token_issuer = str(claims.get("iss", "")).rstrip("/")
        if token_issuer != issuer:
            logger.warning(f"Invalid issuer in token: {claims.get('iss')}")
            raise ValueError(f"Invalid issuer")
        
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
        raise ValueError(f"Invalid token: {str(e)}")
    except ValueError as e:
        logger.warning(f"Token validation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}")
        raise ValueError(f"Token validation error: {str(e)}")


# OAuth2 security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: Session = Depends(get_session),
) -> AuthenticatedUser:
    """
    FastAPI dependency for protecting endpoints with OAuth2 authentication.
    
    Returns the decoded token claims if validation succeeds.
    Raises HTTPException with 401 status if validation fails.
    """
    settings = request.app.state.settings
    
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
        )
    except Exception as e:
        logger.error(f"Authentication context error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication context unavailable",
        )
