"""Platform version and capabilities endpoint tests."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from webstudio_backend.app import create_app
from webstudio_backend.core.config import Settings


@pytest.fixture
def platform_test_settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql+asyncpg://webstudio_app:webstudio_app@localhost:5432/webstudio_test",
        log_json=True,
    )


@pytest.fixture
def client(platform_test_settings: Settings) -> TestClient:
    app = create_app(platform_test_settings)
    with TestClient(app) as test_client:
        yield test_client


def test_api_version(client: TestClient) -> None:
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["backend_version"] == "0.1.0"
    assert body["data"]["api_version"] == "1.0"
    assert "schema_version" in body["data"]
    assert "build_version" in body["data"]
    assert "min_desktop_version" in body["data"]
    assert "min_mobile_version" in body["data"]
    assert body["request_id"]
    assert body["correlation_id"]
    assert body["timestamp"]


def test_api_capabilities(client: TestClient) -> None:
    response = client.get("/api/v1/capabilities")
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
