"""User management and RBAC tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import UserRole
from webstudio_backend.infrastructure.repositories.audit_log_filters import AuditLogSearchFilters
from webstudio_backend.infrastructure.repositories.audit_log_repository import AuditLogRepository
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.services.user_service import UserService


@pytest.mark.asyncio
async def test_main_admin_can_create_user(
    db_session: AsyncSession,
    initialized_system,
) -> None:
    main_admin, _ = initialized_system
    actor = AuditActor(user_id=main_admin.id, display_name="Main Admin", role="main_admin")
    user = await UserService(db_session).create_user(
        username="sales1",
        role=UserRole.SALESPERSON,
        temporary_password=TEST_PASSWORD,
        display_name="Sales One",
        actor=actor,
    )
    assert user.username == "sales1"
    assert user.must_change_password is True

    audits = await AuditLogRepository(db_session).search(
        AuditLogSearchFilters(entity_type="user", entity_id=str(user.id)),
        PageParams(page=1, page_size=10),
    )
    assert audits.total_items >= 1


@pytest.mark.asyncio
async def test_user_management_requires_main_admin(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    main_headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    create_response = await api_client.post(
        "/api/v1/users",
        headers=main_headers,
        json={
            "username": "admin1",
            "display_name": "Admin One",
            "role": "admin",
            "temporary_password": TEST_PASSWORD,
        },
    )
    assert create_response.status_code == 201

    admin_login = await api_client.post(
        "/api/v1/auth/login",
        json={"username": "admin1", "password": TEST_PASSWORD},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["data"]["access_token"]
    forbidden = await api_client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_reset_password_and_disable_user(
    db_session: AsyncSession,
    initialized_system,
) -> None:
    main_admin, _ = initialized_system
    actor = AuditActor(user_id=main_admin.id, display_name="Main Admin", role="main_admin")
    service = UserService(db_session)
    user = await service.create_user(
        username="tempuser",
        role=UserRole.ADMIN,
        temporary_password=TEST_PASSWORD,
        display_name="Temp User",
        actor=actor,
    )
    await service.reset_password(user.id, temporary_password="NewSecurePass9!", actor=actor)
    updated = await service.disable_user(user.id, actor=actor)
    assert updated.status.value == "disabled"


@pytest.mark.asyncio
async def test_role_permissions_endpoint(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    main_headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/users/role-permissions", headers=main_headers)
    assert response.status_code == 200
    roles = response.json()["data"]["roles"]
    role_names = {entry["role"] for entry in roles}
    assert role_names == {"main_admin", "admin", "salesperson"}
    main_admin = next(entry for entry in roles if entry["role"] == "main_admin")
    assert "users:view" in main_admin["permissions"]


@pytest.mark.asyncio
async def test_main_admin_cannot_disable_self(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    main_admin, _ = initialized_system
    main_headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post(
        f"/api/v1/users/{main_admin.id}/disable",
        headers=main_headers,
    )
    assert response.status_code == 409
