from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str
    api_version: str = "v1"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_prefix="AQUALOG_", extra="ignore")


def load_settings() -> Settings:
    """Load settings and fail fast when mandatory values are missing."""
    return Settings()
