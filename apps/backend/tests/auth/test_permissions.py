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


def test_role_has_any_permission() -> None:
    assert role_has_any_permission(UserRole.ADMIN, "users:view", "inventory:edit")
    assert not role_has_any_permission(UserRole.SALESPERSON, "users:view", "inventory:create")


def test_dashboard_widget_permissions() -> None:
    from webstudio_backend.core.permissions import (
        DASHBOARD_WIDGET_PERMISSIONS,
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
