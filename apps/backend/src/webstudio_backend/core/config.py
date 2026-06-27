"""Environment-based configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "config/env/.env.local", "config/env/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_version: str = "0.1.0"
    api_version: str = "1.0"
    min_client_version: str = "0.1.0"

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    database_url: str = Field(
        default="postgresql+asyncpg://webstudio_app:webstudio_app@localhost:5432/webstudio_dev",
    )
    database_pool_size: int = 10
    database_echo: bool = False

    log_level: str = "DEBUG"
    log_json: bool = False

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"],
    )

    jwt_secret: str = Field(default="change-me-in-production")

    tls_cert_path: str = ""
    tls_key_path: str = ""
    tls_ca_path: str = ""

    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 100

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value  # type: ignore[return-value]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()
