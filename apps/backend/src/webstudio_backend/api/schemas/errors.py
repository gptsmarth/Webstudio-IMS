"""API error schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from webstudio_backend.api.schemas.responses import utc_now_iso

ErrorCode = Literal[
    "VALIDATION_ERROR",
    "INTERNAL_ERROR",
    "NOT_FOUND",
    "GONE",
    "NOT_CONFIGURED",
    "PERMISSION_DENIED",
    "INVALID_CREDENTIALS",
    "SERVICE_UNAVAILABLE",
    "RATE_LIMITED",
    "API_ERROR",
    "TIMEOUT",
    "QUOTA_EXCEEDED",
    "SERIAL_NUMBER_DUPLICATE",
    "SERIAL_NOT_FOUND",
    "PRODUCT_MODEL_ARCHIVED",
    "INVALID_STATUS_TRANSITION",
    "INVENTORY_ITEM_HAS_HISTORY",
    "SOLD_ITEM_CANNOT_MOVE",
    "USE_MOVEMENT_ENDPOINT",
    "ALREADY_SOLD",
    "SALE_ALREADY_CANCELLED",
    "SALE_CANCEL_NOT_ALLOWED",
    "NOTIFICATION_ALREADY_RESOLVED",
    "LOCATION_HAS_INVENTORY",
    "CATALOGUE_DELETE_BLOCKED",
    "SESSION_IDLE_TIMEOUT",
    "ALREADY_IMPORTED",
    "ALREADY_IGNORED",
]


class ErrorDetail(BaseModel):
    field: str | None = None
    code: ErrorCode | str
    message: str


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody
    request_id: str
    correlation_id: str
    timestamp: str = Field(default_factory=utc_now_iso)
