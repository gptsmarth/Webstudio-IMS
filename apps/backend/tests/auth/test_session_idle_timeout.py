"""Idle session timeout enforcement tests."""

from __future__ import annotations

pytest_plugins = ["auth.conftest"]

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD
from webstudio_backend.infrastructure.database.enums import SettingValueType
from webstudio_backend.infrastructure.database.models.refresh_token import RefreshToken
from webstudio_backend.infrastructure.repositories.audit_log_repository import AuditLogRepository
from webstudio_backend.infrastructure.repositories.audit_log_filters import AuditLogSearchFilters
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams


@pytest.mark.asyncio
async def test_refresh_rejected_after_idle_timeout(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
) -> None:
    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "session_timeout_minutes",
        "1",
        value_type=SettingValueType.INTEGER,
        updated_by_user_id=1,
    )

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"username": MAIN_ADMIN_USERNAME, "password": TEST_PASSWORD},
    )
    assert login.status_code == 200
    refresh_token = login.json()["data"]["refresh_token"]

    token_hash_row = await db_session.execute(
        select(RefreshToken).order_by(RefreshToken.id.desc()).limit(1),
    )
    stored = token_hash_row.scalar_one()
    stale_time = datetime.now(UTC) - timedelta(minutes=5)
    await db_session.execute(
        update(RefreshToken)
        .where(RefreshToken.id == stored.id)
        .values(last_used_at=stale_time),
    )
    await db_session.commit()

    response = await api_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "SESSION_IDLE_TIMEOUT"

    revoked = await db_session.get(RefreshToken, stored.id)
    assert revoked is not None
    assert revoked.revoked_at is not None

    audits = await AuditLogRepository(db_session).search(
        AuditLogSearchFilters(entity_type="user", search="session_idle_timeout"),
        PageParams(page=1, page_size=20),
    )
    assert any(
        (entry.new_value or {}).get("security_event") == "session_idle_timeout"
        for entry in audits.items
    )


@pytest.mark.asyncio
async def test_refresh_succeeds_within_idle_timeout(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
) -> None:
    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "session_timeout_minutes",
        "15",
        value_type=SettingValueType.INTEGER,
        updated_by_user_id=1,
    )
    await db_session.commit()

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"username": MAIN_ADMIN_USERNAME, "password": TEST_PASSWORD},
    )
    refresh_token = login.json()["data"]["refresh_token"]
    response = await api_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]
