from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.app import create_app
from src.config import Settings


@pytest.fixture
def auth_settings(tmp_path):
    return Settings(
        app_env="test",
        oauth_issuer_url="https://auth.example.com/application/o/aqualog",
        oauth_audience="test-client-id",
        test_database_url=f"sqlite+pysqlite:///{tmp_path}/test-aquarium-thresholds.db",
    )


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "x-request-id": "req-threshold"}


def _create_aquarium(client: TestClient, token: str) -> str:
    response = client.post(
        "/api/v1/aquariums",
        headers=_auth_header(token),
        json={"name": "Display Reef", "type": "reef", "volume": {"value": 200.0, "unit": "L"}},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def test_thresholds_require_authentication(auth_settings):
    app = create_app(auth_settings)

    with TestClient(app) as client:
        assert (
            client.put(
                "/api/v1/aquariums/aq-1/thresholds/salinity",
                json={"target": 35.0},
            ).status_code
            == 401
        )
        assert client.get("/api/v1/aquariums/aq-1/thresholds/salinity").status_code == 401


def test_set_and_get_thresholds_happy_path(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="threshold-owner", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            set_response = client.put(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/salinity",
                headers=_auth_header(token),
                json={"target": 35.0, "min": 33.0, "max": 37.0},
            )
            assert set_response.status_code == 200
            data = set_response.json()["data"]
            assert data["aquarium_id"] == aquarium_id
            assert data["parameter"] == "salinity"
            assert data["target"] == 35.0
            assert data["min"] == 33.0
            assert data["max"] == 37.0
            assert data["unit"] == "ppt"

            get_response = client.get(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/salinity",
                headers=_auth_header(token),
            )
            assert get_response.status_code == 200
            assert get_response.json()["data"]["target"] == 35.0


def test_partial_thresholds_are_accepted(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="threshold-partial", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            response = client.put(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/temperature",
                headers=_auth_header(token),
                json={"target": 25.0},
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["target"] == 25.0
            assert data["min"] is None
            assert data["max"] is None
            assert data["unit"] == "celsius"


def test_thresholds_for_non_owned_aquarium_are_rejected(
    create_valid_token, auth_settings, mock_jwks
):
    owner_token = create_valid_token(sub="threshold-owner-2", aud="test-client-id")
    other_token = create_valid_token(sub="threshold-other", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, owner_token)

            set_response = client.put(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/salinity",
                headers=_auth_header(other_token),
                json={"target": 35.0},
            )
            assert set_response.status_code == 404

            get_response = client.get(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/salinity",
                headers=_auth_header(other_token),
            )
            assert get_response.status_code == 404


def test_unsupported_threshold_parameter_is_rejected(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="threshold-unsupported", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            response = client.put(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/iron",
                headers=_auth_header(token),
                json={"target": 5.0},
            )
            assert response.status_code == 422


def test_threshold_parameter_path_is_case_insensitive(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="threshold-case", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            response = client.put(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/SaLiNiTy",
                headers=_auth_header(token),
                json={"target": 35.0},
            )
            assert response.status_code == 200
            assert response.json()["data"]["parameter"] == "salinity"


def test_threshold_ordering_validation_is_rejected(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="threshold-ordering", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            min_gt_target = client.put(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/salinity",
                headers=_auth_header(token),
                json={"min": 36.0, "target": 35.0, "max": 37.0},
            )
            assert min_gt_target.status_code == 422

            target_gt_max = client.put(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/salinity",
                headers=_auth_header(token),
                json={"min": 33.0, "target": 38.0, "max": 37.0},
            )
            assert target_gt_max.status_code == 422

            min_gt_max = client.put(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/salinity",
                headers=_auth_header(token),
                json={"min": 38.0, "max": 37.0},
            )
            assert min_gt_max.status_code == 422


@pytest.mark.parametrize(
    ("parameter", "field_value"),
    [
        ("salinity", {"target": 150.0}),
        ("phosphate", {"target": 150.0}),
        ("temperature", {"target": 50.0}),
        ("calcium", {"target": 1200.0}),
        ("ammonia", {"target": 60.0}),
        ("nitrite", {"target": 60.0}),
        ("nitrate", {"target": 600.0}),
        ("ph", {"target": 15.0}),
        ("alkalinity", {"target": 35.0}),
        ("magnesium", {"target": 2500.0}),
    ],
)
def test_out_of_range_threshold_values_are_rejected(
    create_valid_token, auth_settings, mock_jwks, parameter, field_value
):
    token = create_valid_token(sub=f"threshold-range-{parameter}", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            response = client.put(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/{parameter}",
                headers=_auth_header(token),
                json=field_value,
            )
            assert response.status_code == 422


def test_unconfigured_threshold_returns_200_with_nulls(
    create_valid_token, auth_settings, mock_jwks
):
    token = create_valid_token(sub="threshold-unconfigured", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            response = client.get(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/phosphate",
                headers=_auth_header(token),
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["target"] is None
            assert data["min"] is None
            assert data["max"] is None
            assert data["unit"] == "ppm"


def test_setting_thresholds_again_replaces_previous_values(
    create_valid_token, auth_settings, mock_jwks
):
    token = create_valid_token(sub="threshold-replace", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            first = client.put(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/phosphate",
                headers=_auth_header(token),
                json={"target": 0.05, "max": 0.1},
            )
            assert first.status_code == 200

            second = client.put(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/phosphate",
                headers=_auth_header(token),
                json={"target": 0.08, "min": 0.02, "max": 0.12},
            )
            assert second.status_code == 200
            data = second.json()["data"]
            assert data["target"] == 0.08
            assert data["min"] == 0.02
            assert data["max"] == 0.12

            get_response = client.get(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/phosphate",
                headers=_auth_header(token),
            )
            assert get_response.json()["data"]["target"] == 0.08


@pytest.mark.parametrize(
    ("parameter", "unit", "target"),
    [
        ("calcium", "ppm", 420.0),
        ("ammonia", "mg/L", 0.1),
        ("nitrite", "ppm", 0.1),
        ("nitrate", "ppm", 10.0),
        ("ph", "pH", 8.2),
        ("alkalinity", "dKH", 9.5),
        ("magnesium", "ppm", 1300.0),
    ],
)
def test_new_parameter_thresholds_set_and_get(
    create_valid_token, auth_settings, mock_jwks, parameter, unit, target
):
    token = create_valid_token(sub=f"threshold-{parameter}", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            set_response = client.put(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/{parameter}",
                headers=_auth_header(token),
                json={"target": target},
            )
            assert set_response.status_code == 200
            data = set_response.json()["data"]
            assert data["parameter"] == parameter
            assert data["target"] == target
            assert data["unit"] == unit

            get_response = client.get(
                f"/api/v1/aquariums/{aquarium_id}/thresholds/{parameter}",
                headers=_auth_header(token),
            )
            assert get_response.status_code == 200
            assert get_response.json()["data"]["target"] == target
            assert get_response.json()["data"]["unit"] == unit
