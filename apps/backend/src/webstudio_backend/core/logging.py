"""Structured logging configuration."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from webstudio_backend.core.config import Settings


def _json_sink(message: Any) -> None:
    record = message.record
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
        "extra": record["extra"],
    }
    sys.stdout.write(json.dumps(payload, default=str) + "\n")


def configure_logging(settings: Settings) -> None:
    logger.remove()
    if settings.log_json or settings.app_env == "production":
        logger.add(_json_sink, level=settings.log_level)
    else:
        logger.add(
            sys.stderr,
            level=settings.log_level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
        )
