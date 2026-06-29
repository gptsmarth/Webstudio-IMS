"""Administration center: archive, force logout, integration keys."""

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
async def test_user_list_includes_admin_fields(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    main_headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/users", headers=main_headers)
    assert response.status_code == 200
    user = response.json()["data"][0]
    assert "failed_login_count" in user
    assert "active_session_count" in user
    assert "password_age_days" in user
    assert "is_archived" in user


@pytest.mark.asyncio
async def test_archive_restore_and_force_logout_user(
    db_session: AsyncSession,
    api_client: AsyncClient,
    initialized_system,
) -> None:
    main_admin, _ = initialized_system
    actor = AuditActor(user_id=main_admin.id, display_name="Main Admin", role="main_admin")
    service = UserService(db_session)
    user = await service.create_user(
        username="archived1",
        role=UserRole.SALESPERSON,
        temporary_password=TEST_PASSWORD,
        display_name="Archived User",
        actor=actor,
    )
    main_headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)

    archive = await api_client.post(f"/api/v1/users/{user.id}/archive", headers=main_headers)
    assert archive.status_code == 200
    archived_body = archive.json()["data"]
    assert archived_body["is_archived"] is True

    login_blocked = await api_client.post(
        "/api/v1/auth/login",
        json={"username": "archived1", "password": TEST_PASSWORD},
    )
    assert login_blocked.status_code in (401, 403)

    restore = await api_client.post(f"/api/v1/users/{user.id}/restore", headers=main_headers)
    assert restore.status_code == 200
    assert restore.json()["data"]["is_archived"] is False

    login_ok = await api_client.post(
        "/api/v1/auth/login",
        json={"username": "archived1", "password": TEST_PASSWORD},
    )
    assert login_ok.status_code == 200

    logout_all = await api_client.post(f"/api/v1/users/{user.id}/logout-all", headers=main_headers)
    assert logout_all.status_code == 200
    assert logout_all.json()["data"]["sessions_revoked"] >= 1

    audits = await AuditLogRepository(db_session).search(
        AuditLogSearchFilters(entity_type="user", entity_id=str(user.id)),
        PageParams(page=1, page_size=20),
    )
    actions = {entry.action.value.lower() for entry in audits.items}
    assert "archive" in actions
    assert "restore" in actions


@pytest.mark.asyncio
async def test_integration_keys_main_admin_only(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    main_headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    create_admin = await api_client.post(
        "/api/v1/users",
        headers=main_headers,
        json={
            "username": "adminkeys",
            "display_name": "Admin Keys",
            "role": "admin",
            "temporary_password": TEST_PASSWORD,
        },
    )
    assert create_admin.status_code == 201

    admin_login = await api_client.post(
        "/api/v1/auth/login",
        json={"username": "adminkeys", "password": TEST_PASSWORD},
    )
    admin_token = admin_login.json()["data"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    forbidden = await api_client.get("/api/v1/admin/integration-keys", headers=admin_headers)
    assert forbidden.status_code == 403

    created = await api_client.post(
        "/api/v1/admin/integration-keys",
        headers=main_headers,
        json={
            "service_type": "email",
            "label": "SMTP Production",
            "api_key": "secret-email-key-1234",
        },
    )
    assert created.status_code == 201
    key_id = created.json()["data"]["id"]
    assert created.json()["data"]["key_hint"].endswith("1234")

    listed = await api_client.get("/api/v1/admin/integration-keys", headers=main_headers)
    assert listed.status_code == 200
    assert any(item["id"] == key_id for item in listed.json()["data"])

    archived = await api_client.post(
        f"/api/v1/admin/integration-keys/{key_id}/archive",
        headers=main_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["data"]["is_archived"] is True
