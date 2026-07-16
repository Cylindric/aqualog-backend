import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from authlib.jose import JsonWebToken

from aqualog_api.db import reset_database

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def reset_db_state():
    reset_database()
    yield
    reset_database()


# Mock JWKS and JWT for testing
@pytest.fixture
def mock_rsa_keys():
    """Generate mock RSA keys for testing."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

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
    from authlib.jose import JsonWebKey
    from cryptography.hazmat.primitives import serialization
    
    public_key = mock_rsa_keys["public"]
    
    # Export public key in PEM format and reimport through authlib
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    
    jwk = JsonWebKey.import_key(pem)
    jwk_data = jwk.as_dict()
    jwk_data["kid"] = "test-key-1"
    jwk_data["use"] = "sig"
    jwk_data["alg"] = "RS256"

    return {"keys": [jwk_data]}


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
    ) -> str:
        jwt = JsonWebToken(algorithms=["RS256"])
        private_key = mock_rsa_keys["private"]

        claims = {
            "sub": sub,
            "aud": aud,
            "iss": mock_oidc_config["issuer"],
            "exp": datetime.now(timezone.utc) + timedelta(seconds=exp_offset_seconds),
            "iat": datetime.now(timezone.utc),
        }

        token = jwt.encode({"alg": "RS256"}, claims, private_key)
        return token.decode() if isinstance(token, bytes) else token

    return _create_token


@pytest.fixture
def create_expired_token(mock_rsa_keys, mock_oidc_config):
    """Factory fixture to create expired JWT tokens for testing."""

    def _create_token(
        sub: str = "test-user",
        aud: str = "test-client-id",
    ) -> str:
        jwt = JsonWebToken(algorithms=["RS256"])
        private_key = mock_rsa_keys["private"]

        claims = {
            "sub": sub,
            "aud": aud,
            "iss": mock_oidc_config["issuer"],
            "exp": datetime.now(timezone.utc) - timedelta(seconds=3600),  # Expired 1 hour ago
            "iat": datetime.now(timezone.utc) - timedelta(seconds=7200),
        }

        token = jwt.encode({"alg": "RS256"}, claims, private_key)
        return token.decode() if isinstance(token, bytes) else token

    return _create_token

