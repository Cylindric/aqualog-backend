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
        test_database_url=f"sqlite+pysqlite:///{tmp_path}/test-health.db",
    )


def test_liveness_returns_machine_readable_healthy_status():
    app = create_app(Settings(app_env="test"))

    with TestClient(app) as client:
        response = client.get("/api/v1/live")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "healthy"


def test_readiness_transitions_from_not_ready_to_ready():
    app = create_app(Settings(app_env="test"))

    # Simulate startup transition window before dependency initialization finishes.
    app.state.readiness.is_ready = False

    with TestClient(app) as client:
        app.state.readiness.is_ready = False
        not_ready = client.get("/api/v1/ready")
        app.state.readiness.is_ready = True
        ready = client.get("/api/v1/ready")

    assert not_ready.status_code == 503
    assert not_ready.json()["data"]["status"] == "not_ready"
    assert ready.status_code == 200
    assert ready.json()["data"]["status"] == "ready"


def test_liveness_does_not_require_authentication(auth_settings):
    """Test that liveness endpoint is accessible without authentication."""
    app = create_app(auth_settings)

    with TestClient(app) as client:
        response = client.get("/api/v1/live")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "healthy"
    assert response.json()["success"] is True


def test_readiness_does_not_require_authentication(auth_settings):
    """Test that readiness endpoint is accessible without authentication."""
    app = create_app(auth_settings)
    app.state.readiness.is_ready = True

    with TestClient(app) as client:
        response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ready"
    assert response.json()["success"] is True


def test_liveness_accepts_but_ignores_invalid_token(auth_settings):
    """Test that liveness endpoint ignores provided tokens."""
    app = create_app(auth_settings)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/live",
            headers={"Authorization": "Bearer invalid.token"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "healthy"


def test_readiness_accepts_but_ignores_invalid_token(auth_settings):
    """Test that readiness endpoint ignores provided tokens."""
    app = create_app(auth_settings)
    app.state.readiness.is_ready = True

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/ready",
            headers={"Authorization": "Bearer invalid.token"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ready"

