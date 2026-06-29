"""Security audit and monitoring tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.infrastructure.database.enums import SettingValueType
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.audit_log_filters import AuditLogSearchFilters
from webstudio_backend.infrastructure.repositories.audit_log_repository import AuditLogRepository
from webstudio_backend.infrastructure.repositories.notification_filters import (
    NotificationSearchFilters,
)
from webstudio_backend.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.audit_log_presenter import extract_security_event


async def _security_event_names(db_session: AsyncSession) -> list[str | None]:
    audits = await AuditLogRepository(db_session).search(
        AuditLogSearchFilters(security_only=True),
        PageParams(page=1, page_size=100),
    )
    return [extract_security_event(entry) for entry in audits.items]


@pytest.mark.asyncio
async def test_login_creates_security_audit(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
) -> None:
    await api_client.post(
        "/api/v1/auth/login",
        json={"username": MAIN_ADMIN_USERNAME, "password": TEST_PASSWORD},
    )
    events = await _security_event_names(db_session)
    assert "login_success" in events


@pytest.mark.asyncio
async def test_failed_login_creates_security_audit(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
) -> None:
    await api_client.post(
        "/api/v1/auth/login",
        json={"username": MAIN_ADMIN_USERNAME, "password": "wrong-password"},
    )
    events = await _security_event_names(db_session)
    assert "login_failure" in events


@pytest.mark.asyncio
async def test_account_lockout_creates_security_audit_and_alert(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
) -> None:
    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "lockout_threshold",
        "1",
        value_type=SettingValueType.INTEGER,
        updated_by_user_id=None,
    )
    await settings.set_value(
        "audit_alerts_enabled",
        "true",
        value_type=SettingValueType.BOOLEAN,
        updated_by_user_id=None,
    )
    await db_session.commit()

    await api_client.post(
        "/api/v1/auth/login",
        json={"username": MAIN_ADMIN_USERNAME, "password": "wrong-password"},
    )
    events = await _security_event_names(db_session)
    assert "account_locked" in events

    notifications = await NotificationRepository(db_session).search(
        NotificationSearchFilters(),
        PageParams(page=1, page_size=20),
    )
    assert any("locked" in note.title.lower() for note in notifications.items)


@pytest.mark.asyncio
async def test_security_settings_change_creates_configuration_audit(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    workspace = await api_client.get("/api/v1/settings", headers=headers)
    security = workspace.json()["data"]["security"]
    security["session_timeout_minutes"] = int(security["session_timeout_minutes"]) + 1

    response = await api_client.patch("/api/v1/settings/security", headers=headers, json=security)
    assert response.status_code == 200

    events = await _security_event_names(db_session)
    assert "configuration_change" in events


@pytest.mark.asyncio
async def test_security_dashboard_includes_monitoring_fields(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/security/dashboard", headers=headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert "org_active_session_count" in payload
    assert "recent_security_events" in payload
    assert "critical_alerts" in payload
    assert isinstance(payload["recent_security_events"], list)


@pytest.mark.asyncio
async def test_audit_logs_support_security_filters(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get(
        "/api/v1/audit_logs",
        headers=headers,
        params={"security_only": True, "severity": "low"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert isinstance(payload, list)
    for entry in payload:
        assert entry.get("severity") == "low"


@pytest.mark.asyncio
async def test_security_export_returns_spreadsheet(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get(
        "/api/v1/security/export",
        headers=headers,
        params={"format": "xlsx"},
    )
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers.get("content-type", "")
    assert len(response.content) > 100


@pytest.mark.asyncio
async def test_logout_creates_security_audit(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
) -> None:
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"username": MAIN_ADMIN_USERNAME, "password": TEST_PASSWORD},
    )
    tokens = login.json()["data"]
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    logout = await api_client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout.status_code == 200

    events = await _security_event_names(db_session)
    assert "logout" in events
