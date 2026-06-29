"""Enterprise RBAC — static role → permission map (extensible for future custom roles)."""

from __future__ import annotations

from webstudio_backend.infrastructure.database.enums import UserRole

# Canonical permission catalogue (module:action). Used by role-permissions API and future custom roles.
ALL_PERMISSIONS: tuple[str, ...] = (
    "auth:login",
    # Users
    "users:view",
    "users:create",
    "users:edit",
    "users:reset_password",
    "users:activate",
    "users:deactivate",
    # Inventory
    "inventory:view",
    "inventory:create",
    "inventory:edit",
    "inventory:transfer",
    "inventory:archive",
    "inventory:restore",
    "inventory:export",
    # Sales
    "sales:view",
    "sales:create",
    "sales:cancel",
    "sales:export",
    # Reports
    "reports:view",
    "reports:export",
    # Dashboard
    "dashboard:view",
    # Catalogue — brands
    "brands:view",
    "brands:create",
    "brands:edit",
    "brands:archive",
    # Catalogue — product models
    "product_models:view",
    "product_models:create",
    "product_models:edit",
    "product_models:archive",
    "product_models:selling_price:edit",
    # Catalogue — locations
    "locations:view",
    "locations:create",
    "locations:edit",
    "locations:archive",
    # Audit
    "audit:view",
    "audit:export",
    "audit:lifecycle",
    # Notifications
    "notifications:view",
    "notifications:manage",
    # Settings
    "settings:view",
    "settings:modify",
    # Tally
    "tally:view_status",
    "tally:configure",
    "tally:run_sync",
    "tally:retry_sync",
    # Service integrations
    "sync:worker",
    "tally:worker",
    "health:integrations",
)

_MAIN_ADMIN: frozenset[str] = frozenset(ALL_PERMISSIONS)

_ADMIN: frozenset[str] = frozenset(
    {
        "auth:login",
        "inventory:view",
        "inventory:create",
        "inventory:edit",
        "inventory:transfer",
        "inventory:archive",
        "inventory:restore",
        "inventory:export",
        "sales:view",
        "sales:create",
        "sales:cancel",
        "sales:export",
        "reports:view",
        "reports:export",
        "dashboard:view",
        "brands:view",
        "brands:create",
        "brands:edit",
        "brands:archive",
        "product_models:view",
        "product_models:create",
        "product_models:edit",
        "product_models:archive",
        "product_models:selling_price:edit",
        "locations:view",
        "locations:create",
        "locations:edit",
        "locations:archive",
        "audit:lifecycle",
        "notifications:view",
        "notifications:manage",
        "tally:view_status",
        "tally:run_sync",
        "tally:retry_sync",
    },
)

_SALESPERSON: frozenset[str] = frozenset(
    {
        "auth:login",
        "inventory:view",
        "inventory:transfer",
        "sales:view",
        "dashboard:view",
        "brands:view",
        "product_models:view",
        "product_models:selling_price:edit",
        "locations:view",
        "notifications:view",
        "audit:lifecycle",
    },
)

_SERVICE_ACCOUNT: frozenset[str] = frozenset({"sync:worker", "tally:worker"})

PERMISSIONS_BY_ROLE: dict[UserRole, frozenset[str]] = {
    UserRole.MAIN_ADMIN: _MAIN_ADMIN,
    UserRole.ADMIN: _ADMIN,
    UserRole.SALESPERSON: _SALESPERSON,
    UserRole.SERVICE_ACCOUNT: _SERVICE_ACCOUNT,
}


def permissions_for_role(role: UserRole) -> list[str]:
    return sorted(PERMISSIONS_BY_ROLE.get(role, frozenset()))


def role_has_permission(role: UserRole, permission: str) -> bool:
    return permission in PERMISSIONS_BY_ROLE.get(role, frozenset())


def role_has_any_permission(role: UserRole, *permissions: str) -> bool:
    granted = PERMISSIONS_BY_ROLE.get(role, frozenset())
    return any(permission in granted for permission in permissions)
