"""Client update platform API tests (M13E)."""

from __future__ import annotations

pytest_plugins = ["auth.conftest"]

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.app import create_app
from webstudio_backend.core.config import get_settings
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.infrastructure.database.enums import ReleaseChannel
from webstudio_backend.infrastructure.database.models.software_release import SoftwareRelease
from webstudio_backend.infrastructure.repositories.software_release_repository import (
    SoftwareReleaseRepository,
)


@pytest_asyncio.fixture
async def client_updates_api_client(
    db_session: AsyncSession,
    initialized_system,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(get_settings())

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_client_update_check_public(
    db_session: AsyncSession,
    client_updates_api_client: AsyncClient,
) -> None:
    repo = SoftwareReleaseRepository(db_session)
    await repo.upsert_release(
        SoftwareRelease(
            release_version="0.2.0",
            build_number=2,
            release_channel=ReleaseChannel.DEVELOPMENT,
            git_commit="abc123",
            git_short="abc123",
            build_timestamp=datetime.now(UTC),
            manifest={
                "release_version": "0.2.0",
                "components": {
                    "desktop": {"version": "0.2.0"},
                    "mobile_flutter": {"version": "0.2.0+2"},
                    "backend": {
                        "min_desktop_version": "0.1.0",
                        "min_mobile_version": "0.1.0",
                    },
                },
                "artifacts": {
                    "desktop_windows": "WEBSTUDIO Desktop Setup.exe",
                    "mobile_android": "WEBSTUDIO IMS.apk",
                },
            },
            checksums={"WEBSTUDIO IMS.apk": "a" * 64},
            compatibility_matrix={
                "desktop": {"min_version": "0.1.0"},
                "mobile": {"min_version": "0.1.0"},
            },
            supported_platforms=[
                {"id": "mobile_android", "artifact": "WEBSTUDIO IMS.apk"},
            ],
            is_current=True,
            published_at=datetime.now(UTC),
        ),
    )
    await db_session.commit()

    response = await client_updates_api_client.get(
        "/api/v1/client-updates/check",
        params={
            "platform": "mobile_android",
            "current_version": "0.1.0",
            "channel": "development",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["update_available"] is True
    assert data["latest_version"] == "0.2.0"
    assert data["github_contact_prohibited"] is True
    assert data["distribution_mode"] == "apk_sideload"


@pytest.mark.asyncio
async def test_ios_check_is_notification_only(
    db_session: AsyncSession,
    client_updates_api_client: AsyncClient,
) -> None:
    repo = SoftwareReleaseRepository(db_session)
    await repo.upsert_release(
        SoftwareRelease(
            release_version="0.2.0",
            build_number=2,
            release_channel=ReleaseChannel.DEVELOPMENT,
            git_commit="abc123",
            git_short="abc123",
            build_timestamp=datetime.now(UTC),
            manifest={
                "release_version": "0.2.0",
                "components": {"mobile_flutter": {"version": "0.2.0+2"}},
                "ios": {"app_store_url": "https://apps.apple.com/app/example"},
            },
            checksums={},
            compatibility_matrix={"mobile": {"min_version": "0.1.0"}},
            supported_platforms=[],
            is_current=True,
            published_at=datetime.now(UTC),
        ),
    )
    await db_session.commit()

    response = await client_updates_api_client.get(
        "/api/v1/client-updates/check",
        params={
            "platform": "mobile_ios",
            "current_version": "0.1.0",
            "channel": "development",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["distribution_mode"] == "app_store_notification"
    assert data["artifact"] is None
    assert data["app_store_url"] == "https://apps.apple.com/app/example"


@pytest.mark.asyncio
async def test_client_update_check_up_to_date(
    client_updates_api_client: AsyncClient,
) -> None:
    response = await client_updates_api_client.get(
        "/api/v1/client-updates/check",
        params={
            "platform": "desktop_macos",
            "current_version": "0.2.0",
            "channel": "development",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["update_available"] is False
