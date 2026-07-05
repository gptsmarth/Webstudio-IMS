"""GitHub release synchronization tests (M13B)."""

from __future__ import annotations

pytest_plugins = ["auth.conftest"]

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.app import create_app
from webstudio_backend.core.config import Settings, get_settings
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.infrastructure.database.enums import ReleaseChannel, ReleaseDownloadStatus
from webstudio_backend.infrastructure.database.models.release_download_job import ReleaseDownloadJob
from webstudio_backend.infrastructure.database.models.software_release import SoftwareRelease
from webstudio_backend.infrastructure.repositories.release_download_repository import (
    ReleaseDownloadRepository,
)
from webstudio_backend.services.github_release_client import GitHubRelease, GitHubReleaseAsset
from webstudio_backend.services.github_release_sync_service import (
    GitHubReleaseSyncService,
    ensure_github_release_sync_enabled,
)


@pytest_asyncio.fixture
async def sync_api_client(
    db_session: AsyncSession,
    initialized_system,
) -> AsyncGenerator[tuple[AsyncClient, dict[str, str]], None]:
    settings = get_settings().model_copy(
        update={
            "github_repo": "webstudio/ims",
            "github_token": "test-token",
            "release_updates_root": "",
        },
    )
    app = create_app(settings)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        headers = await login_headers(client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
        yield client, headers


@pytest.mark.asyncio
async def test_sync_status_requires_auth(db_session: AsyncSession) -> None:
    app = create_app(get_settings())

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/releases/sync/status")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_sync_status_reports_disabled_by_default(
    sync_api_client: tuple[AsyncClient, dict[str, str]],
) -> None:
    client, headers = sync_api_client
    response = await client.get("/api/v1/releases/sync/status", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["enabled"] is False
    assert data["auto_deploy"] is False
    assert data["polling_interval_seconds"] == 900


@pytest.mark.asyncio
async def test_download_history_empty(sync_api_client: tuple[AsyncClient, dict[str, str]]) -> None:
    client, headers = sync_api_client
    response = await client.get("/api/v1/releases/sync/history", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["total_items"] >= 0


@pytest.mark.asyncio
async def test_failed_history_lists_failed_jobs(
    db_session: AsyncSession,
    test_settings: Settings,
    sync_api_client: tuple[AsyncClient, dict[str, str]],
) -> None:
    client, headers = sync_api_client
    repo = ReleaseDownloadRepository(db_session)
    await db_session.execute(
        delete(ReleaseDownloadJob).where(ReleaseDownloadJob.github_release_id == 99001),
    )
    await db_session.commit()
    await repo.create_job(
        ReleaseDownloadJob(
            github_release_id=99001,
            tag_name="v0.2.0",
            release_version="0.2.0",
            build_number=2,
            release_channel=ReleaseChannel.STABLE,
            status=ReleaseDownloadStatus.FAILED,
            bundle_dir="/tmp/v0.2.0",
            error_message="network timeout",
            completed_at=datetime.now(UTC),
        ),
    )
    await db_session.commit()

    response = await client.get("/api/v1/releases/sync/failures", headers=headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total_items"] >= 1
    assert payload["items"][0]["status"] == "failed"
    assert any(item["tag_name"] == "v0.2.0" for item in payload["items"])


@pytest.mark.asyncio
async def test_run_sync_cycle_enqueues_new_release(
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    await db_session.execute(delete(SoftwareRelease))
    await db_session.commit()

    settings = test_settings.model_copy(update={"github_repo": "webstudio/ims"})
    service = GitHubReleaseSyncService(db_session, settings)

    with (
        patch.object(service, "is_enabled", AsyncMock(return_value=True)),
        patch(
            "webstudio_backend.services.github_release_sync_service.GitHubReleaseClient.list_releases",
            AsyncMock(
                return_value=[
                    GitHubRelease(
                        id=42,
                        tag_name="v1.1.0",
                        name="1.1.0",
                        draft=False,
                        prerelease=False,
                        published_at="2026-07-02T00:00:00Z",
                        body="",
                        assets=[
                            GitHubReleaseAsset(
                                id=1,
                                name="version-manifest.json",
                                size=100,
                                download_url="https://example.com/manifest.json",
                                content_type="application/json",
                            ),
                        ],
                        raw={"id": 42},
                    ),
                ],
            ),
        ),
        patch.object(service, "_process_job", AsyncMock(return_value="completed")),
    ):
        result = await service.run_sync_cycle()

    assert result["status"] == "ok"
    assert result["discovered"] == 1
    job = await ReleaseDownloadRepository(db_session).find_job_by_github_release(
        github_release_id=42,
        channel=ReleaseChannel(settings.release_channel),
    )
    assert job is not None
    assert job.tag_name == "v1.1.0"
    assert job.status == ReleaseDownloadStatus.QUEUED


@pytest.mark.asyncio
async def test_ensure_github_release_sync_enabled_when_repo_configured(
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    from webstudio_backend.infrastructure.repositories.system_setting_repository import (
        SystemSettingRepository,
    )

    settings = test_settings.model_copy(update={"github_repo": "webstudio/ims"})
    enabled = await ensure_github_release_sync_enabled(db_session, settings)
    await db_session.commit()

    assert enabled is True
    assert await SystemSettingRepository(db_session).get_bool("github_release_sync_enabled") is True
