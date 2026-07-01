"""Mobile readiness API tests."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from webstudio_backend.app import create_app
from webstudio_backend.core.config import Settings


@pytest.fixture
def mobile_test_settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql+asyncpg://webstudio_app:webstudio_app@localhost:5432/webstudio_test",
        log_json=True,
    )


@pytest.fixture
def client(mobile_test_settings: Settings) -> TestClient:
    app = create_app(mobile_test_settings)
    with TestClient(app) as test_client:
        yield test_client


def test_sync_state_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/sync/state")
    assert response.status_code == 401


def test_search_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/search", params={"q": "asus"})
    assert response.status_code == 401


def test_version_and_capabilities_public(client: TestClient) -> None:
    version = client.get("/api/v1/version")
    assert version.status_code == 200
    capabilities = client.get("/api/v1/capabilities")
    assert capabilities.status_code == 200
    assert "modules" in capabilities.json()["data"]
