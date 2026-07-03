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
    min_desktop_version: str = "0.1.0"
    min_mobile_version: str = "0.1.0"
    build_version: str = ""

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    mdns_enabled: bool = True
    mdns_server_name: str = ""

    database_url: str = Field(
        default="postgresql+asyncpg://webstudio_app:webstudio_app@localhost:5432/webstudio_dev",
    )
    database_pool_size: int = 10
    database_echo: bool = False

    log_level: str = "DEBUG"
    log_json: bool = False
    webstudio_log_dir: str = Field(default="", validation_alias="WEBSTUDIO_LOG_DIR")
    webstudio_crash_log_dir: str = Field(default="", validation_alias="WEBSTUDIO_CRASH_LOG_DIR")

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"],
    )

    jwt_secret: str = Field(default="change-me-in-production")
    jwt_issuer: str = "webstudio-ims"
    jwt_audience: str = "webstudio-ims-api"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    default_lockout_threshold: int = 5
    default_lockout_duration_minutes: int = 15

    tls_cert_path: str = ""
    tls_key_path: str = ""
    tls_ca_path: str = ""

    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 100
    slow_request_threshold_ms: int = 750

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    webstudio_data_root: str = Field(default="", validation_alias="WEBSTUDIO_DATA_ROOT")
    graceful_shutdown_seconds: int = Field(
        default=30, validation_alias="WEBSTUDIO_GRACEFUL_SHUTDOWN_SECONDS"
    )
    scheduler_state_persist_seconds: int = Field(
        default=60, validation_alias="WEBSTUDIO_SCHEDULER_PERSIST_SECONDS"
    )
    discovery_candidates: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["192.168.1.100", "webstudio-server.local"],
        validation_alias="WEBSTUDIO_DISCOVERY_CANDIDATES",
    )
    tally_connectivity_probe_seconds: int = Field(
        default=120,
        validation_alias="WEBSTUDIO_TALLY_CONNECTIVITY_PROBE_SECONDS",
    )
    release_catalog_root: str = Field(default="", validation_alias="WEBSTUDIO_RELEASE_CATALOG_ROOT")
    release_channel: str = Field(default="", validation_alias="WEBSTUDIO_RELEASE_CHANNEL")
    build_number: int = Field(default=1, validation_alias="WEBSTUDIO_BUILD_NUMBER")
    github_repo: str = Field(default="", validation_alias="WEBSTUDIO_GITHUB_REPO")
    github_token: str = Field(default="", validation_alias="WEBSTUDIO_GITHUB_TOKEN")
    release_sync_interval_seconds: int = Field(
        default=900,
        validation_alias="WEBSTUDIO_RELEASE_SYNC_INTERVAL_SECONDS",
    )
    release_updates_root: str = Field(default="", validation_alias="WEBSTUDIO_RELEASE_UPDATES_ROOT")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value  # type: ignore[return-value]

    @field_validator("discovery_candidates", mode="before")
    @classmethod
    def parse_discovery_candidates(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value  # type: ignore[return-value]

    def discovery_candidate_urls(self) -> list[str]:
        urls: list[str] = []
        for candidate in self.discovery_candidates:
            token = candidate.strip()
            if not token:
                continue
            if token.startswith("http://") or token.startswith("https://"):
                urls.append(token.rstrip("/"))
                continue
            host = token.split(":")[0]
            port = self.api_port
            if ":" in token and not token.startswith("["):
                _, maybe_port = token.rsplit(":", 1)
                if maybe_port.isdigit():
                    port = int(maybe_port)
            urls.append(f"http://{host}:{port}")
        return urls

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_staging(self) -> bool:
        return self.app_env == "staging"


@lru_cache
def get_settings() -> Settings:
    from webstudio_backend.core.version_catalog import load_version_catalog

    settings = Settings()
    catalog = load_version_catalog()
    overrides: dict[str, object] = {}
    if catalog.version:
        overrides["app_version"] = catalog.version
    if catalog.build_number > 0:
        overrides["build_number"] = catalog.build_number
    if catalog.release_channel:
        overrides["release_channel"] = catalog.release_channel
    if catalog.git_commit:
        overrides["build_version"] = catalog.git_commit
    if overrides:
        return settings.model_copy(update=overrides)
    return settings
