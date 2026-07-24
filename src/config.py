from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    app_env: str
    app_version: str = "0.0.0"
    api_version: str = "v1"
    log_level: str = "INFO"
    test_reports_dir: str = "artifacts/tests"
    coverage_reports_dir: str = "artifacts/coverage"
    oauth_issuer_url: str | None = None
    oauth_audience: str | None = None
    oauth_client_id: str | None = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "aqualog"
    db_password: SecretStr = SecretStr("")
    db_name: str = "aqualog"
    test_database_url: str = "sqlite+pysqlite:///:memory:"

    model_config = SettingsConfigDict(env_prefix="AQUALOG_", extra="ignore")

    @model_validator(mode="after")
    def set_oauth_audience_fallback(self) -> "Settings":
        # Preserve compatibility with existing env files that use CLIENT_ID.
        if not self.oauth_audience and self.oauth_client_id:
            self.oauth_audience = self.oauth_client_id
        return self

    @property
    def database_url(self) -> str:
        return URL.create(
            drivername="postgresql",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)


def load_settings() -> Settings:
    """Load settings and fail fast when mandatory values are missing."""
    return Settings()  # type: ignore[call-arg]  # fields resolved from env vars, not visible to mypy
