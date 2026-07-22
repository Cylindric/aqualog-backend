"""Tests for OAuth2 authentication module."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, status

from src.auth import validate_token, get_current_user
from src.config import Settings


@pytest.fixture
def auth_settings(tmp_path):
    """Create a Settings instance for testing."""
    return Settings(
        app_env="test",
        oauth_issuer_url="https://auth.example.com/application/o/aqualog",
        oauth_audience="test-client-id",
        test_database_url=f"sqlite+pysqlite:///{tmp_path}/test-auth.db",
    )


class TestValidateToken:
    """Tests for token validation function."""

    @pytest.mark.asyncio
    async def test_validate_token_with_valid_token(self, create_valid_token, auth_settings, mock_jwks, mock_oidc_config):
        """Test that valid tokens are accepted."""
        token = create_valid_token(sub="user123", aud="test-client-id")

        with patch("src.auth.get_jwks_keys") as mock_get_keys:
            mock_get_keys.return_value = mock_jwks
            
            claims = await validate_token(token, auth_settings)
            
            assert claims["sub"] == "user123"
            assert claims["aud"] == "test-client-id"
            assert claims["iss"] == auth_settings.oauth_issuer_url.rstrip("/")

    @pytest.mark.asyncio
    async def test_validate_token_with_expired_token(self, create_expired_token, auth_settings, mock_jwks):
        """Test that expired tokens are rejected."""
        token = create_expired_token()

        with patch("src.auth.get_jwks_keys") as mock_get_keys:
            mock_get_keys.return_value = mock_jwks
            
            with pytest.raises(ValueError, match="expired|Token"):
                await validate_token(token, auth_settings)

    @pytest.mark.asyncio
    async def test_validate_token_with_invalid_issuer(self, create_valid_token, auth_settings, mock_jwks, mock_rsa_keys):
        """Test that tokens with wrong issuer are rejected."""
        token = create_valid_token(sub="user123", aud="test-client-id", issuer="https://wrong-issuer.com")

        with patch("src.auth.get_jwks_keys") as mock_get_keys:
            mock_get_keys.return_value = mock_jwks
            
            with pytest.raises(ValueError, match="issuer"):
                await validate_token(token, auth_settings)

    @pytest.mark.asyncio
    async def test_validate_token_with_invalid_audience(self, create_valid_token, auth_settings, mock_jwks):
        """Test that tokens with wrong audience are rejected."""
        # Create token with wrong audience
        token = create_valid_token(aud="wrong-audience")

        with patch("src.auth.get_jwks_keys") as mock_get_keys:
            mock_get_keys.return_value = mock_jwks
            
            with pytest.raises(ValueError, match="audience"):
                await validate_token(token, auth_settings)

    @pytest.mark.asyncio
    async def test_validate_token_with_missing_token(self, auth_settings, mock_jwks):
        """Test that missing/empty tokens are rejected."""
        with patch("src.auth.get_jwks_keys") as mock_get_keys:
            mock_get_keys.return_value = mock_jwks
            
            with pytest.raises(ValueError):
                await validate_token("", auth_settings)

    @pytest.mark.asyncio
    async def test_validate_token_with_malformed_token(self, auth_settings, mock_jwks):
        """Test that malformed tokens are rejected."""
        with patch("src.auth.get_jwks_keys") as mock_get_keys:
            mock_get_keys.return_value = mock_jwks
            
            with pytest.raises(ValueError):
                await validate_token("not.a.jwt", auth_settings)


class TestGetCurrentUser:
    """Tests for the get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_credentials_via_endpoint(self, create_valid_token, auth_settings, mock_jwks):
        """Test that valid credentials are accepted via HTTP endpoint."""
        from fastapi.testclient import TestClient
        from src.app import create_app
        
        token = create_valid_token(sub="user123")
        app = create_app(auth_settings)

        with patch("src.auth.get_jwks_keys") as mock_get_keys:
            mock_get_keys.return_value = mock_jwks
            
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/calculate/dose/salinity",
                    params={"volume": 100.0, "current": 30.0, "target": 35.0},
                    headers={"Authorization": f"Bearer {token}"},
                )
                
                assert response.status_code == 200
                body = response.json()
                assert body["success"] is True
                assert body["data"]["quantity"] == 550.0

    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_credentials_via_endpoint(self, auth_settings, mock_jwks):
        """Test that invalid credentials are rejected via HTTP endpoint."""
        from fastapi.testclient import TestClient
        from src.app import create_app
        
        app = create_app(auth_settings)

        with patch("src.auth.get_jwks_keys") as mock_get_keys:
            mock_get_keys.return_value = mock_jwks
            
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/calculate/dose/salinity",
                    params={"volume": 100.0, "current": 30.0, "target": 35.0},
                    headers={"Authorization": "Bearer invalid.token"},
                )
                
                assert response.status_code == 401
                body = response.json()
                assert body["success"] is False
                assert body["error"]["code"] == "authentication_error"

    @pytest.mark.asyncio
    async def test_get_current_user_with_expired_token_via_endpoint(self, create_expired_token, auth_settings, mock_jwks):
        """Test that expired tokens are rejected via HTTP endpoint."""
        from fastapi.testclient import TestClient
        from src.app import create_app
        
        token = create_expired_token()
        app = create_app(auth_settings)

        with patch("src.auth.get_jwks_keys") as mock_get_keys:
            mock_get_keys.return_value = mock_jwks
            
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/calculate/dose/salinity",
                    params={"volume": 100.0, "current": 30.0, "target": 35.0},
                    headers={"Authorization": f"Bearer {token}"},
                )
                
                assert response.status_code == 401
                body = response.json()
                assert body["success"] is False
                assert body["error"]["code"] == "authentication_error"
