"""Network discovery and host validation tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from webstudio_backend.core.config import Settings
from webstudio_backend.core.network.host_validation import (
    HostValidationError,
    normalize_server_host,
)
from webstudio_backend.services.mdns_advertisement_service import MdnsAdvertisementService


def test_normalize_accepts_ipv4() -> None:
    assert normalize_server_host("192.168.1.10") == "192.168.1.10"


def test_normalize_accepts_hostname() -> None:
    assert normalize_server_host("WEBSTUDIO-SERVER") == "webstudio-server"


def test_normalize_accepts_mdns_local() -> None:
    assert normalize_server_host("WEBSTUDIO-SERVER.local") == "webstudio-server.local"


def test_normalize_rejects_empty() -> None:
    with pytest.raises(HostValidationError):
        normalize_server_host("   ")


@pytest.mark.asyncio
async def test_discovery_health(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/discovery/health")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "online" in data
    assert data["backend_version"] == "0.1.0"
    assert data["api_version"] == "1.0"
    assert data["database_status"] in {"ok", "failed", "unknown"}
    assert "jwt" not in response.text.lower()
    assert "secret" not in response.text.lower()


@pytest.mark.asyncio
async def test_validate_host_endpoint(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/discovery/validate-host", params={"host": "127.0.0.1"})
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["valid"] is True
    assert body["host"] == "127.0.0.1"


@pytest.mark.asyncio
async def test_validate_host_rejects_invalid(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/discovery/validate-host", params={"host": "bad host!"})
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["valid"] is False


def test_mdns_service_skipped_in_test_env() -> None:
    settings = Settings(app_env="test", mdns_enabled=True)
    service = MdnsAdvertisementService(settings)
    assert service.enabled is False
    service.start(company_name="WEBSTUDIO")
    service.stop()


def test_mdns_txt_record_keys() -> None:
    from webstudio_backend.core.network.discovery_constants import DiscoveryTxtKey

    keys = {item.value for item in DiscoveryTxtKey}
    assert "server_name" in keys
    assert "company_name" in keys
    assert "backend_version" in keys
    assert "jwt_secret" not in keys
