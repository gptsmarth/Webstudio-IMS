"""Audit log API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from webstudio_backend.infrastructure.database.enums import AuditAction
from webstudio_backend.infrastructure.database.models.audit_log import AuditLog


class AuditLogEntry(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: str
    inventory_item_id: uuid.UUID | None = None
    actor_user_id: int | None = None
    actor_display_name: str | None = None
    actor_role: str | None = None
    action: AuditAction
    field_name: str | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    description: str | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, audit_log: AuditLog) -> AuditLogEntry:
        return cls(
            id=audit_log.id,
            entity_type=audit_log.entity_type,
            entity_id=audit_log.entity_id,
            inventory_item_id=audit_log.inventory_item_id,
            actor_user_id=audit_log.actor_user_id,
            actor_display_name=audit_log.actor_display_name,
            actor_role=audit_log.actor_role,
            action=audit_log.action,
            field_name=audit_log.field_name,
            old_value=audit_log.old_value,
            new_value=audit_log.new_value,
            description=audit_log.description,
            created_at=audit_log.created_at,
        )


class AuditLogSearchQuery(BaseModel):
    entity_type: str | None = None
    entity_id: str | None = None
    inventory_item_id: uuid.UUID | None = None
    serial_number: str | None = None
    product_model_id: uuid.UUID | None = None
    brand_id: int | None = None
    actor_user_id: int | None = None
    action: AuditAction | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
