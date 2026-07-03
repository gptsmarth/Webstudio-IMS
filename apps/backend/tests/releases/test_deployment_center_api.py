"""Deployment Center API tests (M13C)."""

from __future__ import annotations

pytest_plugins = ["auth.conftest"]

import random
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.app import create_app
from webstudio_backend.core.config import get_settings
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.infrastructure.database.enums import ReleaseChannel, ReleaseDownloadStatus
from webstudio_backend.infrastructure.database.models.release_download_job import ReleaseDownloadJob
from webstudio_backend.infrastructure.repositories.release_download_repository import ReleaseDownloadRepository


@pytest_asyncio.fixture
async def deployment_center_client(
    db_session: AsyncSession,
    initialized_system,
) -> AsyncGenerator[tuple[AsyncClient, dict[str, str]], None]:
    app = create_app(get_settings())

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = await login_headers(client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
        yield client, headers


@pytest.mark.asyncio
async def test_deployment_dashboard_requires_auth(db_session: AsyncSession) -> None:
    app = create_app(get_settings())

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/deployment/center/dashboard")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_deployment_dashboard_returns_fields(
    deployment_center_client: tuple[AsyncClient, dict[str, str]],
) -> None:
    client, headers = deployment_center_client
    response = await client.get("/api/v1/deployment/center/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert "current_version" in data
    assert "latest_version" in data
    assert data["auto_deploy"] is False
    assert "deployment_status" in data


@pytest.mark.asyncio
async def test_deploy_requires_administrator_approval(
    db_session: AsyncSession,
    deployment_center_client: tuple[AsyncClient, dict[str, str]],
) -> None:
    client, headers = deployment_center_client
    repo = ReleaseDownloadRepository(db_session)
    github_id = random.randint(100_000, 999_999)
    job = await repo.create_job(
        ReleaseDownloadJob(
            github_release_id=github_id,
            tag_name="v88.88.88",
            release_version="88.88.88",
            build_number=8888,
            release_channel=ReleaseChannel.DEVELOPMENT,
            status=ReleaseDownloadStatus.COMPLETED,
            bundle_dir="/tmp/v0.2.0",
            manifest_validated=True,
            checksums_verified=True,
            completed_at=datetime.now(UTC),
        ),
    )
    await db_session.commit()

    denied = await client.post(
        "/api/v1/deployment/center/deploy",
        headers=headers,
        json={"job_id": job.id, "administrator_approved": False},
    )
    assert denied.status_code == 422

    missing_catalog = await client.post(
        "/api/v1/deployment/center/deploy",
        headers=headers,
        json={"job_id": job.id, "administrator_approved": True},
    )
    assert missing_catalog.status_code == 422
