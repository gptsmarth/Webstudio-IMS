"""Health endpoint tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live(api_client: AsyncClient) -> None:
    for path in ("/health/live", "/api/v1/health/live"):
        response = await api_client.get(path)
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["status"] == "ok"
        assert response.headers["API-Version"] == "1.0"
        assert "X-Request-ID" in response.headers
        assert "X-Correlation-ID" in response.headers


@pytest.mark.asyncio
async def test_health_version(api_client: AsyncClient) -> None:
    response = await api_client.get("/health/version")
    assert response.status_code == 200
    assert response.json()["data"]["api_version"] == "1.0"


@pytest.mark.asyncio
async def test_metadata_info(api_client: AsyncClient) -> None:
    response = await api_client.get("/metadata/info")
    assert response.status_code == 200
    assert response.json()["data"]["service"] == "webstudio-ims-api"
