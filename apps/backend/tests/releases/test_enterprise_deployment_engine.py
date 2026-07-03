"""Enterprise Deployment Engine unit tests (M13D)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.database.enums import ReleaseChannel
from webstudio_backend.infrastructure.database.models.software_release import SoftwareRelease
from webstudio_backend.infrastructure.repositories.software_release_repository import SoftwareReleaseRepository
from webstudio_backend.services.deployment_platform_adapter import DeploymentPlatformAdapter
from webstudio_backend.services.enterprise_deployment_engine import DEPLOYMENT_STEPS, EnterpriseDeploymentEngine


@pytest.fixture
def temp_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "v0.2.0"
    bundle.mkdir()
    manifest = {
        "release_version": "0.2.0",
        "build_number": 2,
        "release_channel": "development",
        "git_commit": "abc123",
        "artifacts": [],
    }
    (bundle / "version-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle


@pytest.mark.asyncio
async def test_deployment_steps_order() -> None:
    assert DEPLOYMENT_STEPS[0] == "create_database_backup"
    assert DEPLOYMENT_STEPS[-1] == "deployment_completed"
    assert "run_health_checks" in DEPLOYMENT_STEPS
    assert "notify_desktop_clients" in DEPLOYMENT_STEPS


@pytest.mark.asyncio
async def test_execute_deploy_completes_with_mocked_backup(
    db_session: AsyncSession,
    temp_bundle: Path,
) -> None:
    settings = get_settings()
    settings.app_env = "test"

    release_repo = SoftwareReleaseRepository(db_session)
    await release_repo.upsert_release(
        SoftwareRelease(
            release_version="0.2.0",
            build_number=2,
            release_channel=ReleaseChannel.DEVELOPMENT,
            git_commit="abc123",
            git_short="abc123",
            build_timestamp=datetime.now(UTC),
            is_current=False,
            published_at=datetime.now(UTC),
        ),
    )
    await release_repo.upsert_release(
        SoftwareRelease(
            release_version="0.1.0",
            build_number=1,
            release_channel=ReleaseChannel.DEVELOPMENT,
            git_commit="def456",
            git_short="def456",
            build_timestamp=datetime.now(UTC),
            is_current=True,
            published_at=datetime.now(UTC),
        ),
    )
    await db_session.commit()

    platform = DeploymentPlatformAdapter(settings)
    engine = EnterpriseDeploymentEngine(db_session, settings, platform=platform)

    backup_result = MagicMock()
    backup_result.id = 99
    backup_result.filename = "webstudio-backup-test.tar.gz"

    with patch.object(
        engine,
        "_execute_step",
        new_callable=AsyncMock,
    ) as mock_step:
        mock_step.side_effect = [
            {"backup_id": 99, "filename": backup_result.filename},
            *[{"step": step} for step in DEPLOYMENT_STEPS[1:]],
        ]
        with patch(
            "webstudio_backend.services.enterprise_deployment_engine.BackupEngine.create_backup",
            new_callable=AsyncMock,
            return_value=backup_result,
        ):
            outcome = await engine.execute_deploy(
                job_id=1,
                user_id=1,
                release_version="0.2.0",
                build_number=2,
                release_channel=ReleaseChannel.DEVELOPMENT,
                bundle_dir=str(temp_bundle),
            )

    assert outcome["status"] == "completed"
    assert outcome["release_version"] == "0.2.0"
    assert len(outcome["steps"]) == len(DEPLOYMENT_STEPS)


@pytest.mark.asyncio
async def test_execute_deploy_rolls_back_on_failure(
    db_session: AsyncSession,
    temp_bundle: Path,
) -> None:
    settings = get_settings()
    settings.app_env = "test"

    release_repo = SoftwareReleaseRepository(db_session)
    current = await release_repo.upsert_release(
        SoftwareRelease(
            release_version="0.1.0",
            build_number=1,
            release_channel=ReleaseChannel.DEVELOPMENT,
            git_commit="def456",
            git_short="def456",
            build_timestamp=datetime.now(UTC),
            is_current=True,
            published_at=datetime.now(UTC),
        ),
    )
    await release_repo.upsert_release(
        SoftwareRelease(
            release_version="0.2.0",
            build_number=2,
            release_channel=ReleaseChannel.DEVELOPMENT,
            git_commit="abc123",
            git_short="abc123",
            build_timestamp=datetime.now(UTC),
            is_current=False,
            published_at=datetime.now(UTC),
        ),
    )
    await db_session.commit()

    platform = DeploymentPlatformAdapter(settings)
    engine = EnterpriseDeploymentEngine(db_session, settings, platform=platform)

    async def failing_execute_step(run, step, *, snapshot_root, user_id):
        if step == "validate_package":
            raise ValueError("manifest checksum mismatch")
        return {"ok": True}

    with patch.object(engine, "_execute_step", side_effect=failing_execute_step):
        with patch.object(engine, "_rollback", new_callable=AsyncMock) as mock_rollback:
            with pytest.raises(ValueError, match="manifest checksum mismatch"):
                await engine.execute_deploy(
                    job_id=2,
                    user_id=1,
                    release_version="0.2.0",
                    build_number=2,
                    release_channel=ReleaseChannel.DEVELOPMENT,
                    bundle_dir=str(temp_bundle),
                )
            mock_rollback.assert_awaited_once()

    latest = await engine.get_latest_run()
    assert latest is not None
    assert latest["status"] in {"rolling_back", "rolled_back", "failed"}
    assert current.id == latest["previous_release_id"]
