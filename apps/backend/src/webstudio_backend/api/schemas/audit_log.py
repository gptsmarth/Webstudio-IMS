"""Audit log API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from webstudio_backend.infrastructure.database.enums import AuditAction, AuditSource
from webstudio_backend.infrastructure.database.models.audit_log import AuditLog
from webstudio_backend.infrastructure.repositories.audit_log_repository import AuditLogEnrichedRow
from webstudio_backend.services.audit_log_presenter import (
    audit_module,
    audit_operation,
    audit_result,
    audit_severity,
    extract_security_event,
    extract_correlation_id,
    extract_invoice_number,
    extract_location_name,
    extract_request_id,
    related_tally_sync,
)


class AuditLogEntry(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: str
    inventory_item_id: uuid.UUID | None = None
    actor_user_id: int | None = None
    actor_display_name: str | None = None
    actor_role: str | None = None
    action: AuditAction
    source: AuditSource
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
            source=audit_log.source,
            field_name=audit_log.field_name,
            old_value=audit_log.old_value,
            new_value=audit_log.new_value,
            description=audit_log.description,
            created_at=audit_log.created_at,
        )


class AuditLogListEntry(AuditLogEntry):
    module: str
    operation: str
    serial_number: str | None = None
    location_name: str | None = None
    invoice_number: str | None = None
    model_number: str | None = None
    result: str
    severity: str
    security_event: str | None = None

    @classmethod
    def from_enriched(cls, row: AuditLogEnrichedRow) -> AuditLogListEntry:
        audit_log = row.audit_log
        base = AuditLogEntry.from_model(audit_log)
        return cls(
            **base.model_dump(),
            module=audit_module(audit_log.entity_type),
            operation=audit_operation(audit_log.action),
            serial_number=row.serial_number,
            location_name=extract_location_name(
                location_name=row.location_name,
                old_value=audit_log.old_value,
                new_value=audit_log.new_value,
            ),
            invoice_number=extract_invoice_number(
                invoice_number=row.invoice_number,
                entity_type=audit_log.entity_type,
                entity_id=audit_log.entity_id,
                old_value=audit_log.old_value,
                new_value=audit_log.new_value,
            ),
            model_number=row.model_number,
            result=audit_result(audit_log),
            severity=audit_severity(audit_log),
            security_event=extract_security_event(audit_log),
        )


class AuditLogDetail(AuditLogListEntry):
    request_id: str | None = None
    correlation_id: str | None = None
    related_inventory_item_id: uuid.UUID | None = None
    related_sale_id: str | None = None
    related_tally_sync: bool = False

    @classmethod
    def from_enriched(cls, row: AuditLogEnrichedRow) -> AuditLogDetail:
        base = AuditLogListEntry.from_enriched(row)
        audit_log = row.audit_log
        related_sale_id = audit_log.entity_id if audit_log.entity_type == "sale" else None
        return cls(
            **base.model_dump(),
            request_id=extract_request_id(audit_log.old_value, audit_log.new_value),
            correlation_id=extract_correlation_id(audit_log.old_value, audit_log.new_value),
            related_inventory_item_id=audit_log.inventory_item_id,
            related_sale_id=related_sale_id,
            related_tally_sync=related_tally_sync(audit_log),
        )


class AuditLogSearchQuery(BaseModel):
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
    result: str | None = Field(default=None, pattern="^(success|failure)$")
    severity: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    security_only: bool = False
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
