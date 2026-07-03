"""Platform version and capabilities endpoint tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_version(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert data["backend_version"] == "0.1.0"
    assert data["version"] == "0.1.0"
    assert data["api_version"] == "1.0"
    assert "schema_version" in data
    assert "build_version" in data
    assert "build_number" in data
    assert "git_commit" in data
    assert "release_channel" in data
    assert "database_revision" in data
    assert "version_identity" in data
    assert data["version_identity"]["version"] == "0.1.0"
    assert "min_desktop_version" in data
    assert "min_mobile_version" in data
    assert "mobile" in data
    mobile = data["mobile"]
    assert mobile["latest_version"]
    assert mobile["min_supported_version"]
    assert mobile["release_channel"] in {"stable", "beta", "development"}
    assert body["request_id"]
    assert body["correlation_id"]
    assert body["timestamp"]


@pytest.mark.asyncio
async def test_api_capabilities(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert data["installed_version"] == "0.1.0"
    assert data["modules"]["inventory"] is True
    assert data["modules"]["sales"] is True
    assert "ai" in data
    assert "feature_flags" in data
    assert isinstance(data["tally_enabled"], bool)
    assert isinstance(data["backup_enabled"], bool)
    assert data["reports_enabled"] is True
