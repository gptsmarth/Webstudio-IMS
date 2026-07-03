"""Network administration API tests."""

from __future__ import annotations

import pytest

from webstudio_backend.services.network_validation_service import NetworkValidationService


@pytest.mark.asyncio
async def test_network_validation_includes_core_checks(db_session, test_settings) -> None:
    service = NetworkValidationService(db_session, test_settings)
    report = await service.run_admin_validation(mdns_active=False)
    keys = {check.key for check in report.checks}
    assert "server" in keys
    assert "database" in keys
    assert "api" in keys
    assert "firewall" in keys
    assert "ports" in keys
    assert "ai" in keys
    assert "tally" in keys
    assert "backup_folders" in keys
    assert report.topology
    assert report.overall_status in {"passed", "warning", "failed"}


@pytest.mark.asyncio
async def test_network_report_includes_discovery_candidates(db_session, test_settings) -> None:
    service = NetworkValidationService(db_session, test_settings)
    payload = await service.build_network_report(mdns_active=True)
    assert "discovery_candidates" in payload
    assert payload["mdns_active"] is True


PRODUCTION_CHECK_KEYS = {
    "static_server_ip",
    "lan_accessibility",
    "multi_wifi_access_points",
    "same_subnet_communication",
    "desktop_connectivity",
    "android_connectivity",
    "ios_connectivity",
    "windows_firewall",
    "port_availability",
    "postgresql_connectivity",
    "api_reachability",
    "server_discovery",
    "automatic_reconnect",
}


@pytest.mark.asyncio
async def test_production_network_validation_includes_m14b_checks(db_session, test_settings) -> None:
    service = NetworkValidationService(db_session, test_settings)
    report = await service.run_production_network_validation(mdns_active=False)
    keys = {check.key for check in report.checks}
    assert PRODUCTION_CHECK_KEYS.issubset(keys)
    assert report.overall_status in {"passed", "warning", "failed"}


@pytest.mark.asyncio
async def test_production_network_report_includes_infrastructure_checklist(
    db_session,
    test_settings,
) -> None:
    service = NetworkValidationService(db_session, test_settings)
    payload = await service.build_production_network_report(mdns_active=False)
    assert payload["validation_scope"] == "production"
    assert payload["infrastructure_checklist"]
    assert payload["firewall_script"] == "infra/windows/configure-firewall.ps1"
    assert payload["validation_script"] == "infra/windows/validate-production-network.ps1"
