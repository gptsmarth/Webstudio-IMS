"""M14J final production handover validation tests."""

from __future__ import annotations

import pytest

from webstudio_backend.services.final_production_handover_validation_service import (
    TARGET_CHANNEL,
    TARGET_VERSION,
    FinalProductionHandoverValidationService,
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
    "release_version_1_0_0",
}


@pytest.mark.asyncio
async def test_production_handover_includes_m14j_checks(db_session, test_settings) -> None:
    service = FinalProductionHandoverValidationService(db_session, test_settings)
    report = await service.run_handover_validation()
    keys = {check.key for check in report.checks}
    assert HANDOVER_CHECK_KEYS.issubset(keys)
    assert report.target_version == TARGET_VERSION
    assert report.target_channel == TARGET_CHANNEL
    assert report.overall_status in {"passed", "warning", "failed"}


@pytest.mark.asyncio
async def test_production_handover_version_1_0_0(db_session, test_settings) -> None:
    service = FinalProductionHandoverValidationService(db_session, test_settings)
    payload = await service.build_handover_report()
    assert payload["validation_scope"] == "production_handover"
    assert payload["target_version"] == "1.0.0"
    assert payload["version_label"] == "WEBSTUDIO IMS v1.0.0 — PRODUCTION READY"
    version_check = next(c for c in payload["checks"] if c["key"] == "release_version_1_0_0")
    assert version_check["status"] == "passed"
    assert payload["production_ready"] is True


@pytest.mark.asyncio
async def test_production_handover_milestone_matrix(db_session, test_settings) -> None:
    service = FinalProductionHandoverValidationService(db_session, test_settings)
    report = await service.run_handover_validation()
    assert report.milestone_completion["14A"] == "complete"
    assert report.milestone_completion["14I"] == "complete"
    if report.production_ready:
        assert report.milestone_completion["14J"] == "complete"
