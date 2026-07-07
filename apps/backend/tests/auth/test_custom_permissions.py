"""Tests for custom access role permission normalization."""

from webstudio_backend.core.permissions import (
    normalize_permission_set,
    validate_assignable_permissions,
)


def test_normalize_adds_required_view_permission() -> None:
    normalized = normalize_permission_set({"sales:export"})
    assert "sales:view" in normalized
    assert "sales:export" in normalized
    assert "auth:login" in normalized


def test_inventory_create_requires_view() -> None:
    normalized = normalize_permission_set({"inventory:create"})
    assert "inventory:view" in normalized
    assert "inventory:create" in normalized


def test_inventory_view_does_not_force_dashboard() -> None:
    normalized = normalize_permission_set({"inventory:view", "sales:view"})
    assert "inventory:view" in normalized
    assert "sales:view" in normalized
    assert "dashboard:view" not in normalized


def test_validate_rejects_admin_only_permissions() -> None:
    try:
        validate_assignable_permissions({"users:edit", "inventory:view"})
    except ValueError as exc:
        assert "users:edit" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
