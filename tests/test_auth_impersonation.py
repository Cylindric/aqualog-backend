import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from src.app import create_app
from src.config import Settings


def _oauth_settings(test_database_url: str) -> Settings:
    return Settings(
        app_env="test",
        oauth_issuer_url="https://auth.example.com/application/o/aqualog",
        oauth_audience="test-client-id",
        test_database_url=test_database_url,
    )


def _none_settings(test_database_url: str, impersonate_user_id: str) -> Settings:
    return Settings(
        app_env="test",
        auth_mode="none",
        auth_impersonate_user_id=impersonate_user_id,
        test_database_url=test_database_url,
    )


def _create_user_via_oauth(tmp_path, test_database_url, create_valid_token, mock_jwks) -> str:
    app = create_app(_oauth_settings(test_database_url))
    token = create_valid_token(sub="impersonated-user")

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    user_id: str = response.json()["data"]["id"]
    return user_id


def test_impersonation_mode_resolves_configured_user_without_a_token(
    tmp_path, create_valid_token, mock_jwks
):
    test_database_url = f"sqlite+pysqlite:///{tmp_path}/impersonation.db"
    user_id = _create_user_via_oauth(tmp_path, test_database_url, create_valid_token, mock_jwks)

    app = create_app(_none_settings(test_database_url, user_id))

    with TestClient(app) as client:
        response = client.get("/api/v1/me")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"] == user_id


def test_impersonation_mode_ignores_a_provided_bearer_token(
    tmp_path, create_valid_token, mock_jwks
):
    test_database_url = f"sqlite+pysqlite:///{tmp_path}/impersonation-with-token.db"
    user_id = _create_user_via_oauth(tmp_path, test_database_url, create_valid_token, mock_jwks)

    app = create_app(_none_settings(test_database_url, user_id))

    with TestClient(app) as client:
        response = client.get("/api/v1/me", headers={"Authorization": "Bearer this-is-not-checked"})

    assert response.status_code == 200
    assert response.json()["data"]["id"] == user_id


def test_impersonation_mode_rejects_unknown_user_id_without_creating_one(tmp_path):
    test_database_url = f"sqlite+pysqlite:///{tmp_path}/impersonation-unknown.db"
    unknown_user_id = str(uuid.uuid4())

    app = create_app(_none_settings(test_database_url, unknown_user_id))

    with TestClient(app) as client:
        response = client.get("/api/v1/me")

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False

    engine = create_engine(test_database_url, future=True)
    with engine.connect() as connection:
        count = connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one()

    assert count == 0
