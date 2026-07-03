"""Enterprise Rollback Platform tests (M13F)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.database.enums import ReleaseChannel
from webstudio_backend.infrastructure.database.models.software_release import SoftwareRelease
from webstudio_backend.infrastructure.repositories.software_release_repository import SoftwareReleaseRepository
from webstudio_backend.services.enterprise_rollback_engine import ROLLBACK_STEPS, EnterpriseRollbackEngine


@pytest.mark.asyncio
async def test_rollback_steps_order() -> None:
    assert ROLLBACK_STEPS[0] == "create_pre_rollback_safety_backup"
    assert ROLLBACK_STEPS[-1] == "rollback_completed"
    assert "restore_database" in ROLLBACK_STEPS
    assert "notify_connected_clients" in ROLLBACK_STEPS


@pytest.mark.asyncio
async def test_execute_rollback_completes_in_test_mode(db_session: AsyncSession) -> None:
    settings = get_settings()
    settings.app_env = "test"

    repo = SoftwareReleaseRepository(db_session)
    await repo.upsert_release(
        SoftwareRelease(
            release_version="0.2.0",
            build_number=2,
            release_channel=ReleaseChannel.DEVELOPMENT,
            git_commit="abc",
            git_short="abc",
            build_timestamp=datetime.now(UTC),
            is_current=True,
            published_at=datetime.now(UTC),
        ),
    )
    await repo.upsert_release(
        SoftwareRelease(
            release_version="0.1.0",
            build_number=1,
            release_channel=ReleaseChannel.DEVELOPMENT,
            git_commit="def",
            git_short="def",
            build_timestamp=datetime.now(UTC),
            is_current=False,
            published_at=datetime.now(UTC),
        ),
    )
    await db_session.commit()

    engine = EnterpriseRollbackEngine(db_session, settings)
    with patch.object(engine, "_execute_step", new_callable=AsyncMock) as mock_step:
        mock_step.side_effect = [{"step": step} for step in ROLLBACK_STEPS]
        outcome = await engine.execute_rollback(user_id=1)

    assert outcome["status"] == "completed"
    assert outcome["from_release_version"] == "0.2.0"
    assert outcome["to_release_version"] == "0.1.0"
    assert len(outcome["steps"]) == len(ROLLBACK_STEPS)


@pytest.mark.asyncio
async def test_rollback_history_is_permanent(db_session: AsyncSession) -> None:
    settings = get_settings()
    settings.app_env = "test"
    engine = EnterpriseRollbackEngine(db_session, settings)

    repo = SoftwareReleaseRepository(db_session)
    await repo.upsert_release(
        SoftwareRelease(
            release_version="0.2.0",
            build_number=2,
            release_channel=ReleaseChannel.DEVELOPMENT,
            git_commit="abc",
            git_short="abc",
            build_timestamp=datetime.now(UTC),
            is_current=True,
            published_at=datetime.now(UTC),
        ),
    )
    await repo.upsert_release(
        SoftwareRelease(
            release_version="0.1.0",
            build_number=1,
            release_channel=ReleaseChannel.DEVELOPMENT,
            git_commit="def",
            git_short="def",
            build_timestamp=datetime.now(UTC),
            is_current=False,
            published_at=datetime.now(UTC),
        ),
    )
    await db_session.commit()

    with patch.object(engine, "_execute_step", new_callable=AsyncMock) as mock_step:
        mock_step.side_effect = [{"step": step} for step in ROLLBACK_STEPS]
        await engine.execute_rollback(user_id=1)

    history = await engine.list_history(page=1, page_size=10)
    assert history["permanent_history"] is True
    assert history["total_items"] >= 1
