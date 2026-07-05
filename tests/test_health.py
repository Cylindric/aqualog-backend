from fastapi.testclient import TestClient

from aqualog_api.app import create_app
from aqualog_api.config import Settings


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
