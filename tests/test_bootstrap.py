import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.app import create_app
from src.config import Settings, load_settings


def test_missing_required_config_fails_fast(monkeypatch):
    monkeypatch.delenv("AQUALOG_APP_ENV", raising=False)

    with pytest.raises(ValidationError):
        load_settings()


def test_create_app_fails_fast_when_oauth_config_missing():
    with pytest.raises(RuntimeError):
        create_app(Settings(app_env="test", auth_mode="oauth"))


def test_create_app_fails_fast_when_none_mode_impersonation_id_missing():
    with pytest.raises(RuntimeError):
        create_app(Settings(app_env="test", auth_mode="none"))


def test_create_app_succeeds_in_none_mode_with_impersonation_id():
    app = create_app(
        Settings(app_env="test", auth_mode="none", auth_impersonate_user_id="some-user-id")
    )

    assert app is not None


def test_versioned_namespace_route_exists():
    app = create_app(
        Settings(
            app_env="test",
            api_version="v1",
            oauth_issuer_url="https://auth.example.com/application/o/aqualog",
            oauth_audience="test-client-id",
        )
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/live")

    assert response.status_code == 200


def test_unknown_route_returns_not_found_without_crash():
    app = create_app(
        Settings(
            app_env="test",
            api_version="v1",
            oauth_issuer_url="https://auth.example.com/application/o/aqualog",
            oauth_audience="test-client-id",
        )
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/not-a-route")

    assert response.status_code == 404


def test_oauth_audience_falls_back_to_client_id(monkeypatch):
    monkeypatch.setenv("AQUALOG_APP_ENV", "test")
    monkeypatch.setenv("AQUALOG_OAUTH_ISSUER_URL", "https://auth.example.com/application/o/aqualog")
    monkeypatch.delenv("AQUALOG_OAUTH_AUDIENCE", raising=False)
    monkeypatch.setenv("AQUALOG_OAUTH_CLIENT_ID", "client-id-from-env")

    settings = load_settings()

    assert settings.oauth_audience == "client-id-from-env"


def test_favicon_route_serves_icon():
    app = create_app(
        Settings(
            app_env="test",
            api_version="v1",
            oauth_issuer_url="https://auth.example.com/application/o/aqualog",
            oauth_audience="test-client-id",
        )
    )

    with TestClient(app) as client:
        response = client.get("/favicon.png")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
