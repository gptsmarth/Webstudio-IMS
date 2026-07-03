"""Disaster recovery API tests."""

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
from webstudio_backend.infrastructure.database.enums import NotificationType
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.audit_log_filters import AuditLogSearchFilters
from webstudio_backend.infrastructure.repositories.audit_log_repository import AuditLogRepository
from webstudio_backend.infrastructure.repositories.notification_filters import (
    NotificationSearchFilters,
)
from webstudio_backend.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from webstudio_backend.services.backup_alert_service import BackupAlertService
from webstudio_backend.services.backup_schedule import (
    compute_recovery_readiness,
    compute_system_health,
)


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
async def test_recovery_center_dashboard(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/settings/recovery/center", headers=headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["database_status"] == "ok"
    assert payload["recovery_readiness"] in {"ready", "partial", "not_ready"}
    assert "health_issues" in payload


@pytest.mark.asyncio
async def test_recovery_validation(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
    db_session: AsyncSession,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post("/api/v1/settings/recovery/validate", headers=headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["overall_status"] in {"passed", "warning", "failed"}
    assert len(payload["checks"]) >= 8
    keys = {check["key"] for check in payload["checks"]}
    assert "database_integrity" in keys
    assert "schema_version" in keys
    assert "tally_configuration" in keys

    audit_repo = AuditLogRepository(db_session)
    page = await audit_repo.search(
        AuditLogSearchFilters(entity_type="system"),
        PageParams(page=1, page_size=50),
    )
    assert any(log.description and "Recovery validation" in log.description for log in page.items)


@pytest.mark.asyncio
async def test_recovery_health_checks(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/settings/recovery/health-checks", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


@pytest.mark.asyncio
async def test_recovery_reports(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/settings/recovery/reports", headers=headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total_backups"] >= 1
    assert payload["backup_success_rate"] >= 0
    assert payload["export_supported"] is False


@pytest.mark.asyncio
async def test_backup_completed_notification(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    await api_client.post(
        "/api/v1/settings/backups",
        headers=headers,
        json={"backup_type": "full", "trigger_type": "manual"},
    )
    repo = NotificationRepository(db_session)
    notifications = await repo.search(
        NotificationSearchFilters(),
        PageParams(page=1, page_size=50),
    )
    types = [item.notification_type for item in notifications.items]
    assert NotificationType.BACKUP_COMPLETED in types


@pytest.mark.asyncio
async def test_backup_alerts_setting_patch(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.patch(
        "/api/v1/settings/notifications",
        headers=headers,
        json={
            "notifications_enabled": True,
            "desktop_notifications": True,
            "system_alerts_enabled": True,
            "tally_alerts_enabled": True,
            "inventory_alerts_enabled": True,
            "audit_alerts_enabled": True,
            "backup_alerts_enabled": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["backup_alerts_enabled"] is False


def test_compute_recovery_readiness_helpers() -> None:
    assert (
        compute_recovery_readiness(
            database_health="ok",
            backup_health="healthy",
            has_recent_backup=True,
            failed_backup_count=0,
            open_health_issues=0,
        )
        == "ready"
    )
    assert (
        compute_system_health(
            database_health="failed",
            backup_health="healthy",
            open_critical_issues=0,
            open_warning_issues=0,
        )
        == "critical"
    )


@pytest.mark.asyncio
async def test_backup_alert_service_low_storage(db_session: AsyncSession) -> None:
    service = BackupAlertService(db_session)
    await service.maybe_notify_low_storage(storage_free_bytes=1024)
    await db_session.commit()
    repo = NotificationRepository(db_session)
    result = await repo.search(
        NotificationSearchFilters(),
        PageParams(page=1, page_size=50),
    )
    assert any(item.notification_type == NotificationType.LOW_STORAGE for item in result.items)
