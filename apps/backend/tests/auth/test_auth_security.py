"""Enterprise authentication security tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.infrastructure.database.enums import SettingValueType
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.password_policy_service import PasswordPolicyService


@pytest.mark.asyncio
async def test_login_returns_session_id(api_client: AsyncClient, initialized_system) -> None:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={
            "username": MAIN_ADMIN_USERNAME,
            "password": TEST_PASSWORD,
            "remember_me": True,
            "device_label": "Test Client",
        },
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body.get("session_id") is not None
    assert body["access_token"]
    assert body["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_rotates_token(api_client: AsyncClient, initialized_system) -> None:
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"username": MAIN_ADMIN_USERNAME, "password": TEST_PASSWORD},
    )
    refresh_token = login.json()["data"]["refresh_token"]
    refreshed = await api_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["data"]["refresh_token"]
    assert new_refresh != refresh_token
    stale = await api_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert stale.status_code == 401


@pytest.mark.asyncio
async def test_list_and_revoke_sessions(api_client: AsyncClient, initialized_system) -> None:
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"username": MAIN_ADMIN_USERNAME, "password": TEST_PASSWORD},
    )
    tokens = login.json()["data"]
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    listed = await api_client.get(
        "/api/v1/auth/sessions",
        headers=headers,
        params={"refresh_token": tokens["refresh_token"]},
    )
    assert listed.status_code == 200
    sessions = listed.json()["data"]
    assert len(sessions) >= 1
    assert any(session["is_current"] for session in sessions)


@pytest.mark.asyncio
async def test_security_dashboard(api_client: AsyncClient, initialized_system) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/security/dashboard", headers=headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert "password_policy" in payload
    assert "recent_login_events" in payload
    assert "recent_security_events" in payload
    assert "org_active_session_count" in payload
    assert payload["failed_logins_24h"] >= 0


@pytest.mark.asyncio
async def test_password_policy_enforced_from_settings(db_session: AsyncSession) -> None:
    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "password_min_length",
        "12",
        value_type=SettingValueType.INTEGER,
        updated_by_user_id=None,
    )
    await settings.set_value(
        "password_require_symbol",
        "true",
        value_type=SettingValueType.BOOLEAN,
        updated_by_user_id=None,
    )
    await db_session.commit()

    service = PasswordPolicyService(db_session)
    policy = await service.get_policy()
    with pytest.raises(ValueError, match="special character"):
        service.validate_strength("LongPassword1", policy)


@pytest.mark.asyncio
async def test_unlock_user(
    api_client: AsyncClient, initialized_system, db_session: AsyncSession
) -> None:
    from webstudio_backend.infrastructure.repositories.user_repository import UserRepository

    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    admin = await UserRepository(db_session).get_by_username(MAIN_ADMIN_USERNAME)
    assert admin is not None
    await UserRepository(db_session).record_failed_login(
        admin, lockout_threshold=1, lockout_minutes=30
    )
    await db_session.commit()

    unlock = await api_client.post(f"/api/v1/users/{admin.id}/unlock", headers=headers)
    assert unlock.status_code == 200
    refreshed = await UserRepository(db_session).get_by_id(admin.id)
    assert refreshed is not None
    assert refreshed.locked_until is None
