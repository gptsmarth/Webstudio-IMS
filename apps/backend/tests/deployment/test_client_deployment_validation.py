"""M14E client deployment validation tests."""

from __future__ import annotations

import pytest

from webstudio_backend.services.client_deployment_validation_service import (
    CLIENT_ACCEPTANCE_CHECKLIST,
    ClientDeploymentValidationService,
)


DESKTOP_CHECK_KEYS = {
    "desktop_install_exe",
    "desktop_install_dmg",
    "desktop_connect_automatically",
    "desktop_discover_server",
    "desktop_authenticate",
    "desktop_verify_permissions",
}

FLUTTER_CHECK_KEYS = {
    "flutter_install_apk",
    "flutter_connect",
    "flutter_restore_session",
    "flutter_offline_validation",
    "flutter_camera_validation",
    "flutter_barcode_validation",
}

IOS_CHECK_KEYS = {
    "ios_installation_architecture",
    "ios_validate_installation",
}


@pytest.mark.asyncio
async def test_client_deployment_validation_includes_m14e_checks(db_session, test_settings) -> None:
    service = ClientDeploymentValidationService(db_session, test_settings)
    report = await service.run_production_validation()
    keys = {check.key for check in report.checks}
    assert DESKTOP_CHECK_KEYS.issubset(keys)
    assert FLUTTER_CHECK_KEYS.issubset(keys)
    assert IOS_CHECK_KEYS.issubset(keys)
    assert report.overall_status in {"passed", "warning", "failed"}
    assert len(report.acceptance_checklist) == len(CLIENT_ACCEPTANCE_CHECKLIST)


@pytest.mark.asyncio
async def test_client_deployment_report_includes_artifact_paths(db_session, test_settings) -> None:
    service = ClientDeploymentValidationService(db_session, test_settings)
    payload = await service.build_production_report()
    assert payload["validation_scope"] == "production"
    assert payload["artifact_paths"]["desktop_windows_exe"]
    assert payload["artifact_paths"]["mobile_android_apk"]
    assert payload["desktop_deployment_guide"] == "docs/milestones/m14/DESKTOP_DEPLOYMENT_GUIDE.md"
