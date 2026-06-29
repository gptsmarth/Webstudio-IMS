"""Backup administration API tests."""

from __future__ import annotations

pytest_plugins = ["auth.conftest"]

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.app import create_app
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.services.backup_schedule import resolve_retention_limit


@pytest_asyncio.fixture
async def api_client(
    db_session: AsyncSession,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(test_settings)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def backup_filename(
    api_client: AsyncClient,
    initialized_system,
) -> str:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post(
        "/api/v1/settings/backups",
        headers=headers,
        json={"backup_type": "full", "trigger_type": "manual"},
    )
    assert response.status_code == 200
    return response.json()["data"]["filename"]


@pytest.mark.asyncio
async def test_backup_admin_dashboard(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/settings/backups/admin/dashboard", headers=headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total_backup_count"] >= 1
    assert "storage_free_bytes" in payload
    assert "retention_policy" in payload


@pytest.mark.asyncio
async def test_backup_admin_history(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/settings/backups/admin/history", headers=headers)
    assert response.status_code == 200
    items = response.json()["data"]
    assert any(item["filename"] == backup_filename for item in items)


@pytest.mark.asyncio
async def test_backup_details_and_verify(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    details = await api_client.get(
        f"/api/v1/settings/backups/{backup_filename}/details",
        headers=headers,
    )
    assert details.status_code == 200
    assert details.json()["data"]["filename"] == backup_filename

    verify = await api_client.post(
        f"/api/v1/settings/backups/{backup_filename}/verify",
        headers=headers,
    )
    assert verify.status_code == 200
    assert verify.json()["data"]["integrity_valid"] is True


@pytest.mark.asyncio
async def test_backup_archive_and_delete(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    archive = await api_client.post(
        f"/api/v1/settings/backups/{backup_filename}/archive",
        headers=headers,
    )
    assert archive.status_code == 200
    assert archive.json()["data"]["is_archived"] is True

    delete = await api_client.delete(
        f"/api/v1/settings/backups/{backup_filename}",
        headers=headers,
    )
    assert delete.status_code == 200


@pytest.mark.asyncio
async def test_backup_history_export_xlsx(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get(
        "/api/v1/settings/backups/admin/history/export",
        headers=headers,
        params={"format": "xlsx"},
    )
    assert response.status_code == 200
    assert response.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_retention_policy_update(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.patch(
        "/api/v1/settings/backup",
        headers=headers,
        json={
            "backup_folder": "backups",
            "storage_backend": "local",
            "schedule": "manual",
            "retention_policy": "last_7",
            "retention_count": 7,
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["retention_policy"] == "last_7"


def test_resolve_retention_limit() -> None:
    assert resolve_retention_limit("last_7", 30) == 7
    assert resolve_retention_limit("unlimited", 30) is None
    assert resolve_retention_limit("custom", 42) == 42
