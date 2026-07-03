"""M14C production Tally validation tests."""

from __future__ import annotations

import pytest

from webstudio_backend.services.tally_production_validation_service import (
    TallyProductionValidationService,
)

PRODUCTION_TALLY_CHECK_KEYS = {
    "xml_request_generation",
    "incremental_synchronization",
    "guid_checkpoint",
    "last_synchronization_timestamp",
    "recovery_after_server_restart",
    "recovery_after_tally_restart",
    "offline_xml_replay",
    "duplicate_prevention",
    "manual_synchronization",
    "automatic_scheduler",
    "configurable_polling_interval",
    "dashboard_synchronization_status",
}


@pytest.mark.asyncio
async def test_production_tally_validation_includes_m14c_checks(db_session) -> None:
    service = TallyProductionValidationService(db_session)
    report = await service.run_production_validation(assume_live_tally=False)
    keys = {check.key for check in report.checks}
    assert PRODUCTION_TALLY_CHECK_KEYS.issubset(keys)
    assert report.overall_status in {"passed", "warning", "failed"}
    assert report.validation_checklist


@pytest.mark.asyncio
async def test_production_tally_report_includes_dashboard_metadata(db_session) -> None:
    service = TallyProductionValidationService(db_session)
    payload = await service.build_production_report(assume_live_tally=False)
    assert payload["validation_scope"] == "production"
    assert payload["validation_checklist"]
    assert payload["xml_verification_script"] == "tools/scripts/uat_analyze_tally_xml.py"
    assert payload["production_validation_script"] == "infra/windows/validate-production-tally.ps1"
    assert "dashboard_operational" in payload
