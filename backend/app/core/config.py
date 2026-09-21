"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "Vehicle Master Tracker"
    log_level: str = "INFO"
    auth_enabled: bool = True
    # Comma-separated entries: user_id:api_key:role
    auth_users: str = ""
    jwt_secret_key: str = "vehicle-tracker-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)
    default_user_password: str = "test"

    database_url: str = (
        "postgresql+asyncpg://vehicle_user:vehicle_password@localhost:5432/vehicle_master"
    )

    cors_origins: str = "http://localhost:3000"

    max_page_size: int = Field(default=100, ge=1)
    default_page_size: int = Field(default=10, ge=1)
    excel_max_file_size_mb: int = Field(default=50, ge=1)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _normalize_origins(cls, value: str) -> str:
        if isinstance(value, list):
            return ",".join(str(item) for item in value)
        return str(value)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def excel_max_file_size_bytes(self) -> int:
        return self.excel_max_file_size_mb * 1024 * 1024

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local", "test"}

    @property
    def jwt_expire_minutes(self) -> int:
        return self.access_token_expire_minutes

    @property
    def configured_users(self) -> dict[str, tuple[str, str]]:
        users: dict[str, tuple[str, str]] = {}
        for entry in self.auth_users.split(","):
            parts = [part.strip() for part in entry.split(":", 2)]
            if len(parts) == 3 and all(parts):
                users[parts[0]] = (parts[1], parts[2].lower())
        return users


@lru_cache
def get_settings() -> Settings:
    return Settings()
