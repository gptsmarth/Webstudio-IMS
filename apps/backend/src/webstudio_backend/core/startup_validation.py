"""Startup configuration validation."""

from __future__ import annotations

from loguru import logger

from webstudio_backend.core.config import Settings


class ConfigurationError(Exception):
    """Raised when mandatory production configuration is invalid."""


def validate_startup_settings(settings: Settings) -> None:
    has_cert = bool(settings.tls_cert_path.strip())
    has_key = bool(settings.tls_key_path.strip())
    if has_cert != has_key or (settings.tls_required and not has_cert):
        raise ConfigurationError("TLS_CERT_PATH and TLS_KEY_PATH must be configured together.")

    if settings.app_env != "production":
        return

    secret_length = len(settings.jwt_secret.encode("utf-8"))
    if secret_length < 32:
        message = "Production JWT_SECRET must be at least 32 bytes."
        logger.error(message)
        raise ConfigurationError(message)

    if not has_cert:
        logger.warning(
            "The API listener uses plain HTTP. Set TLS_CERT_PATH and TLS_KEY_PATH "
            "for HTTPS and enable TLS_REQUIRED to enforce it at startup."
        )

    if not settings.rate_limit_enabled:
        logger.warning(
            "RATE_LIMIT_ENABLED is false. The API will accept requests from "
            "any reachable device with no throttling — enable it in production."
        )
