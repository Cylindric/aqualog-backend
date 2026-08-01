from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.app import create_app
from src.config import Settings

SEEDED_SLUGS = {
    "ppt",
    "sg",
    "celsius",
    "fahrenheit",
    "ppm",
    "mg_l",
    "ph",
    "dkh",
    "l",
    "gal_us",
}


@pytest.fixture
def auth_settings(tmp_path):
    return Settings(
        app_env="test",
        oauth_issuer_url="https://auth.example.com/application/o/aqualog",
        oauth_audience="test-client-id",
        test_database_url=f"sqlite+pysqlite:///{tmp_path}/test-units.db",
    )


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "x-request-id": "req-unit"}


def test_unit_endpoints_require_authentication(auth_settings):
    app = create_app(auth_settings)

    with TestClient(app) as client:
        assert (
            client.post(
                "/api/v1/units",
                json={"unit": "mol/L", "display_name": "Moles per Litre"},
            ).status_code
            == 401
        )
        assert (
            client.patch(
                "/api/v1/units/ppt",
                json={"display_name": "Parts per Thousand"},
            ).status_code
            == 401
        )
        assert client.delete("/api/v1/units/ppt").status_code == 401


def test_unit_endpoints_do_not_require_authentication(auth_settings):
    app = create_app(auth_settings)

    with TestClient(app) as client:
        assert client.get("/api/v1/units").status_code == 200
        assert client.get("/api/v1/units/ppt").status_code == 200


def test_list_units_returns_seeded_catalog(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="unit-catalog-lister", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            response = client.get("/api/v1/units", headers=_auth_header(token))
            assert response.status_code == 200
            slugs = {item["slug"] for item in response.json()["data"]}
            assert slugs == SEEDED_SLUGS
            units = {item["unit"] for item in response.json()["data"]}
            assert "mg/L" in units
            assert "pH" in units
            assert "dKH" in units


def test_get_unit_by_slug(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="unit-catalog-getter", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            response = client.get("/api/v1/units/ph", headers=_auth_header(token))
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["slug"] == "ph"
            assert data["unit"] == "pH"

            slash_unit = client.get("/api/v1/units/mg_l", headers=_auth_header(token))
            assert slash_unit.status_code == 200
            assert slash_unit.json()["data"]["unit"] == "mg/L"

            not_found = client.get("/api/v1/units/unobtainium", headers=_auth_header(token))
            assert not_found.status_code == 404


def test_create_unit_derives_slug_from_unit(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="unit-catalog-creator", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/units",
                headers=_auth_header(token),
                json={
                    "unit": " mol/L ",
                    "display_name": "Moles per Litre",
                    "description": "Molar concentration.",
                },
            )
            assert create_response.status_code == 201
            created = create_response.json()["data"]
            assert created["unit"] == "mol/L"
            assert created["slug"] == "mol_l"
            assert "/" not in created["slug"]
            assert created["display_name"] == "Moles per Litre"

            list_response = client.get("/api/v1/units", headers=_auth_header(token))
            slugs = {item["slug"] for item in list_response.json()["data"]}
            assert "mol_l" in slugs


def test_create_unit_that_derives_an_existing_slug_is_rejected(
    create_valid_token, auth_settings, mock_jwks
):
    token = create_valid_token(sub="unit-catalog-duplicate", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            duplicate = client.post(
                "/api/v1/units",
                headers=_auth_header(token),
                json={"unit": "PH", "display_name": "pH again"},
            )
            assert duplicate.status_code == 409


def test_create_unit_validation_errors(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="unit-catalog-validator", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            missing_display_name = client.post(
                "/api/v1/units",
                headers=_auth_header(token),
                json={"unit": "mol/L"},
            )
            assert missing_display_name.status_code == 422

            empty_unit = client.post(
                "/api/v1/units",
                headers=_auth_header(token),
                json={"unit": "   ", "display_name": "Moles per Litre"},
            )
            assert empty_unit.status_code == 422

            empty_display_name = client.post(
                "/api/v1/units",
                headers=_auth_header(token),
                json={"unit": "mol/L", "display_name": "   "},
            )
            assert empty_display_name.status_code == 422


def test_update_unit_editable_including_seeded_rows(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="unit-catalog-updater", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            response = client.patch(
                "/api/v1/units/ppt",
                headers=_auth_header(token),
                json={"display_name": "Parts per Thousand (Salinity)", "description": "Updated."},
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["slug"] == "ppt"
            assert data["display_name"] == "Parts per Thousand (Salinity)"
            assert data["description"] == "Updated."

            not_found = client.patch(
                "/api/v1/units/unobtainium",
                headers=_auth_header(token),
                json={"display_name": "Nope"},
            )
            assert not_found.status_code == 404


def test_update_unit_rejects_slug_or_unit_change(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="unit-catalog-slug-lock", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            slug_change = client.patch(
                "/api/v1/units/ppt",
                headers=_auth_header(token),
                json={"slug": "parts-per-thousand"},
            )
            assert slug_change.status_code == 422

            unit_change = client.patch(
                "/api/v1/units/ppt",
                headers=_auth_header(token),
                json={"unit": "parts-per-thousand"},
            )
            assert unit_change.status_code == 422


def test_delete_unreferenced_unit_succeeds(create_valid_token, auth_settings, mock_jwks):
    token = create_valid_token(sub="unit-catalog-deleter", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            client.post(
                "/api/v1/units",
                headers=_auth_header(token),
                json={"unit": "mol/L", "display_name": "Moles per Litre"},
            )

            deleted = client.delete("/api/v1/units/mol_l", headers=_auth_header(token))
            assert deleted.status_code == 200
            assert deleted.json()["data"] == {"slug": "mol_l", "deleted": True}

            not_found = client.get("/api/v1/units/mol_l", headers=_auth_header(token))
            assert not_found.status_code == 404

            missing_delete = client.delete("/api/v1/units/mol_l", headers=_auth_header(token))
            assert missing_delete.status_code == 404


def test_delete_unit_referenced_by_measurement_is_rejected(
    create_valid_token, auth_settings, mock_jwks
):
    token = create_valid_token(sub="unit-catalog-delete-blocked", aud="test-client-id")
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

            delete_response = client.delete("/api/v1/units/ppt", headers=_auth_header(token))
            assert delete_response.status_code == 409


def test_delete_unit_referenced_by_parameter_association_is_rejected(
    create_valid_token, auth_settings, mock_jwks
):
    token = create_valid_token(sub="unit-catalog-delete-assoc-blocked", aud="test-client-id")
    app = create_app(auth_settings)

    with patch("src.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            delete_response = client.delete("/api/v1/units/sg", headers=_auth_header(token))
            assert delete_response.status_code == 409
