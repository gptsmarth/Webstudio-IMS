"""Inventory API error mapping to standardized error envelope."""

from __future__ import annotations

from typing import NoReturn

from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.repositories.exceptions import (
    ArchivedInventoryOperationError,
    DuplicateSerialNumberError,
    InactiveLocationError,
    InactiveProductModelError,
    InventoryAlreadySoldError,
    InventoryItemArchiveNotAllowedError,
    InventoryItemDeleteNotAllowedError,
    InventoryItemNotFoundError,
    InventoryNotAvailableForSaleError,
    LocationNotFoundError,
    RequiredFieldError,
    SameLocationMovementError,
    SoldItemCannotMoveError,
    UseLocationTransferEndpointError,
)


def raise_inventory_error(exc: Exception) -> NoReturn:
    """Map repository validation errors to AppError with catalogue codes."""
    if isinstance(exc, DuplicateSerialNumberError):
        raise AppError(
            "SERIAL_NUMBER_DUPLICATE",
            "Serial number already exists.",
            status_code=409,
        ) from exc
    if isinstance(exc, InventoryItemNotFoundError):
        raise AppError(
            "NOT_FOUND",
            "Inventory item not found.",
            status_code=404,
        ) from exc
    if isinstance(exc, InactiveProductModelError):
        raise AppError(
            "PRODUCT_MODEL_ARCHIVED",
            "Product model is not active.",
            status_code=422,
        ) from exc
    if isinstance(exc, InactiveLocationError):
        raise AppError(
            "VALIDATION_ERROR",
            "Location is not active.",
            status_code=422,
        ) from exc
    if isinstance(exc, LocationNotFoundError):
        raise AppError(
            "NOT_FOUND",
            "Location not found.",
            status_code=404,
        ) from exc
    if isinstance(exc, InventoryItemArchiveNotAllowedError):
        raise AppError(
            "INVALID_STATUS_TRANSITION",
            str(exc),
            status_code=409,
        ) from exc
    if isinstance(exc, InventoryItemDeleteNotAllowedError):
        raise AppError(
            "INVENTORY_ITEM_HAS_HISTORY",
            str(exc),
            status_code=409,
        ) from exc
    if isinstance(exc, ArchivedInventoryOperationError):
        raise AppError(
            "INVALID_STATUS_TRANSITION",
            str(exc),
            status_code=409,
        ) from exc
    if isinstance(exc, InventoryAlreadySoldError):
        raise AppError(
            "ALREADY_SOLD",
            "Inventory item is already sold.",
            status_code=409,
        ) from exc
    if isinstance(exc, InventoryNotAvailableForSaleError):
        raise AppError(
            "INVALID_STATUS_TRANSITION",
            "Inventory must be available to mark as sold.",
            status_code=422,
        ) from exc
    if isinstance(exc, SoldItemCannotMoveError):
        raise AppError(
            "SOLD_ITEM_CANNOT_MOVE",
            "Sold inventory item cannot be moved.",
            status_code=422,
        ) from exc
    if isinstance(exc, SameLocationMovementError):
        raise AppError(
            "VALIDATION_ERROR",
            "Source and destination locations must differ.",
            status_code=422,
        ) from exc
    if isinstance(exc, UseLocationTransferEndpointError):
        raise AppError(
            "USE_MOVEMENT_ENDPOINT",
            str(exc),
            status_code=422,
        ) from exc
    if isinstance(exc, RequiredFieldError):
        raise AppError(
            "VALIDATION_ERROR",
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
