"""Health endpoint tests."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from webstudio_backend.app import create_app
from webstudio_backend.core.config import Settings


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql+asyncpg://webstudio_app:webstudio_app@localhost:5432/webstudio_test",
        log_json=True,
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    app = create_app(test_settings)
    with TestClient(app) as test_client:
        yield test_client


def test_health_live(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert response.headers["API-Version"] == "1.0"
    assert "X-Request-ID" in response.headers
    assert "X-Correlation-ID" in response.headers


def test_health_version(client: TestClient) -> None:
    response = client.get("/health/version")
    assert response.status_code == 200
    assert response.json()["data"]["api_version"] == "1.0"


def test_metadata_info(client: TestClient) -> None:
    response = client.get("/metadata/info")
    assert response.status_code == 200
    assert response.json()["data"]["service"] == "webstudio-ims-api"
