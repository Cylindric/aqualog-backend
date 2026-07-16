from fastapi.testclient import TestClient
from pydantic import ValidationError

from aqualog_api.app import create_app
from aqualog_api.config import Settings, load_settings


def test_missing_required_config_fails_fast(monkeypatch):
    monkeypatch.delenv("AQUALOG_APP_ENV", raising=False)

    try:
        load_settings()
        assert False, "Expected settings validation to fail"
    except ValidationError:
        assert True


def test_versioned_namespace_route_exists():
    app = create_app(Settings(app_env="test", api_version="v1"))

    with TestClient(app) as client:
        response = client.get("/api/v1/live")

    assert response.status_code == 200


def test_unknown_route_returns_not_found_without_crash():
    app = create_app(Settings(app_env="test", api_version="v1"))

    with TestClient(app) as client:
        response = client.get("/api/v1/not-a-route")

    assert response.status_code == 404


def test_oauth_audience_falls_back_to_client_id(monkeypatch):
    monkeypatch.setenv("AQUALOG_APP_ENV", "test")
    monkeypatch.delenv("AQUALOG_OAUTH_AUDIENCE", raising=False)
    monkeypatch.setenv("AQUALOG_OAUTH_CLIENT_ID", "client-id-from-env")

    settings = load_settings()

    assert settings.oauth_audience == "client-id-from-env"
