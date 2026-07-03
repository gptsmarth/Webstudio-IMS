"""Structured logging configuration."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
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


def _add_file_sinks(settings: Settings) -> None:
    log_dir = settings.webstudio_log_dir.strip()
    if log_dir:
        path = Path(log_dir)
        path.mkdir(parents=True, exist_ok=True)
        logger.add(
            path / "webstudio-api.log",
            level=settings.log_level,
            rotation="10 MB",
            retention=5,
            enqueue=True,
            serialize=settings.log_json or settings.is_production,
        )

    crash_dir = settings.webstudio_crash_log_dir.strip()
    if crash_dir:
        path = Path(crash_dir)
        path.mkdir(parents=True, exist_ok=True)
        logger.add(
            path / "webstudio-crash.log",
            level="ERROR",
            rotation="5 MB",
            retention=10,
            enqueue=True,
            serialize=settings.log_json or settings.is_production,
        )


def configure_logging(settings: Settings) -> None:
    logger.remove()
    if settings.log_json or settings.is_production:
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
    _add_file_sinks(settings)
