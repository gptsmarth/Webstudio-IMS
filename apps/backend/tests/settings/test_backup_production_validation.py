"""M14D production backup validation tests."""

from __future__ import annotations

import pytest

from webstudio_backend.services.backup_production_validation_service import (
    PRODUCTION_RESTORE_CHECKLIST,
    BackupProductionValidationService,
)

PRODUCTION_BACKUP_CHECK_KEYS = {
    "automatic_backups",
    "manual_backups",
    "restore_capability",
    "fresh_machine_recovery",
    "database_recovery",
    "configuration_recovery",
    "windows_service_recovery",
    "scheduler_recovery",
    "tally_checkpoint_recovery",
    "release_rollback",
    "backup_integrity",
}


@pytest.mark.asyncio
async def test_production_backup_validation_includes_m14d_checks(
    db_session,
    test_settings,
) -> None:
    service = BackupProductionValidationService(db_session, test_settings)
    report = await service.run_production_validation()
    keys = {check.key for check in report.checks}
    assert PRODUCTION_BACKUP_CHECK_KEYS.issubset(keys)
    assert report.overall_status in {"passed", "warning", "failed"}
    assert len(report.restore_checklist) == len(PRODUCTION_RESTORE_CHECKLIST)


@pytest.mark.asyncio
async def test_production_backup_report_includes_metadata(db_session, test_settings) -> None:
    service = BackupProductionValidationService(db_session, test_settings)
    payload = await service.build_production_report()
    assert payload["validation_scope"] == "production"
    assert payload["restore_checklist"]
    assert payload["disaster_recovery_script"] == "infra/windows/validate-production-backup.ps1"
    assert payload["technical_reference"] == "docs/internal/BACKUP_RESTORE.md"
