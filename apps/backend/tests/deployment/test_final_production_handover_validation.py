"""M14J final production handover validation tests."""

from __future__ import annotations

import pytest

from webstudio_backend.core.version_catalog import load_version_catalog
from webstudio_backend.services.final_production_handover_validation_service import (
    TARGET_CHANNEL,
    FinalProductionHandoverValidationService,
    release_version_check_key,
    target_release_version,
)

HANDOVER_CHECK_KEYS = {
    "server_installation",
    "desktop_installation",
    "android_installation",
    "ios_installation",
    "desktop_dmg",
    "windows_service",
    "database",
    "backup",
    "restore",
    "scheduler",
    "notifications",
    "tally",
    "ai",
    "github_release",
    "deployment_center",
    "rollback",
    "automatic_updates",
}


@pytest.mark.asyncio
async def test_production_handover_includes_m14j_checks(db_session, test_settings) -> None:
    service = FinalProductionHandoverValidationService(db_session, test_settings)
    report = await service.run_handover_validation()
    keys = {check.key for check in report.checks}
    target_version = target_release_version()
    assert HANDOVER_CHECK_KEYS.issubset(keys)
    assert release_version_check_key(target_version) in keys
    assert report.target_version == target_version
    assert report.target_channel == TARGET_CHANNEL
    assert report.overall_status in {"passed", "warning", "failed"}


@pytest.mark.asyncio
async def test_production_handover_target_release_version(db_session, test_settings) -> None:
    catalog = load_version_catalog()
    target_version = target_release_version()
    service = FinalProductionHandoverValidationService(db_session, test_settings)
    payload = await service.build_handover_report()
    assert payload["validation_scope"] == "production_handover"
    assert payload["target_version"] == target_version
    assert payload["version_label"] == f"WEBSTUDIO IMS v{target_version} — PRODUCTION READY"
    version_check = next(
        c for c in payload["checks"] if c["key"] == release_version_check_key(target_version)
    )
    assert version_check["status"] == "passed"
    assert payload["verified_version"] == catalog.version
    assert payload["production_ready"] is True


@pytest.mark.asyncio
async def test_production_handover_milestone_matrix(db_session, test_settings) -> None:
    service = FinalProductionHandoverValidationService(db_session, test_settings)
    report = await service.run_handover_validation()
    assert report.milestone_completion["14A"] == "complete"
    assert report.milestone_completion["14I"] == "complete"
    if report.production_ready:
        assert report.milestone_completion["14J"] == "complete"
