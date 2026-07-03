"""Enterprise release API tests (M13)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.app import create_app
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.infrastructure.database.enums import ReleaseChannel
from webstudio_backend.infrastructure.database.models.software_release import SoftwareRelease
from webstudio_backend.infrastructure.repositories.software_release_repository import (
    SoftwareReleaseRepository,
)
from webstudio_backend.services.release_catalog_loader import release_from_bundle_dir


@pytest_asyncio.fixture
async def release_api_client(
    db_session: AsyncSession,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient, None]:
    settings = test_settings.model_copy(
        update={
            "release_catalog_root": "",
            "release_channel": ReleaseChannel.DEVELOPMENT.value,
            "build_number": 1,
        },
    )
    app = create_app(settings)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_releases_current_bootstraps_catalog(
    release_api_client: AsyncClient,
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    bundle_dir = repo_root / "release" / "v0.1.0"
    if bundle_dir.is_dir():
        release = release_from_bundle_dir(
            bundle_dir,
            channel=ReleaseChannel.DEVELOPMENT,
            mark_current=True,
        )
        assert release is not None
        await SoftwareReleaseRepository(db_session).upsert_release(release)
        await db_session.commit()

    response = await release_api_client.get("/api/v1/releases/current")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["release_version"] == test_settings.app_version
    assert data["release_channel"] in {"development", "beta", "stable"}
    assert "compatibility_matrix" in data
    assert "checksums" in data
    assert "supported_platforms" in data
    assert "build_number" in data
    assert "git_commit" in data
    assert "database_revision" in data
    assert "release_date" in data
    assert "version_identity" in data


@pytest.mark.asyncio
async def test_releases_latest_and_history(
    release_api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    repo = SoftwareReleaseRepository(db_session)
    for build_number in (1, 2):
        await repo.upsert_release(
            SoftwareRelease(
                release_version="0.1.0",
                build_number=build_number,
                release_channel=ReleaseChannel.DEVELOPMENT,
                git_commit=f"commit{build_number}",
                git_short=f"c{build_number}",
                build_timestamp=datetime.now(UTC),
                manifest={"release_version": "0.1.0"},
                checksums={"WEBSTUDIO Desktop Setup.exe": "abc123"},
                compatibility_matrix={"desktop": {"min_version": "0.1.0"}},
                supported_platforms=[{"id": "desktop_windows", "artifact": "WEBSTUDIO Desktop Setup.exe"}],
                is_current=build_number == 2,
            ),
        )
    await db_session.commit()

    latest = await release_api_client.get("/api/v1/releases/latest", params={"channel": "development"})
    assert latest.status_code == 200
    assert latest.json()["data"]["build_number"] == 2

    history = await release_api_client.get(
        "/api/v1/releases/history",
        params={"channel": "development", "page": 1, "page_size": 10},
    )
    assert history.status_code == 200
    payload = history.json()["data"]
    assert payload["total_items"] >= 2
    assert len(payload["items"]) >= 2
