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
    "system_setting": "Security",
    "permission": "Security",
    "integration_api_key": "Security",
    "tally_sync": "System",
    "notification": "Notifications",
    "report": "Reports",
}

SECURITY_ENTITY_TYPES = frozenset(
    {"user", "permission", "system_setting", "integration_api_key", "system"},
)

SECURITY_EVENT_SEVERITY: dict[str, str] = {
    "login_success": "low",
    "logout": "low",
    "login_failure": "high",
    "account_locked": "critical",
    "password_reset": "high",
    "password_change": "medium",
    "permission_change": "high",
    "permission_denied": "high",
    "user_creation": "medium",
    "user_deactivation": "medium",
    "user_activation": "medium",
    "user_deletion": "high",
    "user_restore": "medium",
    "configuration_change": "high",
    "tally_configuration": "high",
    "recovery_key_used": "critical",
    "recovery_key_regenerated": "critical",
    "session_revoked": "medium",
    "force_logout": "high",
    "token_refresh_reuse": "critical",
}


def extract_security_event(audit_log: AuditLog) -> str | None:
    if isinstance(audit_log.new_value, dict):
        event = audit_log.new_value.get("security_event")
        if isinstance(event, str) and event.strip():
            return event.strip()
    description = (audit_log.description or "").lower()
    if "failed login" in description:
        return "login_failure"
    if "logged in" in description:
        return "login_success"
    if "logged out" in description:
        return "logout"
    if "permission denied" in description:
        return "permission_denied"
    if "password reset" in description:
        return "password_reset"
    if "deactivated" in description or "disabled" in description:
        return "user_deactivation"
    if "activated" in description and "user" in description:
        return "user_activation"
    if "archived" in description and "user" in description:
        return "user_deletion"
    if "recovery key" in description:
        return "recovery_key_used"
    return None


def audit_severity(audit_log: AuditLog) -> str:
    if isinstance(audit_log.new_value, dict):
        stored = audit_log.new_value.get("severity")
        if isinstance(stored, str) and stored in {"low", "medium", "high", "critical"}:
            return stored
    event = extract_security_event(audit_log)
    if event and event in SECURITY_EVENT_SEVERITY:
        return SECURITY_EVENT_SEVERITY[event]
    if audit_result(audit_log) == "failure":
        return "high"
    if audit_log.entity_type in SECURITY_ENTITY_TYPES:
        return "medium"
    return "low"


def is_security_event(audit_log: AuditLog) -> bool:
    if audit_log.entity_type in SECURITY_ENTITY_TYPES:
        return True
    return extract_security_event(audit_log) is not None


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
