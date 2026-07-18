from unittest.mock import MagicMock, patch

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
        test_database_url=f"sqlite+pysqlite:///{tmp_path}/test-aquariums.db",
    )


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "x-request-id": "req-aquarium"}


def test_aquarium_endpoints_require_authentication(auth_settings):
    app = create_app(auth_settings)

    with TestClient(app) as client:
        assert client.get("/api/v1/aquariums").status_code == 401
        assert client.post(
            "/api/v1/aquariums",
            json={"name": "A", "type": "reef", "volume": {"value": 1, "unit": "L"}},
        ).status_code == 401


def test_aquarium_crud_happy_path(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="aquarium-owner", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/aquariums",
                headers=_auth_header(token),
                json={
                    "name": "Display Reef",
                    "type": "  reef  ",
                    "volume": {"value": 100.0, "unit": "L"},
                },
            )
            assert create_response.status_code == 201
            created = create_response.json()["data"]
            aquarium_id = created["id"]
            assert created["type"] == "reef"
            assert created["volume_liters"] == pytest.approx(100.0)

            list_response = client.get("/api/v1/aquariums", headers=_auth_header(token))
            assert list_response.status_code == 200
            items = list_response.json()["data"]
            assert len(items) == 1
            assert items[0]["id"] == aquarium_id

            get_response = client.get(f"/api/v1/aquariums/{aquarium_id}", headers=_auth_header(token))
            assert get_response.status_code == 200
            assert get_response.json()["data"]["id"] == aquarium_id

            update_response = client.patch(
                f"/api/v1/aquariums/{aquarium_id}",
                headers=_auth_header(token),
                json={"type": "mixed", "volume": {"value": 10.0, "unit": "gal_us"}},
            )
            assert update_response.status_code == 200
            updated = update_response.json()["data"]
            assert updated["type"] == "mixed"
            assert updated["volume_liters"] == pytest.approx(37.85411784)

            delete_response = client.delete(
                f"/api/v1/aquariums/{aquarium_id}",
                headers=_auth_header(token),
            )
            assert delete_response.status_code == 200
            assert delete_response.json()["data"]["deleted"] is True


def test_aquarium_cross_user_access_is_not_found(create_valid_token, auth_settings, mock_jwks):
    owner_token = create_valid_token(sub="owner", aud="test-client-id")
    other_token = create_valid_token(sub="other", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/aquariums",
                headers=_auth_header(owner_token),
                json={"name": "Owner Tank", "type": "reef", "volume": {"value": 50.0, "unit": "L"}},
            )
            aquarium_id = create_response.json()["data"]["id"]

            assert client.get(
                f"/api/v1/aquariums/{aquarium_id}",
                headers=_auth_header(other_token),
            ).status_code == 404

            assert client.patch(
                f"/api/v1/aquariums/{aquarium_id}",
                headers=_auth_header(other_token),
                json={"name": "Stolen Tank"},
            ).status_code == 404

            assert client.delete(
                f"/api/v1/aquariums/{aquarium_id}",
                headers=_auth_header(other_token),
            ).status_code == 404


def test_aquarium_validation_and_units(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="validation-owner", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            short_type = client.post(
                "/api/v1/aquariums",
                headers=_auth_header(token),
                json={"name": "Tank", "type": "ab", "volume": {"value": 10.0, "unit": "L"}},
            )
            assert short_type.status_code == 422

            long_type = client.post(
                "/api/v1/aquariums",
                headers=_auth_header(token),
                json={
                    "name": "Tank",
                    "type": "x" * 25,
                    "volume": {"value": 10.0, "unit": "L"},
                },
            )
            assert long_type.status_code == 422

            missing_unit = client.post(
                "/api/v1/aquariums",
                headers=_auth_header(token),
                json={"name": "Tank", "type": "reef", "volume": {"value": 10.0}},
            )
            assert missing_unit.status_code == 422

            unsupported_unit = client.post(
                "/api/v1/aquariums",
                headers=_auth_header(token),
                json={"name": "Tank", "type": "reef", "volume": {"value": 10.0, "unit": "mL"}},
            )
            assert unsupported_unit.status_code == 422


def test_aquarium_name_unique_per_user(create_valid_token, auth_settings, mock_jwks):
    first_user_token = create_valid_token(sub="user-1", aud="test-client-id")
    second_user_token = create_valid_token(sub="user-2", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            first = client.post(
                "/api/v1/aquariums",
                headers=_auth_header(first_user_token),
                json={"name": "Nano", "type": "reef", "volume": {"value": 20.0, "unit": "L"}},
            )
            assert first.status_code == 201

            duplicate_same_user = client.post(
                "/api/v1/aquariums",
                headers=_auth_header(first_user_token),
                json={"name": "Nano", "type": "reef", "volume": {"value": 25.0, "unit": "L"}},
            )
            assert duplicate_same_user.status_code == 409

            same_name_other_user = client.post(
                "/api/v1/aquariums",
                headers=_auth_header(second_user_token),
                json={"name": "Nano", "type": "reef", "volume": {"value": 25.0, "unit": "L"}},
            )
            assert same_name_other_user.status_code == 201


def test_create_aquarium_logs_debug_context(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="logger-owner", aud="test-client-id")
    app = create_app(auth_settings)
    mock_logger = MagicMock()
    app.state.logger = mock_logger

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/aquariums",
                headers=_auth_header(token),
                json={"name": "Debug Tank", "type": "reef", "volume": {"value": 10.0, "unit": "gal_us"}},
            )

    assert response.status_code == 201
    assert mock_logger.info.call_count >= 2
    start_call = next(call for call in mock_logger.info.call_args_list if call.args[0] == "aquarium.create.start")
    assert start_call.kwargs["extra"]["request_id"] == "req-aquarium"
    assert start_call.kwargs["extra"]["aquarium_name"] == "Debug Tank"
    assert start_call.kwargs["extra"]["aquarium_type"] == "reef"
    assert start_call.kwargs["extra"]["volume_value"] == 10.0
    assert start_call.kwargs["extra"]["volume_unit"] == "gal_us"
    assert start_call.kwargs["extra"]["volume_liters"] == pytest.approx(37.85411784)
    assert start_call.kwargs["extra"]["owner_user_id"]

    success_call = next(call for call in mock_logger.info.call_args_list if call.args[0] == "aquarium.create.success")
    assert success_call.kwargs["extra"]["request_id"] == "req-aquarium"
    assert success_call.kwargs["extra"]["owner_user_id"] == start_call.kwargs["extra"]["owner_user_id"]
    assert success_call.kwargs["extra"]["aquarium_name"] == "Debug Tank"
    assert success_call.kwargs["extra"]["aquarium_id"]
