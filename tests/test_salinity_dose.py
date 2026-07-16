from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from aqualog_api.app import create_app
from aqualog_api.config import Settings


@pytest.fixture
def auth_settings(tmp_path):
    """Create Settings with OAuth2 configuration for testing."""
    return Settings(
        app_env="test",
        oauth_issuer_url="https://auth.example.com/application/o/aqualog",
        oauth_audience="test-client-id",
        test_database_url=f"sqlite+pysqlite:///{tmp_path}/test-salinity.db",
    )


def test_salinity_dose_returns_expected_quantity_in_success_envelope(
    create_valid_token, auth_settings, mock_jwks, mock_oidc_config
):
    app = create_app(auth_settings)
    token = create_valid_token(sub="test-user", aud="test-client-id")

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/calculate/dose/salinity",
                params={"volume": 100.0, "current": 30.0, "target": 35.0},
                headers={
                    "x-request-id": "req-salinity-1",
                    "Authorization": f"Bearer {token}",
                },
            )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["request_id"] == "req-salinity-1"
    assert body["data"]["volume"] == 100.0
    assert body["data"]["current"] == 30.0
    assert body["data"]["target"] == 35.0
    assert body["data"]["quantity"] == 550.0


def test_salinity_dose_allows_negative_quantity_when_target_below_current(
    create_valid_token, auth_settings, mock_jwks, mock_oidc_config
):
    app = create_app(auth_settings)
    token = create_valid_token(sub="test-user", aud="test-client-id")

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/calculate/dose/salinity",
                params={"volume": 10.0, "current": 35.0, "target": 30.0},
                headers={
                    "x-request-id": "req-salinity-2",
                    "Authorization": f"Bearer {token}",
                },
            )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["request_id"] == "req-salinity-2"
    assert body["data"]["quantity"] == -55.0


def test_salinity_dose_missing_or_invalid_params_return_standard_error_envelope(
    create_valid_token, auth_settings, mock_jwks, mock_oidc_config
):
    app = create_app(auth_settings)
    token = create_valid_token(sub="test-user", aud="test-client-id")

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        
        with TestClient(app) as client:
            missing_response = client.get(
                "/api/v1/calculate/dose/salinity",
                params={"volume": 100.0, "current": 30.0},
                headers={
                    "x-request-id": "req-salinity-missing",
                    "Authorization": f"Bearer {token}",
                },
            )
            invalid_response = client.get(
                "/api/v1/calculate/dose/salinity",
                params={"volume": "bad", "current": 30.0, "target": 35.0},
                headers={
                    "x-request-id": "req-salinity-invalid",
                    "Authorization": f"Bearer {token}",
                },
            )

    missing_body = missing_response.json()
    invalid_body = invalid_response.json()

    assert missing_response.status_code == 422
    assert missing_body["success"] is False
    assert missing_body["error"]["code"] == "validation_error"
    assert missing_body["request_id"] == "req-salinity-missing"

    assert invalid_response.status_code == 422
    assert invalid_body["success"] is False
    assert invalid_body["error"]["code"] == "validation_error"
    assert invalid_body["request_id"] == "req-salinity-invalid"


def test_salinity_dose_requires_authentication(auth_settings):
    """Test that salinity dose endpoint returns 401 without authentication."""
    app = create_app(auth_settings)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/calculate/dose/salinity",
            params={"volume": 100.0, "current": 30.0, "target": 35.0},
            headers={"x-request-id": "req-salinity-no-auth"},
        )

    body = response.json()
    assert response.status_code == 401
    assert body["success"] is False
    assert body["error"]["code"] == "authentication_error"


def test_salinity_dose_rejects_invalid_token(auth_settings, mock_jwks):
    """Test that salinity dose endpoint rejects invalid tokens."""
    app = create_app(auth_settings)

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/calculate/dose/salinity",
                params={"volume": 100.0, "current": 30.0, "target": 35.0},
                headers={
                    "x-request-id": "req-salinity-invalid-token",
                    "Authorization": "Bearer invalid.token.here",
                },
            )

    body = response.json()
    assert response.status_code == 401
    assert body["success"] is False
    assert body["error"]["code"] == "authentication_error"

