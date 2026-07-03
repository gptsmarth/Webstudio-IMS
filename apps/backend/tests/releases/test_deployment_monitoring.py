"""Enterprise deployment monitoring analytics tests (M13I)."""

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
from webstudio_backend.infrastructure.database.models.release_deployment_run import ReleaseDeploymentRun
from webstudio_backend.infrastructure.database.models.release_download_job import ReleaseDownloadJob
from webstudio_backend.infrastructure.repositories.client_version_observation_repository import (
    ClientVersionObservationRepository,
)
from webstudio_backend.infrastructure.repositories.release_deployment_run_repository import (
    ReleaseDeploymentRunRepository,
)
from webstudio_backend.infrastructure.repositories.release_download_repository import ReleaseDownloadRepository
from webstudio_backend.services.deployment_monitoring_service import DeploymentMonitoringService


@pytest_asyncio.fixture
async def monitoring_client(
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
async def test_deployment_analytics_endpoint(
    monitoring_client: tuple[AsyncClient, dict[str, str]],
    db_session: AsyncSession,
) -> None:
    client, headers = monitoring_client
    await ClientVersionObservationRepository(db_session).record_observation(
        platform="desktop_windows",
        client_version="0.1.0",
        release_channel="development",
    )
    await ReleaseDownloadRepository(db_session).create_job(
        ReleaseDownloadJob(
            github_release_id=random.randint(900_000, 999_999),
            tag_name="v0.1.0",
            release_version="0.1.0",
            build_number=1,
            release_channel=ReleaseChannel.DEVELOPMENT,
            status=ReleaseDownloadStatus.FAILED,
            attempt_count=2,
            max_attempts=5,
            error_message="network timeout",
        ),
    )
    await ReleaseDeploymentRunRepository(db_session).create(
        ReleaseDeploymentRun(
            release_version="0.1.0",
            build_number=1,
            release_channel=ReleaseChannel.DEVELOPMENT,
            status="completed",
            current_step="deployment_completed",
            steps_json=[
                {
                    "step": "run_health_checks",
                    "status": "completed",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "detail": {"api_health": "ok"},
                },
            ],
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        ),
    )
    await db_session.commit()

    response = await client.get("/api/v1/deployment/center/analytics", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert "summary" in data
    assert "release_downloads" in data
    assert "deployment_durations" in data
    assert "health_check_history" in data
    assert "retry_queue" in data
    assert "github_polling_history" in data
    assert "scheduler_recovery" in data
    assert any(row["client_version"] == "0.1.0" for row in data["desktop_version_distribution"])
    assert any(item.get("kind") == "release_download" for item in data["deployment_failures"])


@pytest.mark.asyncio
async def test_deployment_monitoring_service_summary(
    db_session: AsyncSession,
    test_settings,
) -> None:
    service = DeploymentMonitoringService(db_session, test_settings)
    payload = await service.get_analytics()
    assert payload["generated_at"]
    assert "backup_scheduler_recovery" in payload
    assert "tally_scheduler_recovery" in payload
    assert isinstance(payload["scheduler_recovery"], list)
