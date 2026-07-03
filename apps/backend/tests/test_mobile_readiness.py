"""Mobile readiness API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_sync_state_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/sync/state")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/search", params={"q": "asus"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_version_and_capabilities_public(api_client: AsyncClient) -> None:
    version = await api_client.get("/api/v1/version")
    assert version.status_code == 200
    capabilities = await api_client.get("/api/v1/capabilities")
    assert capabilities.status_code == 200
    assert "modules" in capabilities.json()["data"]
