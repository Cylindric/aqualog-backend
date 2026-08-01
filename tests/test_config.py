import pytest
from pydantic import ValidationError

from src.config import Settings, ensure_auth_mode_configured


def test_auth_mode_defaults_to_oauth():
    settings = Settings(app_env="test")

    assert settings.auth_mode == "oauth"


def test_unsupported_auth_mode_is_rejected():
    with pytest.raises(ValidationError):
        Settings(app_env="test", auth_mode="invalid")


def test_settings_construction_does_not_require_auth_config():
    # Settings() is also constructed by tooling unrelated to serving requests
    # (e.g. alembic/env.py, which only needs DB config) - it must stay
    # constructible without any auth_mode-specific config.
    settings = Settings(app_env="test")

    assert settings.oauth_issuer_url is None
    assert settings.auth_impersonate_user_id is None


def test_ensure_auth_mode_configured_requires_issuer_url_for_oauth_mode():
    settings = Settings(app_env="test", auth_mode="oauth", oauth_audience="test-client-id")

    with pytest.raises(RuntimeError):
        ensure_auth_mode_configured(settings)


def test_ensure_auth_mode_configured_requires_audience_for_oauth_mode():
    settings = Settings(
        app_env="test",
        auth_mode="oauth",
        oauth_issuer_url="https://auth.example.com/application/o/aqualog",
    )

    with pytest.raises(RuntimeError):
        ensure_auth_mode_configured(settings)


def test_ensure_auth_mode_configured_succeeds_for_oauth_mode_with_required_config():
    settings = Settings(
        app_env="test",
        auth_mode="oauth",
        oauth_issuer_url="https://auth.example.com/application/o/aqualog",
        oauth_audience="test-client-id",
    )

    ensure_auth_mode_configured(settings)  # does not raise


def test_ensure_auth_mode_configured_requires_impersonation_user_id_for_none_mode():
    settings = Settings(app_env="test", auth_mode="none")

    with pytest.raises(RuntimeError):
        ensure_auth_mode_configured(settings)


def test_ensure_auth_mode_configured_rejects_blank_impersonation_user_id():
    settings = Settings(app_env="test", auth_mode="none", auth_impersonate_user_id="")

    with pytest.raises(RuntimeError):
        ensure_auth_mode_configured(settings)


def test_ensure_auth_mode_configured_succeeds_for_none_mode_with_user_id():
    settings = Settings(app_env="test", auth_mode="none", auth_impersonate_user_id="some-user-id")

    ensure_auth_mode_configured(settings)  # does not raise
