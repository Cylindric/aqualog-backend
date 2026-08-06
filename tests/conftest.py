import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from joserfc import jwk, jwt
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db import reset_database  # noqa: E402

# Several repository-level tests build their own throwaway SQLAlchemy engine
# directly (bypassing src.db's engine singleton, which reset_db_state below
# already tears down) and never closed/disposed it, leaking a real sqlite
# connection per test until garbage collection - surfacing as "ResourceWarning:
# unclosed database" at session end. register_engine_for_cleanup lets those
# tests' helper functions opt in to teardown without needing a fixture
# threaded through every call site.
_pending_engine_cleanup: list[tuple[Session, Engine]] = []


def register_engine_for_cleanup(session: Session, engine: Engine) -> None:
    _pending_engine_cleanup.append((session, engine))


@pytest.fixture(autouse=True)
def _dispose_registered_test_engines():
    yield
    while _pending_engine_cleanup:
        session, engine = _pending_engine_cleanup.pop()
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def strip_ambient_aqualog_env(monkeypatch):
    """Tests construct Settings(...) from explicit kwargs and assume no other
    AQUALOG_* config is present. But Task's `dotenv: [../.env]` loads the real
    dev/prod .env into the process environment for every `task` invocation, so
    e.g. AQUALOG_OAUTH_ISSUER_URL/AQUALOG_OAUTH_AUDIENCE leak in via
    pydantic-settings and silently make settings "configured" when a test
    expects them not to be. Strip all ambient AQUALOG_* vars before each test
    so Settings() only ever sees what the test explicitly provides.
    """
    for key in list(os.environ):
        if key.startswith("AQUALOG_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def reset_db_state():
    reset_database()
    yield
    reset_database()


# Mock JWKS and JWT for testing
@pytest.fixture
def mock_rsa_keys():
    """Generate mock RSA keys for testing."""
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import rsa

    backend = default_backend()
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=backend,
    )
    public_key = private_key.public_key()

    return {"private": private_key, "public": public_key}


@pytest.fixture
def mock_jwks(mock_rsa_keys):
    """Generate mock JWKS for testing."""
    public_key = mock_rsa_keys["public"]
    public_jwk = jwk.import_key(
        public_key,
        "RSA",
        parameters={"kid": "test-key-1", "use": "sig", "alg": "RS256"},
    )
    return jwk.KeySet([public_jwk]).as_dict()


@pytest.fixture
def mock_oidc_config(mock_jwks):
    """Generate mock OIDC discovery configuration."""
    return {
        "issuer": "https://auth.example.com/application/o/aqualog",
        "jwks_uri": "https://auth.example.com/application/o/aqualog/.well-known/jwks.json",
        "token_endpoint": "https://auth.example.com/application/o/aqualog/token/",
        "authorization_endpoint": "https://auth.example.com/application/o/aqualog/authorize/",
    }


@pytest.fixture
def create_valid_token(mock_rsa_keys, mock_oidc_config):
    """Factory fixture to create valid JWT tokens for testing."""

    def _create_token(
        sub: str = "test-user",
        aud: str = "test-client-id",
        exp_offset_seconds: int = 3600,
        issuer: str | None = None,
        preferred_username: str | None = None,
        groups: list[str] | None = None,
    ) -> str:
        private_key = jwk.import_key(
            mock_rsa_keys["private"],
            "RSA",
            parameters={"kid": "test-key-1", "use": "sig", "alg": "RS256"},
        )

        claims = {
            "sub": sub,
            "aud": aud,
            "iss": issuer or mock_oidc_config["issuer"],
            "exp": datetime.now(timezone.utc) + timedelta(seconds=exp_offset_seconds),
            "iat": datetime.now(timezone.utc),
        }
        if preferred_username is not None:
            claims["preferred_username"] = preferred_username
        if groups is not None:
            claims["groups"] = groups

        return jwt.encode({"alg": "RS256", "kid": "test-key-1"}, claims, private_key)

    return _create_token


@pytest.fixture
def create_expired_token(mock_rsa_keys, mock_oidc_config):
    """Factory fixture to create expired JWT tokens for testing."""

    def _create_token(
        sub: str = "test-user",
        aud: str = "test-client-id",
    ) -> str:
        private_key = jwk.import_key(
            mock_rsa_keys["private"],
            "RSA",
            parameters={"kid": "test-key-1", "use": "sig", "alg": "RS256"},
        )

        claims = {
            "sub": sub,
            "aud": aud,
            "iss": mock_oidc_config["issuer"],
            "exp": datetime.now(timezone.utc) - timedelta(seconds=3600),  # Expired 1 hour ago
            "iat": datetime.now(timezone.utc) - timedelta(seconds=7200),
        }

        return jwt.encode({"alg": "RS256", "kid": "test-key-1"}, claims, private_key)

    return _create_token
