"""Office deployment wizard API tests (M12F)."""

from __future__ import annotations

pytest_plugins = ["auth.conftest"]

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.app import create_app
from webstudio_backend.core.config import get_settings
from webstudio_backend.core.dependencies import get_db_session


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(get_settings())

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


EXPECTED_CHECK_KEYS = {
    "network",
    "postgresql",
    "windows_service",
    "api",
    "backup_path",
    "image_storage",
    "ai_provider",
    "tally",
    "firewall",
    "ports",
}


@pytest.mark.asyncio
async def test_office_deployment_status_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/deployment/office/status")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_office_deployment_detect_returns_all_checks(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post("/api/v1/deployment/office/detect", headers=headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    keys = {check["key"] for check in payload["checks"]}
    assert EXPECTED_CHECK_KEYS.issubset(keys)
    assert payload["ip_strategy"] is not None
    assert payload["ip_strategy"]["recommended"] in {"static_ip", "dhcp_reservation"}
    assert payload["server_lan_ip"]


@pytest.mark.asyncio
async def test_office_deployment_complete_saves_configuration(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post("/api/v1/deployment/office/complete", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["completed"] is True
    assert data["summary"]["configuration_files_required"] is False
    assert data["apply"]["saved_settings"]["backup_folder"]
    assert data["apply"]["saved_settings"]["product_image_storage_path"]

    status_response = await api_client.get("/api/v1/deployment/office/status", headers=headers)
    status = status_response.json()["data"]
    assert status["completed"] is True
    assert status["summary_available"] is True
    assert status["summary"]["client_connection_url"]
