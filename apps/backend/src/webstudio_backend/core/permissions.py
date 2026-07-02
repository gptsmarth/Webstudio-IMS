"""Enterprise RBAC — static role → permission map and custom access roles."""

from __future__ import annotations

from webstudio_backend.infrastructure.database.enums import UserRole

# Canonical permission catalogue (module:action). Used by role-permissions API and custom roles.
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
    "inventory:stock_edit",
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
    "dashboard:quick_actions",
    "dashboard:inventory_distribution",
    "dashboard:brand_distribution",
    "dashboard:recent_sales",
    "dashboard:recent_inventory",
    "dashboard:recent_transfers",
    "dashboard:recent_activity",
    "dashboard:notifications",
    "dashboard:store_status",
    "dashboard:tally_status",
    "dashboard:system_status",
    # Catalogue — brands
    "brands:view",
    "brands:create",
    "brands:edit",
    "brands:delete",
    # Catalogue — product models
    "product_models:view",
    "product_models:create",
    "product_models:edit",
    "product_models:delete",
    "product_models:selling_price:edit",
    # Catalogue — locations
    "locations:view",
    "locations:create",
    "locations:edit",
    "locations:delete",
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
    # Backup & recovery
    "backup:view",
    "backup:manage",
    "restore:view",
    "restore:execute",
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

DASHBOARD_WIDGET_PERMISSIONS: tuple[str, ...] = (
    "dashboard:quick_actions",
    "dashboard:inventory_distribution",
    "dashboard:brand_distribution",
    "dashboard:recent_sales",
    "dashboard:recent_inventory",
    "dashboard:recent_transfers",
    "dashboard:recent_activity",
    "dashboard:notifications",
    "dashboard:store_status",
    "dashboard:tally_status",
    "dashboard:system_status",
)

_DASHBOARD_SALESPERSON: frozenset[str] = frozenset(
    {
        "dashboard:view",
        "dashboard:inventory_distribution",
        "dashboard:quick_actions",
        "dashboard:recent_transfers",
        "dashboard:store_status",
    },
)

_MAIN_ADMIN: frozenset[str] = frozenset(ALL_PERMISSIONS)

_ADMIN: frozenset[str] = frozenset(
    {
        "auth:login",
        "inventory:view",
        "inventory:create",
        "inventory:edit",
        "inventory:stock_edit",
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
        *DASHBOARD_WIDGET_PERMISSIONS,
        "brands:view",
        "brands:create",
        "brands:edit",
        "brands:delete",
        "product_models:view",
        "product_models:create",
        "product_models:edit",
        "product_models:delete",
        "product_models:selling_price:edit",
        "locations:view",
        "locations:create",
        "locations:edit",
        "locations:delete",
        "audit:lifecycle",
        "notifications:view",
        "notifications:manage",
        "backup:view",
        "backup:manage",
        "restore:view",
        "restore:execute",
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
        "inventory:stock_edit",
        "sales:view",
        *sorted(_DASHBOARD_SALESPERSON),
        "brands:view",
        "product_models:view",
        "product_models:edit",
        "product_models:selling_price:edit",
        "locations:view",
        "notifications:view",
        "settings:view",
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


# Permissions that cannot be granted through custom access roles (Main Admin / system only).
_CUSTOM_ROLE_DENIED: frozenset[str] = frozenset(
    {
        "users:view",
        "users:create",
        "users:edit",
        "users:reset_password",
        "users:activate",
        "users:deactivate",
        "settings:modify",
        "tally:configure",
        "sync:worker",
        "tally:worker",
        "health:integrations",
    },
)

ASSIGNABLE_PERMISSIONS: tuple[str, ...] = tuple(
    permission for permission in ALL_PERMISSIONS if permission not in _CUSTOM_ROLE_DENIED
)

# Mutating permissions require their module view permission.
PERMISSION_REQUIRES: dict[str, str] = {
    "inventory:create": "inventory:view",
    "inventory:edit": "inventory:view",
    "inventory:stock_edit": "inventory:view",
    "inventory:transfer": "inventory:view",
    "inventory:archive": "inventory:view",
    "inventory:restore": "inventory:view",
    "inventory:export": "inventory:view",
    "sales:create": "sales:view",
    "sales:cancel": "sales:view",
    "sales:export": "sales:view",
    "reports:export": "reports:view",
    "brands:create": "brands:view",
    "brands:edit": "brands:view",
    "brands:delete": "brands:view",
    "product_models:create": "product_models:view",
    "product_models:edit": "product_models:view",
    "product_models:delete": "product_models:view",
    "product_models:selling_price:edit": "product_models:view",
    "locations:create": "locations:view",
    "locations:edit": "locations:view",
    "locations:delete": "locations:view",
    "audit:export": "audit:view",
    "audit:lifecycle": "audit:view",
    "notifications:manage": "notifications:view",
    "backup:manage": "backup:view",
    "restore:execute": "restore:view",
    "tally:run_sync": "tally:view_status",
    "tally:retry_sync": "tally:view_status",
}
for _widget in DASHBOARD_WIDGET_PERMISSIONS:
    PERMISSION_REQUIRES[_widget] = "dashboard:view"

# Legacy catalogue archive permissions map to delete for custom roles created before M12.
LEGACY_PERMISSION_ALIASES: dict[str, str] = {
    "brands:archive": "brands:delete",
    "product_models:archive": "product_models:delete",
    "locations:archive": "locations:delete",
}


def expand_legacy_permissions(permissions: set[str] | frozenset[str]) -> set[str]:
    expanded = set(permissions)
    for legacy, current in LEGACY_PERMISSION_ALIASES.items():
        if legacy in expanded:
            expanded.add(current)
    return expanded


def normalize_permission_set(permissions: set[str] | frozenset[str]) -> set[str]:
    """Ensure implied view permissions are included."""
    normalized = expand_legacy_permissions(permissions)
    for permission in list(normalized):
        required = PERMISSION_REQUIRES.get(permission)
        if required:
            normalized.add(required)
    if "dashboard:view" not in normalized and normalized.intersection(
        {"inventory:view", "sales:view", "reports:view", "brands:view"},
    ):
        normalized.add("dashboard:view")
    normalized.add("auth:login")
    return normalized


def validate_assignable_permissions(permissions: set[str]) -> None:
    unknown = permissions.difference(ALL_PERMISSIONS)
    if unknown:
        raise ValueError(f"Unknown permissions: {', '.join(sorted(unknown))}")
    denied = permissions.intersection(_CUSTOM_ROLE_DENIED)
    if denied:
        raise ValueError(f"Permissions not allowed in custom roles: {', '.join(sorted(denied))}")


def user_has_permission(granted: set[str] | frozenset[str], permission: str) -> bool:
    if permission in granted:
        return True
    legacy = next(
        (legacy for legacy, current in LEGACY_PERMISSION_ALIASES.items() if current == permission),
        None,
    )
    return legacy is not None and legacy in granted


def user_has_any_permission(granted: set[str] | frozenset[str], *permissions: str) -> bool:
    return any(permission in granted for permission in permissions)


def user_has_dashboard_widget(granted: set[str] | frozenset[str], widget: str) -> bool:
    """Return whether a dashboard widget should render for the granted permission set."""
    if "dashboard:view" not in granted:
        return False
    if widget in granted:
        return True
    if not any(entry in granted for entry in DASHBOARD_WIDGET_PERMISSIONS):
        return True
    return False
