"""Main Admin recovery key and password recovery tests."""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.infrastructure.repositories.exceptions import (
    InvalidRecoveryKeyError,
    SetupPendingRecoveryConfirmationError,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.security.recovery_key import (
    generate_recovery_key,
    hash_recovery_key,
    normalize_recovery_key,
    verify_recovery_key,
)
from webstudio_backend.services.main_admin_recovery_service import MainAdminRecoveryService
from webstudio_backend.services.setup_service import SetupService

RECOVERY_KEY_PATTERN = re.compile(r"^[A-F0-9]{4}(?:-[A-F0-9]{4}){3}$")
NEW_PASSWORD = "NewSecurePass456!"


def test_generate_recovery_key_format() -> None:
    key = generate_recovery_key()
    assert RECOVERY_KEY_PATTERN.fullmatch(key)


def test_normalize_recovery_key_accepts_unformatted() -> None:
    raw = "ABCD1234EFAB5678"
    assert normalize_recovery_key(raw) == "ABCD-1234-EFAB-5678"


def test_hash_and_verify_recovery_key() -> None:
    key = generate_recovery_key()
    hashed = hash_recovery_key(key)
    assert verify_recovery_key(hashed, key) is True
    assert verify_recovery_key(hashed, "AAAA-BBBB-CCCC-DDDD") is False


@pytest.mark.asyncio
async def test_setup_initialize_returns_recovery_key_once(db_session: AsyncSession) -> None:
    result = await SetupService(db_session).initialize(
        company_name="WEBSTUDIO",
        main_admin_name="Main Admin",
        username=MAIN_ADMIN_USERNAME,
        password=TEST_PASSWORD,
        confirm_password=TEST_PASSWORD,
    )
    assert RECOVERY_KEY_PATTERN.fullmatch(result.recovery_key)
    assert result.user.recovery_key_hash is not None
    assert await SystemSettingRepository(db_session).is_system_initialized() is False

    status = await SetupService(db_session).get_status()
    assert status["awaiting_recovery_key_confirmation"] is True


@pytest.mark.asyncio
async def test_setup_blocks_reinitialize_before_confirmation(db_session: AsyncSession) -> None:
    await SetupService(db_session).initialize(
        company_name="WEBSTUDIO",
        main_admin_name="Main Admin",
        username=MAIN_ADMIN_USERNAME,
        password=TEST_PASSWORD,
        confirm_password=TEST_PASSWORD,
    )
    with pytest.raises(SetupPendingRecoveryConfirmationError):
        await SetupService(db_session).initialize(
            company_name="Other",
            main_admin_name="Other Admin",
            username="otheradmin",
            password=TEST_PASSWORD,
            confirm_password=TEST_PASSWORD,
        )


@pytest.mark.asyncio
async def test_confirm_recovery_key_completes_setup(db_session: AsyncSession) -> None:
    await SetupService(db_session).initialize(
        company_name="WEBSTUDIO",
        main_admin_name="Main Admin",
        username=MAIN_ADMIN_USERNAME,
        password=TEST_PASSWORD,
        confirm_password=TEST_PASSWORD,
    )
    await SetupService(db_session).confirm_recovery_key()
    assert await SystemSettingRepository(db_session).is_system_initialized() is True


@pytest.mark.asyncio
async def test_invalid_recovery_key_rejected(db_session: AsyncSession) -> None:
    await SetupService(db_session).initialize(
        company_name="WEBSTUDIO",
        main_admin_name="Main Admin",
        username=MAIN_ADMIN_USERNAME,
        password=TEST_PASSWORD,
        confirm_password=TEST_PASSWORD,
    )
    await SetupService(db_session).confirm_recovery_key()

    service = MainAdminRecoveryService(db_session)
    with pytest.raises(InvalidRecoveryKeyError):
        await service.recover_password(
            recovery_key="AAAA-BBBB-CCCC-DDDD",
            new_password=NEW_PASSWORD,
            confirm_password=NEW_PASSWORD,
        )


@pytest.mark.asyncio
async def test_successful_password_recovery_regenerates_key(db_session: AsyncSession) -> None:
    init = await SetupService(db_session).initialize(
        company_name="WEBSTUDIO",
        main_admin_name="Main Admin",
        username=MAIN_ADMIN_USERNAME,
        password=TEST_PASSWORD,
        confirm_password=TEST_PASSWORD,
    )
    old_key = init.recovery_key
    await SetupService(db_session).confirm_recovery_key()

    result = await MainAdminRecoveryService(db_session).recover_password(
        recovery_key=old_key,
        new_password=NEW_PASSWORD,
        confirm_password=NEW_PASSWORD,
    )
    assert RECOVERY_KEY_PATTERN.fullmatch(result.new_recovery_key)
    assert result.new_recovery_key != old_key

    with pytest.raises(InvalidRecoveryKeyError):
        await MainAdminRecoveryService(db_session).recover_password(
            recovery_key=old_key,
            new_password="AnotherPass789!",
            confirm_password="AnotherPass789!",
        )


@pytest.mark.asyncio
async def test_recovery_invalidates_sessions(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    init = await SetupService(db_session).initialize(
        company_name="WEBSTUDIO",
        main_admin_name="Main Admin",
        username=MAIN_ADMIN_USERNAME,
        password=TEST_PASSWORD,
        confirm_password=TEST_PASSWORD,
    )
    recovery_key = init.recovery_key
    await SetupService(db_session).confirm_recovery_key()

    login_response = await api_client.post(
        "/api/v1/auth/login",
        json={"username": MAIN_ADMIN_USERNAME, "password": TEST_PASSWORD},
    )
    assert login_response.status_code == 200
    refresh_token = login_response.json()["data"]["refresh_token"]

    recover_response = await api_client.post(
        "/api/v1/auth/main-admin/recover-password",
        json={
            "recovery_key": recovery_key,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert recover_response.status_code == 200
    assert RECOVERY_KEY_PATTERN.fullmatch(recover_response.json()["data"]["recovery_key"])

    refresh_response = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401

    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, NEW_PASSWORD)
    me_response = await api_client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200


@pytest.mark.asyncio
async def test_password_recovery_policy_for_normal_users(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/auth/password-recovery-policy", params={"role": "admin"})
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["self_service_available"] is False
    assert "Main Administrator" in body["message"]

    main_admin_response = await api_client.get(
        "/api/v1/auth/password-recovery-policy",
        params={"role": "main_admin"},
    )
    assert main_admin_response.json()["data"]["self_service_available"] is True
