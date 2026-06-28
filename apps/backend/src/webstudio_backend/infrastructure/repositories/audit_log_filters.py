"""Audit log search filter parameters."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from webstudio_backend.infrastructure.database.enums import AuditAction, AuditSource


@dataclass(frozen=True, slots=True)
class AuditLogSearchFilters:
    entity_type: str | None = None
    entity_id: str | None = None
    inventory_item_id: uuid.UUID | None = None
    serial_number: str | None = None
    product_model_id: uuid.UUID | None = None
    brand_id: int | None = None
    actor_user_id: int | None = None
    actor_role: str | None = None
    action: AuditAction | None = None
    source: AuditSource | None = None
    location_id: int | None = None
    invoice_number: str | None = None
    model_number: str | None = None
    search: str | None = None
    result: str | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None
