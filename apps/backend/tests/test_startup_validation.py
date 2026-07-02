"""Production startup configuration validation tests."""

from __future__ import annotations

import pytest

from webstudio_backend.core.config import Settings
from webstudio_backend.core.startup_validation import ConfigurationError, validate_startup_settings


def test_production_requires_jwt_secret_at_least_32_bytes() -> None:
    settings = Settings(app_env="production", jwt_secret="too-short")
    with pytest.raises(ConfigurationError, match="Production JWT_SECRET must be at least 32 bytes"):
        validate_startup_settings(settings)


def test_production_accepts_32_byte_jwt_secret() -> None:
    settings = Settings(app_env="production", jwt_secret="x" * 32)
    validate_startup_settings(settings)


def test_development_allows_short_jwt_secret() -> None:
    settings = Settings(app_env="development", jwt_secret="short")
    validate_startup_settings(settings)


def test_test_environment_allows_short_jwt_secret() -> None:
    settings = Settings(app_env="test", jwt_secret="short")
    validate_startup_settings(settings)


def test_create_app_rejects_production_with_short_secret() -> None:
    from webstudio_backend.app import create_app

    settings = Settings(app_env="production", jwt_secret="short")
    with pytest.raises(ConfigurationError):
        create_app(settings)
