from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from aqualog_api.app import create_app
from aqualog_api.config import Settings
from aqualog_api.responses import success_response


class InputModel(BaseModel):
    value: int


def test_success_envelope_contains_data_and_request_id():
    app = create_app(Settings(app_env="test"))

    with TestClient(app) as client:
        response = client.get("/api/v1/live", headers={"x-request-id": "req-123"})

    body = response.json()
    assert response.headers["content-type"].startswith("application/json")
    assert body["success"] is True
    assert body["request_id"] == "req-123"
    assert "data" in body


def test_validation_error_uses_standard_error_envelope():
    app = create_app(Settings(app_env="test"))
    router = APIRouter(prefix="/api/v1")

    @router.post("/echo")
    async def echo(payload: InputModel):
        return success_response({"value": payload.value}, request_id="test")

    app.include_router(router)

    with TestClient(app) as client:
        response = client.post("/api/v1/echo", json={"value": "invalid"})

    body = response.json()
    assert response.status_code == 422
    assert body["success"] is False
    assert body["error"]["code"] == "validation_error"
    assert "request_id" in body


def test_internal_error_uses_sanitized_standard_error_envelope():
    app = create_app(Settings(app_env="test"))
    router = APIRouter(prefix="/api/v1")

    @router.get("/boom")
    async def boom():
        raise RuntimeError("sensitive stack context")

    app.include_router(router)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/boom")

    body = response.json()
    assert response.status_code == 500
    assert body["success"] is False
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An internal server error occurred."
    assert "request_id" in body
