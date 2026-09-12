"""RBAC permission matrix tests."""

from webstudio_backend.core.permissions import (
    ALL_PERMISSIONS,
    permissions_for_role,
    role_has_any_permission,
    role_has_permission,
)
from webstudio_backend.infrastructure.database.enums import UserRole


def test_main_admin_has_full_matrix() -> None:
    perms = set(permissions_for_role(UserRole.MAIN_ADMIN))
    assert perms == set(ALL_PERMISSIONS)


def test_salesperson_can_view_stock_and_transfer() -> None:
    role = UserRole.SALESPERSON
    assert role_has_permission(role, "inventory:view")
    assert role_has_permission(role, "inventory:transfer")
    assert role_has_permission(role, "dashboard:view")
    assert role_has_permission(role, "sales:view")
    assert role_has_permission(role, "product_models:edit")
    assert role_has_permission(role, "product_models:selling_price:edit")
    assert role_has_permission(role, "inventory:stock_edit")
    assert not role_has_permission(role, "inventory:create")
    assert not role_has_permission(role, "users:view")
    assert not role_has_permission(role, "backup:view")
    assert not role_has_permission(role, "restore:execute")


def test_admin_has_backup_permissions_not_settings() -> None:
    role = UserRole.ADMIN
    assert role_has_permission(role, "backup:view")
    assert role_has_permission(role, "backup:manage")
    assert role_has_permission(role, "restore:view")
    assert role_has_permission(role, "restore:execute")
    assert not role_has_permission(role, "settings:view")


def test_admin_has_inventory_write_not_users() -> None:
    role = UserRole.ADMIN
    assert role_has_permission(role, "inventory:create")
    assert role_has_permission(role, "inventory:archive")
    assert role_has_permission(role, "reports:export")
    assert not role_has_permission(role, "users:view")
    assert not role_has_permission(role, "settings:view")


def test_purchase_permissions_by_role() -> None:
    from webstudio_backend.core.permissions import (
        ASSIGNABLE_PERMISSIONS,
        normalize_permission_set,
    )

    # Main admin always has the full purchase surface.
    main_admin = set(permissions_for_role(UserRole.MAIN_ADMIN))
    assert {"purchase:view", "purchase:import"}.issubset(main_admin)

    # Admin can import; salesperson cannot see or import purchases.
    assert role_has_permission(UserRole.ADMIN, "purchase:view")
    assert role_has_permission(UserRole.ADMIN, "purchase:import")
    assert not role_has_permission(UserRole.SALESPERSON, "purchase:view")
    assert not role_has_permission(UserRole.SALESPERSON, "purchase:import")

    # Purchase permissions are assignable to custom roles.
    assert "purchase:view" in ASSIGNABLE_PERMISSIONS
    assert "purchase:import" in ASSIGNABLE_PERMISSIONS

    # Granting import implies view plus the catalogue reads the import flow needs.
    normalized = normalize_permission_set({"purchase:import"})
    assert "purchase:view" in normalized
    assert "brands:view" in normalized
    assert "product_models:view" in normalized
    assert "locations:view" in normalized
    assert "product_models:create" in normalized


def test_asus_live_price_refresh_is_admin_tier_only() -> None:
    """The bulk/manual "Update prices" trigger spends real Gemini API quota
    per click — Main Admin and Admin both have it, Salesperson does not, and
    it can never be granted to a custom role (so a custom role named
    "manager" still can't get it)."""
    from webstudio_backend.core.permissions import ASSIGNABLE_PERMISSIONS

    permission = "product_models:live_price:refresh"
    assert role_has_permission(UserRole.MAIN_ADMIN, permission)
    assert role_has_permission(UserRole.ADMIN, permission)
    assert not role_has_permission(UserRole.SALESPERSON, permission)
    assert permission not in ASSIGNABLE_PERMISSIONS


def test_role_has_any_permission() -> None:
    assert role_has_any_permission(UserRole.ADMIN, "users:view", "inventory:edit")
    assert not role_has_any_permission(UserRole.SALESPERSON, "users:view", "inventory:create")


def test_dashboard_widget_permissions() -> None:
    from webstudio_backend.core.permissions import (
        DASHBOARD_WIDGET_PERMISSIONS,
        normalize_permission_set,
        user_has_dashboard_widget,
    )

    admin = set(permissions_for_role(UserRole.ADMIN))
    salesperson = set(permissions_for_role(UserRole.SALESPERSON))
    assert "dashboard:brand_distribution" in admin
    assert "dashboard:brand_distribution" not in salesperson
    assert user_has_dashboard_widget(admin, "dashboard:recent_sales")
    assert user_has_dashboard_widget(salesperson, "dashboard:inventory_distribution")
    assert not user_has_dashboard_widget(salesperson, "dashboard:system_status")
    legacy = {"dashboard:view", "inventory:view"}
    assert user_has_dashboard_widget(legacy, DASHBOARD_WIDGET_PERMISSIONS[0])

    normalized = normalize_permission_set({"dashboard:notifications", "dashboard:tally_status"})
    assert "notifications:view" in normalized
    assert "tally:view_status" in normalized
    assert "dashboard:view" in normalized
