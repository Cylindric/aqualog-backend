from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from aqualog_api.app import create_app
from aqualog_api.config import Settings


@pytest.fixture
def auth_settings(tmp_path):
    return Settings(
        app_env="test",
        oauth_issuer_url="https://auth.example.com/application/o/aqualog",
        oauth_audience="test-client-id",
        test_database_url=f"sqlite+pysqlite:///{tmp_path}/test-profile.db",
    )


def test_get_my_profile_returns_current_user_profile(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="profile-user", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/me",
                headers={"Authorization": f"Bearer {token}", "x-request-id": "req-profile-get"},
            )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["request_id"] == "req-profile-get"
    assert body["data"]["id"]
    assert body["data"]["display_name"] is None


def test_patch_my_profile_updates_allowed_fields(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="profile-user-2", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            response = client.patch(
                "/api/v1/me",
                headers={"Authorization": f"Bearer {token}", "x-request-id": "req-profile-patch"},
                json={"display_name": "Aqua Tester", "bio": "Keeping SPS"},
            )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["display_name"] == "Aqua Tester"
    assert body["data"]["bio"] == "Keeping SPS"


def test_patch_my_profile_rejects_disallowed_fields(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="profile-user-3", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            response = client.patch(
                "/api/v1/me",
                headers={"Authorization": f"Bearer {token}"},
                json={"oauth_subject": "attempted-overwrite"},
            )

    body = response.json()
    assert response.status_code == 422
    assert body["success"] is False
    assert body["error"]["code"] == "validation_error"


def test_me_endpoints_require_authentication(auth_settings):
    app = create_app(auth_settings)

    with TestClient(app) as client:
        get_response = client.get("/api/v1/me")
        patch_response = client.patch("/api/v1/me", json={"display_name": "Nope"})

    assert get_response.status_code == 401
    assert patch_response.status_code == 401
