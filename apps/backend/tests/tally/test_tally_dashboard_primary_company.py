"""Dashboard must follow configured Tally company, not alphabetical first row."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import SettingValueType
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import (
    TallyCompanySyncRepository,
)
from webstudio_backend.infrastructure.repositories.tally_sync_history_repository import (
    TallySyncHistoryRepository,
)
from webstudio_backend.services.tally_dashboard_service import TallyDashboardService

FULL_NAME = "WEBSTUDIO - (from 1-Apr-2022) - (from 1-Apr-25) - (from 1-Apr-26)"


@pytest.mark.asyncio
async def test_dashboard_uses_configured_company_not_alphabetical_first(
    db_session: AsyncSession,
) -> None:
    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "tally_enabled",
        "true",
        value_type=SettingValueType.BOOLEAN,
        updated_by_user_id=None,
    )
    await settings.set_value(
        "tally_company_name",
        FULL_NAME,
        value_type=SettingValueType.STRING,
        updated_by_user_id=None,
    )

    repo = TallyCompanySyncRepository(db_session)
    legacy = await repo.get_or_create("WEBSTUDIO")
    legacy.last_successful_sync_at = datetime(2026, 7, 4, 8, 53, tzinfo=UTC)
    legacy.is_active = True

    primary = await repo.get_or_create(FULL_NAME)
    primary.last_successful_sync_at = datetime(2026, 7, 4, 13, 0, tzinfo=UTC)
    primary.is_active = True
    await db_session.commit()

    dashboard = await TallyDashboardService(db_session).build_dashboard()
    assert dashboard["last_successful_sync_at"] == primary.last_successful_sync_at.isoformat()


@pytest.mark.asyncio
async def test_sync_history_uses_configured_company(db_session: AsyncSession) -> None:
    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "tally_enabled",
        "true",
        value_type=SettingValueType.BOOLEAN,
        updated_by_user_id=None,
    )
    await settings.set_value(
        "tally_company_name",
        FULL_NAME,
        value_type=SettingValueType.STRING,
        updated_by_user_id=None,
    )

    repo = TallyCompanySyncRepository(db_session)
    await repo.get_or_create("WEBSTUDIO")
    primary = await repo.get_or_create(FULL_NAME)
    history_repo = TallySyncHistoryRepository(db_session)
    run = await history_repo.create_started(
        company_sync_id=primary.id,
        sync_run_id=__import__("uuid").uuid4(),
        correlation_id="configured-company-run",
    )
    await history_repo.finalize(
        run,
        status="success",
        invoices_checked=3,
        invoices_imported=2,
        invoices_skipped=1,
        errors_count=0,
    )
    await db_session.commit()

    rows = await TallyDashboardService(db_session).build_sync_history(limit=5)
    assert rows
    assert rows[0]["invoices_checked"] == 3
    assert rows[0]["invoices_imported"] == 2
