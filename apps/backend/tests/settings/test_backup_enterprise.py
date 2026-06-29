"""Enterprise backup enhancement tests."""

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
from webstudio_backend.services.backup_schedule import compute_readiness_score


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


@pytest.mark.asyncio
async def test_mobile_backup_status(api_client: AsyncClient, initialized_system) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/settings/backups/mobile/status", headers=headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert "health_status" in payload
    assert payload["restore_history_available"] is True


@pytest.mark.asyncio
async def test_recovery_center_readiness_score(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    await api_client.post("/api/v1/settings/backups", headers=headers, json={})
    response = await api_client.get("/api/v1/settings/recovery/center", headers=headers)
    payload = response.json()["data"]
    assert "readiness_score" in payload
    assert payload["readiness_score"]["overall_score"] >= 0
    assert "storage_monitoring" in payload


def test_compute_readiness_score() -> None:
    score = compute_readiness_score(
        database_health="ok",
        backup_health="healthy",
        storage_status="healthy",
        latest_backup_age_days=0.5,
        latest_verification_status="success",
        recovery_readiness="ready",
    )
    assert score["overall_score"] >= 90
