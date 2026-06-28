"""Audit log presentation helpers."""

from __future__ import annotations

from typing import Any

from webstudio_backend.infrastructure.database.enums import AuditAction, AuditSource
from webstudio_backend.infrastructure.database.models.audit_log import AuditLog


MODULE_BY_ENTITY_TYPE: dict[str, str] = {
    "inventory_item": "Inventory",
    "sale": "Sales",
    "brand": "Catalogue",
    "product_model": "Catalogue",
    "location": "Catalogue",
    "user": "Users",
    "system": "System",
    "notification": "Notifications",
    "report": "Reports",
}


def audit_module(entity_type: str) -> str:
    return MODULE_BY_ENTITY_TYPE.get(entity_type, entity_type.replace("_", " ").title())


def audit_operation(action: AuditAction) -> str:
    return action.value.replace("_", " ").title()


def audit_result(audit_log: AuditLog) -> str:
    description = (audit_log.description or "").strip().lower()
    if description.startswith("failed") or "failure" in description:
        return "failure"
    if isinstance(audit_log.new_value, dict) and audit_log.new_value.get("success") is False:
        return "failure"
    return "success"


def extract_location_name(
    *,
    location_name: str | None,
    old_value: dict[str, Any] | None,
    new_value: dict[str, Any] | None,
) -> str | None:
    if location_name:
        return location_name
    for payload in (new_value, old_value):
        if not isinstance(payload, dict):
            continue
        for key in ("location_name", "to_location_name", "location"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                name = value.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
    return None


def extract_invoice_number(
    *,
    invoice_number: str | None,
    entity_type: str,
    entity_id: str,
    old_value: dict[str, Any] | None,
    new_value: dict[str, Any] | None,
) -> str | None:
    if invoice_number:
        return invoice_number
    if entity_type == "sale":
        return entity_id
    for payload in (new_value, old_value):
        if isinstance(payload, dict):
            value = payload.get("invoice_number")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def extract_request_id(old_value: dict[str, Any] | None, new_value: dict[str, Any] | None) -> str | None:
    for payload in (new_value, old_value):
        if isinstance(payload, dict):
            value = payload.get("request_id")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def extract_correlation_id(old_value: dict[str, Any] | None, new_value: dict[str, Any] | None) -> str | None:
    for payload in (new_value, old_value):
        if isinstance(payload, dict):
            value = payload.get("correlation_id")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def related_tally_sync(audit_log: AuditLog) -> bool:
    return audit_log.source == AuditSource.TALLY_SYNC
