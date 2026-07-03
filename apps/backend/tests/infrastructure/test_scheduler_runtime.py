"""Tests for scheduler runtime persistence across restarts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from webstudio_backend.services.scheduler_runtime_service import SchedulerRuntimeService


@pytest.mark.asyncio
async def test_record_run_sets_next_run_at(db_session) -> None:
    service = SchedulerRuntimeService(db_session)
    before = datetime.now(UTC)
    await service.record_run("backup", status="completed", interval_seconds=900)
    await db_session.commit()

    remaining = await service.seconds_until_next_run("backup", interval_seconds=900)
    assert remaining > 0
    assert remaining <= 900

    row = await service._repo.get("backup")
    assert row is not None
    assert row.last_run_status == "completed"
    assert row.last_run_at is not None
    assert row.next_run_at is not None
    assert row.next_run_at >= before + timedelta(seconds=899)


@pytest.mark.asyncio
async def test_seconds_until_next_run_resumes_from_persisted_state(db_session) -> None:
    service = SchedulerRuntimeService(db_session)
    row = await service._repo.get_or_create("tally_sync", default_interval_seconds=300)
    row.last_run_at = datetime.now(UTC) - timedelta(seconds=250)
    row.next_run_at = datetime.now(UTC) + timedelta(seconds=50)
    row.interval_seconds = 300
    await db_session.flush()

    remaining = await service.seconds_until_next_run("tally_sync", interval_seconds=300)
    assert 40 <= remaining <= 60


@pytest.mark.asyncio
async def test_restore_all_returns_scheduler_keys(db_session) -> None:
    service = SchedulerRuntimeService(db_session)
    restored = await service.restore_all()
    await db_session.commit()
    assert "tally_sync" in restored
    assert "backup" in restored
    assert "notification_delivery" in restored
    assert "maintenance" in restored
