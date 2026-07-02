"""Startup configuration validation."""

from __future__ import annotations

from loguru import logger

from webstudio_backend.core.config import Settings


class ConfigurationError(Exception):
    """Raised when mandatory production configuration is invalid."""


def validate_startup_settings(settings: Settings) -> None:
    if settings.app_env != "production":
        return

    secret_length = len(settings.jwt_secret.encode("utf-8"))
    if secret_length < 32:
        message = "Production JWT_SECRET must be at least 32 bytes."
        logger.error(message)
        raise ConfigurationError(message)
