"""Notification API error mapping."""

from __future__ import annotations

from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.repositories.exceptions import (
    NotificationAlreadyResolvedError,
    NotificationNotFoundError,
)


def raise_notification_error(exc: Exception) -> None:
    if isinstance(exc, NotificationNotFoundError):
        raise AppError(
            code="NOT_FOUND",
            message=str(exc),
            status_code=404,
        ) from exc
    if isinstance(exc, NotificationAlreadyResolvedError):
        raise AppError(
            code="NOTIFICATION_ALREADY_RESOLVED",
            message=str(exc),
            status_code=409,
        ) from exc
    raise exc
