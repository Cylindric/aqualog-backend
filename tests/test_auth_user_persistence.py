from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from aqualog_api.app import create_app
from aqualog_api.config import Settings


def test_first_login_creates_user_and_second_login_reuses_same_user(
    tmp_path,
    create_valid_token,
    mock_jwks,
):
    test_db_url = f"sqlite+pysqlite:///{tmp_path}/auth-persistence.db"
    settings = Settings(
        app_env="test",
        oauth_issuer_url="https://auth.example.com/application/o/aqualog",
        oauth_audience="test-client-id",
        test_database_url=test_db_url,
    )
    app = create_app(settings)
    token = create_valid_token(sub="persisted-user", aud="test-client-id")

    with patch("aqualog_api.auth.get_jwks_keys") as mock_get_keys:
        mock_get_keys.return_value = mock_jwks
        with TestClient(app) as client:
            first = client.get(
                "/api/v1/calculate/dose/salinity",
                params={"volume": 100.0, "current": 30.0, "target": 35.0},
                headers={"Authorization": f"Bearer {token}"},
            )
            second = client.get(
                "/api/v1/calculate/dose/salinity",
                params={"volume": 120.0, "current": 30.0, "target": 34.0},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert first.status_code == 200
    assert second.status_code == 200

    engine = create_engine(test_db_url, future=True)
    with engine.connect() as connection:
        count = connection.execute(
            text(
                "SELECT COUNT(*) FROM users WHERE oauth_issuer = :iss AND oauth_subject = :sub"
            ),
            {
                "iss": "https://auth.example.com/application/o/aqualog",
                "sub": "persisted-user",
            },
        ).scalar_one()

    assert count == 1
