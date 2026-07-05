"""Sales API error mapping to standardized error envelope."""

from __future__ import annotations

from typing import NoReturn

from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.repositories.exceptions import (
    SaleAlreadyCancelledError,
    SaleCancelNotAllowedError,
    SaleNotFoundError,
)


def raise_sale_error(exc: Exception) -> NoReturn:
    """Map sale service errors to AppError with catalogue codes."""
    if isinstance(exc, SaleNotFoundError):
        raise AppError(
            "NOT_FOUND",
            "Sale not found.",
            status_code=404,
        ) from exc
    if isinstance(exc, SaleAlreadyCancelledError):
        raise AppError(
            "SALE_ALREADY_CANCELLED",
            "This sale has already been cancelled.",
            status_code=409,
        ) from exc
    if isinstance(exc, SaleCancelNotAllowedError):
        raise AppError(
            "SALE_CANCEL_NOT_ALLOWED",
            str(exc),
            status_code=422,
        ) from exc
    if isinstance(exc, ValueError):
        raise AppError(
            "VALIDATION_ERROR",
            str(exc),
            status_code=422,
        ) from exc
    raise exc
