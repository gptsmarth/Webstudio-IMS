"""Catalogue deletion API error mapping."""

from __future__ import annotations

from typing import NoReturn

from webstudio_backend.api.schemas.errors import ErrorDetail
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.repositories.exceptions import (
    BrandHasDependenciesError,
    LocationHasInventoryError,
    LocationNotFoundError,
    ProductModelHasInventoryError,
    SameLocationMovementError,
)


def raise_catalogue_deletion_error(exc: Exception) -> NoReturn:
    if isinstance(exc, BrandHasDependenciesError):
        raise AppError(
            "CATALOGUE_DELETE_BLOCKED",
            str(exc),
            status_code=409,
            details=[
                ErrorDetail(
                    field="product_model_count",
                    code="CATALOGUE_DELETE_BLOCKED",
                    message=str(exc.product_model_count),
                ),
                ErrorDetail(
                    field="inventory_count",
                    code="CATALOGUE_DELETE_BLOCKED",
                    message=str(exc.inventory_count),
                ),
            ],
        ) from exc
    if isinstance(exc, ProductModelHasInventoryError):
        raise AppError(
            "CATALOGUE_DELETE_BLOCKED",
            str(exc),
            status_code=409,
            details=[
                ErrorDetail(
                    field="inventory_count",
                    code="CATALOGUE_DELETE_BLOCKED",
                    message=str(exc.inventory_count),
                ),
            ],
        ) from exc
    if isinstance(exc, LocationHasInventoryError):
        raise AppError(
            "LOCATION_HAS_INVENTORY",
            str(exc),
            status_code=409,
            details=[
                ErrorDetail(
                    field="inventory_count",
                    code="LOCATION_HAS_INVENTORY",
                    message=str(exc.movable_count),
                ),
            ],
        ) from exc
    if isinstance(exc, LocationNotFoundError):
        raise AppError("NOT_FOUND", str(exc), status_code=404) from exc
    if isinstance(exc, SameLocationMovementError):
        raise AppError("VALIDATION_ERROR", str(exc), status_code=422) from exc
    raise exc
