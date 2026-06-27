"""Inventory item field validation."""

from __future__ import annotations

from webstudio_backend.infrastructure.database.enums import InventoryStatus
from webstudio_backend.infrastructure.repositories.exceptions import (
    InvalidFieldValueError,
    RequiredFieldError,
)

MAX_SERIAL_NUMBER_LENGTH = 128
MAX_COLOR_LENGTH = 64


def validate_serial_number(serial_number: str) -> str:
    if serial_number is None:
        raise RequiredFieldError("serial_number")

    normalized = serial_number.strip()
    if not normalized:
        raise RequiredFieldError("serial_number")
    if len(normalized) > MAX_SERIAL_NUMBER_LENGTH:
        raise InvalidFieldValueError(
            "serial_number",
            f"must be at most {MAX_SERIAL_NUMBER_LENGTH} characters",
        )
    return normalized


def validate_color(color: str) -> str:
    if color is None:
        raise RequiredFieldError("color")

    normalized = color.strip()
    if not normalized:
        raise RequiredFieldError("color")
    if len(normalized) > MAX_COLOR_LENGTH:
        raise InvalidFieldValueError("color", f"must be at most {MAX_COLOR_LENGTH} characters")
    return normalized


def validate_status(status: InventoryStatus) -> InventoryStatus:
    if not isinstance(status, InventoryStatus):
        raise InvalidFieldValueError("status", "invalid enum value")
    return status
