"""System settings API tests."""

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


@pytest.mark.asyncio
async def test_settings_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/settings")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_settings_workspace_for_main_admin(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/settings", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]
    assert "general" in data
    assert "security" in data
    assert "integrations" in data
    assert "backup" in data
    assert "system" in data
    assert data["system"]["api_health"] in {"ok", "failed"}


@pytest.mark.asyncio
async def test_settings_general_patch(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    body = {
        "company_name": "WEBSTUDIO Retail",
        "company_logo": "",
        "company_address": "Test Address",
        "gst_number": "29TEST0000A1Z5",
        "company_phone": "+91 90000 00000",
        "company_email": "admin@webstudio.test",
        "default_store_id": None,
        "default_language": "en",
        "timezone": "Asia/Kolkata",
        "currency": "INR",
    }
    response = await api_client.patch("/api/v1/settings/general", headers=headers, json=body)
    assert response.status_code == 200
    updated = response.json()["data"]
    assert updated["company_name"] == "WEBSTUDIO Retail"
    assert updated["gst_number"] == "29TEST0000A1Z5"


@pytest.mark.asyncio
async def test_settings_notifications_patch(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    body = {
        "notifications_enabled": False,
        "desktop_notifications": True,
        "system_alerts_enabled": True,
        "tally_alerts_enabled": False,
        "inventory_alerts_enabled": True,
        "audit_alerts_enabled": True,
    }
    response = await api_client.patch("/api/v1/settings/notifications", headers=headers, json=body)
    assert response.status_code == 200
    updated = response.json()["data"]
    assert updated["notifications_enabled"] is False
    assert updated["tally_alerts_enabled"] is False


@pytest.mark.asyncio
async def test_settings_integrations_patch(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    body = {
        "gemini_model": "gemini-2.5-flash",
        "gemini_api_key": "AIzaSyTestKey1234567890",
        "clear_gemini_api_key": False,
        "ai_primary_provider": "gemini",
        "ai_fallback_chain": ["gemini"],
        "ai_enrichment_enabled": True,
        "ai_timeout_seconds": 90,
        "ai_retry_count": 2,
        "asus_price_refresh_stale_days": 15,
        "asus_price_gemini_api_key": "AIzaSyAsusPriceKey0987654321",
        "clear_asus_price_gemini_api_key": False,
        "groq_model": "llama-3.3-70b-versatile",
        "clear_groq_api_key": False,
        "openrouter_model": "meta-llama/llama-3.3-70b-instruct:free",
        "clear_openrouter_api_key": False,
    }
    response = await api_client.patch("/api/v1/settings/integrations", headers=headers, json=body)
    assert response.status_code == 200
    updated = response.json()["data"]
    assert updated["gemini_configured"] is True
    assert updated["gemini_model"] == "gemini-2.5-flash"
    assert updated["gemini_api_key_hint"] is not None
    assert "7890" in updated["gemini_api_key_hint"]
    assert updated["ai_primary_provider"] == "gemini"
    assert "gemini" in updated["ai_fallback_chain"]
    assert len(updated["ai_provider_health"]) >= 4
    assert updated["asus_price_refresh_stale_days"] == 15
    # ASUS price lookups keep their own key, separate from the general one above.
    assert updated["asus_price_gemini_configured"] is True
    assert updated["asus_price_gemini_api_key_hint"] is not None
    assert "4321" in updated["asus_price_gemini_api_key_hint"]
