"""Setup and authentication service tests."""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.infrastructure.database.enums import UserRole
from webstudio_backend.infrastructure.repositories.exceptions import (
    SystemAlreadyInitializedError,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.setup_service import SetupService

RECOVERY_KEY_PATTERN = re.compile(r"^[A-F0-9]{4}(?:-[A-F0-9]{4}){3}$")


@pytest.mark.asyncio
async def test_setup_status_uninitialized(db_session: AsyncSession) -> None:
    status = await SetupService(db_session).get_status()
    assert status["system_initialized"] is False
    assert status["company_name"] is None


@pytest.mark.asyncio
async def test_setup_initialize_creates_main_admin(db_session: AsyncSession) -> None:
    result = await SetupService(db_session).initialize(
        company_name="WEBSTUDIO",
        main_admin_name="Main Admin",
        username=MAIN_ADMIN_USERNAME,
        password=TEST_PASSWORD,
        confirm_password=TEST_PASSWORD,
    )
    assert result.user.role is UserRole.MAIN_ADMIN
    assert result.company_name == "WEBSTUDIO"
    assert RECOVERY_KEY_PATTERN.fullmatch(result.recovery_key)
    assert await SystemSettingRepository(db_session).is_system_initialized() is False

    await SetupService(db_session).confirm_recovery_key()
    assert await SystemSettingRepository(db_session).is_system_initialized() is True


@pytest.mark.asyncio
async def test_setup_cannot_run_twice(db_session: AsyncSession, initialized_system) -> None:
    with pytest.raises(SystemAlreadyInitializedError):
        await SetupService(db_session).initialize(
            company_name="Other",
            main_admin_name="Other Admin",
            username="otheradmin",
            password=TEST_PASSWORD,
            confirm_password=TEST_PASSWORD,
        )


@pytest.mark.asyncio
async def test_login_and_me(api_client: AsyncClient, initialized_system) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["username"] == MAIN_ADMIN_USERNAME
    assert body["role"] == "main_admin"
    assert "users:view" in body["permissions"]


@pytest.mark.asyncio
async def test_login_blocked_before_setup(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"username": MAIN_ADMIN_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 403
