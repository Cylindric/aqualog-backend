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
        test_database_url=f"sqlite+pysqlite:///{tmp_path}/test-aquarium-measurements.db",
    )


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "x-request-id": "req-measure"}


def _create_aquarium(client: TestClient, token: str) -> str:
    response = client.post(
        "/api/v1/aquariums",
        headers=_auth_header(token),
        json={"name": "Display Reef", "type": "reef", "volume": {"value": 200.0, "unit": "L"}},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def test_salinity_measurements_require_authentication(auth_settings):
    app = create_app(auth_settings)

    with TestClient(app) as client:
        assert client.post(
            "/api/v1/aquariums/aq-1/measurements/salinity",
            json={"unit": "ppt", "value": 35.0, "measured_at": "2026-07-01T12:00:00Z"},
        ).status_code == 401
        assert client.get("/api/v1/aquariums/aq-1/measurements/salinity").status_code == 401


def test_salinity_measurement_create_list_happy_path(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="measure-owner", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            create_response = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
                json={"unit": "sg", "value": 1.026, "measured_at": "2026-07-01T12:00:00.987654Z"},
            )
            assert create_response.status_code == 201
            created = create_response.json()["data"]
            assert created["parameter"] == "salinity"
            assert created["unit"] == "ppt"
            assert created["value"] == pytest.approx(34.46976)
            assert created["raw_unit"] == "sg"
            assert created["raw_value"] == pytest.approx(1.026)
            assert created["measured_at"].endswith("+00:00")
            assert "." not in created["measured_at"]

            second_response = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
                json={"unit": "ppt", "value": 35.5, "measured_at": "2026-07-01T12:05:00Z"},
            )
            assert second_response.status_code == 201

            list_response = client.get(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
            )
            assert list_response.status_code == 200
            payload = list_response.json()
            assert isinstance(payload["data"], list)
            assert "pagination" not in payload
            assert [item["measured_at"] for item in payload["data"]] == [
                "2026-07-01T12:00:00+00:00",
                "2026-07-01T12:05:00+00:00",
            ]

            filtered = client.get(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
                params={"from": "2026-07-01T12:01:00Z"},
            )
            assert filtered.status_code == 200
            assert len(filtered.json()["data"]) == 1
            assert filtered.json()["data"][0]["measured_at"] == "2026-07-01T12:05:00+00:00"


def test_salinity_measurement_duplicate_timestamp_and_cross_user(create_valid_token, auth_settings, mock_jwks):
    owner_token = create_valid_token(sub="owner", aud="test-client-id")
    other_token = create_valid_token(sub="other", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, owner_token)

            created = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(owner_token),
                json={"unit": "ppt", "value": 35.0, "measured_at": "2026-07-01T12:00:00.950000Z"},
            )
            assert created.status_code == 201

            duplicate = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(owner_token),
                json={"unit": "sg", "value": 1.026, "measured_at": "2026-07-01T12:00:00.100000Z"},
            )
            assert duplicate.status_code == 409

            assert client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(other_token),
                json={"unit": "ppt", "value": 35.0, "measured_at": "2026-07-01T12:01:00Z"},
            ).status_code == 404

            assert client.get(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(other_token),
            ).status_code == 404


def test_salinity_measurement_validation_errors(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="validator", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            unsupported_unit = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
                json={"unit": "psu", "value": 35.0, "measured_at": "2026-07-01T12:00:00Z"},
            )
            assert unsupported_unit.status_code == 422

            invalid_sg = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
                json={"unit": "sg", "value": 1.2, "measured_at": "2026-07-01T12:00:00Z"},
            )
            assert invalid_sg.status_code == 422

            missing_field = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
                json={"unit": "ppt", "value": 35.0},
            )
            assert missing_field.status_code == 422

            missing_timezone = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
                json={"unit": "ppt", "value": 35.0, "measured_at": "2026-07-01T12:00:00"},
            )
            assert missing_timezone.status_code == 422


def test_measurement_create_phosphate_happy_path_with_parameter_normalization(
    create_valid_token,
    auth_settings,
    mock_jwks,
):
    token = create_valid_token(sub="phosphate-owner", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            create_response = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/PhOsPhAtE",
                headers=_auth_header(token),
                json={
                    "unit": "PPM",
                    "value": 0.08,
                    "measured_at": "2026-07-01T12:00:00.987654Z",
                },
            )
            assert create_response.status_code == 201
            created = create_response.json()["data"]
            assert created["parameter"] == "phosphate"
            assert created["unit"] == "ppm"
            assert created["raw_unit"] == "ppm"
            assert created["value"] == pytest.approx(0.08)
            assert created["raw_value"] == pytest.approx(0.08)
            assert created["measured_at"] == "2026-07-01T12:00:00+00:00"


def test_measurement_create_phosphate_validation_and_duplicate_errors(
    create_valid_token,
    auth_settings,
    mock_jwks,
):
    token = create_valid_token(sub="phosphate-validator", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            unsupported_unit = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/phosphate",
                headers=_auth_header(token),
                json={
                    "unit": "mg/L",
                    "value": 0.08,
                    "measured_at": "2026-07-01T12:00:00Z",
                },
            )
            assert unsupported_unit.status_code == 422

            invalid_value = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/phosphate",
                headers=_auth_header(token),
                json={
                    "unit": "ppm",
                    "value": 101.0,
                    "measured_at": "2026-07-01T12:00:00Z",
                },
            )
            assert invalid_value.status_code == 422

            created = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/phosphate",
                headers=_auth_header(token),
                json={
                    "unit": "ppm",
                    "value": 0.08,
                    "measured_at": "2026-07-01T12:00:00.950000Z",
                },
            )
            assert created.status_code == 201

            duplicate = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/PHOSPHATE",
                headers=_auth_header(token),
                json={
                    "unit": "ppm",
                    "value": 0.09,
                    "measured_at": "2026-07-01T12:00:00.100000Z",
                },
            )
            assert duplicate.status_code == 409


def test_measurement_history_path_parameter_returns_selected_parameter_only(
    create_valid_token,
    auth_settings,
    mock_jwks,
):
    token = create_valid_token(sub="history-owner", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            salinity = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
                json={"unit": "ppt", "value": 35.0, "measured_at": "2026-07-01T12:00:00Z"},
            )
            assert salinity.status_code == 201

            phosphate = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/phosphate",
                headers=_auth_header(token),
                json={
                    "unit": "ppm",
                    "value": 0.08,
                    "measured_at": "2026-07-01T12:05:00Z",
                },
            )
            assert phosphate.status_code == 201

            salinity_results = client.get(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
            )
            assert salinity_results.status_code == 200
            assert [row["parameter"] for row in salinity_results.json()["data"]] == ["salinity"]

            phosphate_only = client.get(
                f"/api/v1/aquariums/{aquarium_id}/measurements/phosphate",
                headers=_auth_header(token),
            )
            assert phosphate_only.status_code == 200
            assert len(phosphate_only.json()["data"]) == 1
            assert phosphate_only.json()["data"][0]["parameter"] == "phosphate"

            phosphate_filtered = client.get(
                f"/api/v1/aquariums/{aquarium_id}/measurements/phosphate",
                headers=_auth_header(token),
                params={"from": "2026-07-01T12:06:00Z"},
            )
            assert phosphate_filtered.status_code == 200
            assert phosphate_filtered.json()["data"] == []


def test_measurement_routes_reject_unsupported_path_parameter(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="history-filter", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            unsupported_create = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/temperature",
                headers=_auth_header(token),
                json={"unit": "c", "value": 25.0, "measured_at": "2026-07-01T12:00:00Z"},
            )
            assert unsupported_create.status_code == 422

            unsupported_get = client.get(
                f"/api/v1/aquariums/{aquarium_id}/measurements/temperature",
                headers=_auth_header(token),
            )
            assert unsupported_get.status_code == 422


def test_measurement_routes_accept_mixed_case_path_aliases(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="mixed-case", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            created = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/SaLiNiTy",
                headers=_auth_header(token),
                json={"unit": "ppt", "value": 35.0, "measured_at": "2026-07-01T12:00:00Z"},
            )
            assert created.status_code == 201
            assert created.json()["data"]["parameter"] == "salinity"

            listed = client.get(
                f"/api/v1/aquariums/{aquarium_id}/measurements/sALiNITY",
                headers=_auth_header(token),
            )
            assert listed.status_code == 200
            assert len(listed.json()["data"]) == 1
            assert listed.json()["data"][0]["parameter"] == "salinity"


def test_legacy_generic_measurement_routes_are_obsolete(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="legacy-routes", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            post_response = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements",
                headers=_auth_header(token),
                json={"unit": "ppt", "value": 35.0, "measured_at": "2026-07-01T12:00:00Z"},
            )
            assert post_response.status_code == 404

            get_response = client.get(
                f"/api/v1/aquariums/{aquarium_id}/measurements",
                headers=_auth_header(token),
            )
            assert get_response.status_code == 404


def test_measurement_delete_by_parameter_and_id(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="delete-owner", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, token)

            created = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
                json={"unit": "ppt", "value": 35.0, "measured_at": "2026-07-01T12:00:00Z"},
            )
            assert created.status_code == 201
            measurement_id = created.json()["data"]["id"]

            deleted = client.delete(
                f"/api/v1/aquariums/{aquarium_id}/measurements/SALINITY/{measurement_id}",
                headers=_auth_header(token),
            )
            assert deleted.status_code == 200
            assert deleted.json()["data"] == {"id": measurement_id, "deleted": True}

            after_delete = client.get(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
            )
            assert after_delete.status_code == 200
            assert after_delete.json()["data"] == []


def test_measurement_delete_not_found_and_cross_user(create_valid_token, auth_settings, mock_jwks):
    owner_token = create_valid_token(sub="delete-owner", aud="test-client-id")
    other_token = create_valid_token(sub="delete-other", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_id = _create_aquarium(client, owner_token)

            created = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/phosphate",
                headers=_auth_header(owner_token),
                json={"unit": "ppm", "value": 0.08, "measured_at": "2026-07-01T12:00:00Z"},
            )
            assert created.status_code == 201
            measurement_id = created.json()["data"]["id"]

            wrong_parameter = client.delete(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity/{measurement_id}",
                headers=_auth_header(owner_token),
            )
            assert wrong_parameter.status_code == 404

            unknown_measurement = client.delete(
                f"/api/v1/aquariums/{aquarium_id}/measurements/phosphate/not-a-real-id",
                headers=_auth_header(owner_token),
            )
            assert unknown_measurement.status_code == 404

            cross_user = client.delete(
                f"/api/v1/aquariums/{aquarium_id}/measurements/phosphate/{measurement_id}",
                headers=_auth_header(other_token),
            )
            assert cross_user.status_code == 404
