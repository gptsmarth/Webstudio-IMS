"""Regression tests for production API security middleware."""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from webstudio_backend.app import create_app
from webstudio_backend.core.config import Settings


async def test_rate_limits_preserve_desktop_cors_and_https_headers() -> None:
    app = create_app(
        Settings(
            app_env="test",
            rate_limit_enabled=True,
            rate_limit_per_minute=2,
            auth_rate_limit_per_minute=1,
        )
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://ims.example.test"
    ) as client:
        headers = {"Origin": "app://."}
        login = await client.post("/api/v1/auth/login", headers=headers)
        assert login.status_code == 422

        blocked = await client.post("/api/v1/auth/main-admin/recover-password/", headers=headers)
        assert blocked.status_code == 429
        assert blocked.headers["Retry-After"].isdigit()
        assert blocked.headers["Access-Control-Allow-Origin"] == "app://."
        assert blocked.headers["Strict-Transport-Security"] == "max-age=31536000"
        assert blocked.json()["error"]["code"] == "RATE_LIMITED"

        assert (await client.get("/health/live")).status_code == 200
        assert (await client.get("/health/live")).status_code == 429


async def test_production_schema_and_other_desktop_origins_are_private() -> None:
    app = create_app(Settings(app_env="production", jwt_secret="a" * 32))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://ims.example.test"
    ) as client:
        assert (await client.get("/openapi.json")).status_code == 404
        response = await client.get("/health/live", headers={"Origin": "app://other"})
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" not in response.headers
        assert "Strict-Transport-Security" not in response.headers
