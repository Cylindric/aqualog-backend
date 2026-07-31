from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.app import create_app
from src.config import Settings

SEEDED_SLUGS = {
    "salinity",
    "phosphate",
    "temperature",
    "calcium",
    "ammonia",
    "nitrite",
    "nitrate",
    "ph",
    "alkalinity",
    "magnesium",
}


@pytest.fixture
def auth_settings(tmp_path):
    return Settings(
        app_env="test",
        oauth_issuer_url="https://auth.example.com/application/o/aqualog",
        oauth_audience="test-client-id",
        test_database_url=f"sqlite+pysqlite:///{tmp_path}/test-parameters.db",
    )


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "x-request-id": "req-parameter"}


def test_parameter_endpoints_require_authentication(auth_settings):
    app = create_app(auth_settings)

    with TestClient(app) as client:
        assert client.get("/api/v1/parameters").status_code == 401
        assert client.get("/api/v1/parameters/salinity").status_code == 401
        assert (
            client.post(
                "/api/v1/parameters",
                json={"slug": "iron", "display_name": "Iron"},
            ).status_code
            == 401
        )
        assert (
            client.patch(
                "/api/v1/parameters/salinity",
                json={"display_name": "Salinity"},
            ).status_code
            == 401
        )
        assert client.delete("/api/v1/parameters/salinity").status_code == 401


def test_list_parameters_returns_seeded_catalog(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="catalog-lister", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            response = client.get("/api/v1/parameters", headers=_auth_header(token))
            assert response.status_code == 200
            slugs = {item["slug"] for item in response.json()["data"]}
            assert slugs == SEEDED_SLUGS


def test_get_parameter_by_slug(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="catalog-getter", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            response = client.get("/api/v1/parameters/salinity", headers=_auth_header(token))
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["slug"] == "salinity"
            assert data["display_name"]

            not_found = client.get("/api/v1/parameters/unobtainium", headers=_auth_header(token))
            assert not_found.status_code == 404


def test_create_parameter_happy_path_and_normalization(
    create_valid_token, auth_settings, mock_jwks
):
    token = create_valid_token(sub="catalog-creator", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/parameters",
                headers=_auth_header(token),
                json={
                    "slug": " Iron ",
                    "display_name": "Iron",
                    "description": "Trace element for planted tanks.",
                },
            )
            assert create_response.status_code == 201
            created = create_response.json()["data"]
            assert created["slug"] == "iron"
            assert created["display_name"] == "Iron"

            list_response = client.get("/api/v1/parameters", headers=_auth_header(token))
            slugs = {item["slug"] for item in list_response.json()["data"]}
            assert "iron" in slugs


def test_create_parameter_duplicate_slug_is_rejected(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="catalog-duplicate", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            duplicate = client.post(
                "/api/v1/parameters",
                headers=_auth_header(token),
                json={"slug": "salinity", "display_name": "Salinity Again"},
            )
            assert duplicate.status_code == 409


def test_create_parameter_validation_errors(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="catalog-validator", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            missing_display_name = client.post(
                "/api/v1/parameters",
                headers=_auth_header(token),
                json={"slug": "iron"},
            )
            assert missing_display_name.status_code == 422

            empty_slug = client.post(
                "/api/v1/parameters",
                headers=_auth_header(token),
                json={"slug": "   ", "display_name": "Iron"},
            )
            assert empty_slug.status_code == 422

            empty_display_name = client.post(
                "/api/v1/parameters",
                headers=_auth_header(token),
                json={"slug": "iron", "display_name": "   "},
            )
            assert empty_display_name.status_code == 422


def test_update_parameter_editable_including_seeded_rows(
    create_valid_token, auth_settings, mock_jwks
):
    token = create_valid_token(sub="catalog-updater", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            response = client.patch(
                "/api/v1/parameters/salinity",
                headers=_auth_header(token),
                json={"display_name": "Salinity (Salt Content)", "description": "Updated."},
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["slug"] == "salinity"
            assert data["display_name"] == "Salinity (Salt Content)"
            assert data["description"] == "Updated."

            not_found = client.patch(
                "/api/v1/parameters/unobtainium",
                headers=_auth_header(token),
                json={"display_name": "Nope"},
            )
            assert not_found.status_code == 404


def test_update_parameter_rejects_slug_change(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="catalog-slug-lock", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            response = client.patch(
                "/api/v1/parameters/salinity",
                headers=_auth_header(token),
                json={"slug": "salt"},
            )
            assert response.status_code == 422


def test_delete_unreferenced_parameter_succeeds(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="catalog-deleter", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            client.post(
                "/api/v1/parameters",
                headers=_auth_header(token),
                json={"slug": "iron", "display_name": "Iron"},
            )

            deleted = client.delete("/api/v1/parameters/iron", headers=_auth_header(token))
            assert deleted.status_code == 200
            assert deleted.json()["data"] == {"slug": "iron", "deleted": True}

            not_found = client.get("/api/v1/parameters/iron", headers=_auth_header(token))
            assert not_found.status_code == 404

            missing_delete = client.delete("/api/v1/parameters/iron", headers=_auth_header(token))
            assert missing_delete.status_code == 404


def test_delete_parameter_referenced_by_measurement_is_rejected(
    create_valid_token, auth_settings, mock_jwks
):
    token = create_valid_token(sub="catalog-delete-blocked", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            aquarium_response = client.post(
                "/api/v1/aquariums",
                headers=_auth_header(token),
                json={
                    "name": "Display Reef",
                    "type": "reef",
                    "volume": {"value": 100.0, "unit": "L"},
                },
            )
            aquarium_id = aquarium_response.json()["data"]["id"]

            measurement_response = client.post(
                f"/api/v1/aquariums/{aquarium_id}/measurements/salinity",
                headers=_auth_header(token),
                json={"unit": "ppt", "value": 35.0, "measured_at": "2026-07-01T12:00:00Z"},
            )
            assert measurement_response.status_code == 201

            delete_response = client.delete(
                "/api/v1/parameters/salinity", headers=_auth_header(token)
            )
            assert delete_response.status_code == 409
