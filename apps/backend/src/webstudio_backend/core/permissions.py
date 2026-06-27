"""Role-based permission definitions."""

from __future__ import annotations

from webstudio_backend.infrastructure.database.enums import UserRole

PERMISSIONS_BY_ROLE: dict[UserRole, frozenset[str]] = {
    UserRole.MAIN_ADMIN: frozenset(
        {
            "auth:login",
            "users:manage",
            "brands:read",
            "brands:write",
            "product_models:read",
            "product_models:write",
            "product_models:archive",
            "locations:read",
            "locations:write",
            "inventory:read",
            "inventory:write",
            "inventory:transition",
            "location:transfer",
            "audit:lifecycle",
            "audit:read",
            "sales:reflect",
            "sales:read",
            "dashboard:read",
            "reports:read",
            "sync:trigger",
            "tally:sync",
            "tally:dashboard",
            "tally:notifications",
            "tally:admin",
            "settings:read",
            "settings:write",
            "health:integrations",
        },
    ),
    UserRole.ADMIN: frozenset(
        {
            "auth:login",
            "brands:read",
            "brands:write",
            "product_models:read",
            "product_models:write",
            "locations:read",
            "inventory:read",
            "inventory:write",
            "inventory:transition",
            "location:transfer",
            "audit:lifecycle",
            "sales:reflect",
            "sales:read",
            "dashboard:read",
            "reports:read",
            "sync:trigger",
            "tally:sync",
            "tally:dashboard",
            "tally:notifications",
            "tally:admin",
        },
    ),
    UserRole.SALESPERSON: frozenset(
        {
            "auth:login",
            "brands:read",
            "product_models:read",
            "locations:read",
            "inventory:read",
            "location:transfer",
            "audit:lifecycle",
            "sales:read",
            "dashboard:read",
        },
    ),
    UserRole.SERVICE_ACCOUNT: frozenset(
        {
            "sync:worker",
            "tally:worker",
        },
    ),
}


def permissions_for_role(role: UserRole) -> list[str]:
    return sorted(PERMISSIONS_BY_ROLE.get(role, frozenset()))


def role_has_permission(role: UserRole, permission: str) -> bool:
    return permission in PERMISSIONS_BY_ROLE.get(role, frozenset())
