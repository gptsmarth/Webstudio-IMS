"""M14G production certification validation tests."""

from __future__ import annotations

import pytest

from webstudio_backend.services.production_certification_validation_service import (
    CONCURRENT_SESSIONS_TARGET,
    INVENTORY_SCALE_TARGET,
    SALES_SCALE_TARGET,
    ProductionCertificationValidationService,
)

SECURITY_CHECK_KEYS = {
    "authentication",
    "authorization",
    "jwt",
    "rbac",
    "password_policy",
    "argon2",
    "backup_encryption",
    "ai_keys",
    "tally_security",
    "security_headers",
}

PERFORMANCE_CHECK_KEYS = {
    "inventory_10000",
    "sales_50000",
    "concurrent_sessions_100",
    "slow_request_observability",
}

INFRASTRUCTURE_CHECK_KEYS = {
    "https_readiness",
    "lan_deployment",
    "postgresql_locality",
    "startup_validation",
    "rate_limiting",
}


@pytest.mark.asyncio
async def test_production_certification_includes_m14g_checks(db_session, test_settings) -> None:
    service = ProductionCertificationValidationService(db_session, test_settings)
    report = await service.run_certification()
    security_keys = {check.key for check in report.security.checks}
    performance_keys = {check.key for check in report.performance.checks}
    infrastructure_keys = {check.key for check in report.infrastructure.checks}

    assert SECURITY_CHECK_KEYS.issubset(security_keys)
    assert PERFORMANCE_CHECK_KEYS.issubset(performance_keys)
    assert INFRASTRUCTURE_CHECK_KEYS.issubset(infrastructure_keys)
    assert report.overall_status in {"passed", "warning", "failed"}
    assert report.performance.targets["inventory_items"] == INVENTORY_SCALE_TARGET
    assert report.performance.targets["sales"] == SALES_SCALE_TARGET
    assert report.performance.targets["concurrent_sessions"] == CONCURRENT_SESSIONS_TARGET


@pytest.mark.asyncio
async def test_production_certification_report_payload(db_session, test_settings) -> None:
    service = ProductionCertificationValidationService(db_session, test_settings)
    payload = await service.build_certification_report()
    assert payload["validation_scope"] == "production_certification"
    assert payload["security_certification"]["name"] == "security"
    assert payload["performance_certification"]["name"] == "performance"
    assert payload["infrastructure_certification"]["name"] == "infrastructure"
    assert payload["security_certification_doc"] == "docs/milestones/m14/SECURITY_CERTIFICATION.md"


@pytest.mark.asyncio
async def test_performance_indexes_checked(db_session, test_settings) -> None:
    service = ProductionCertificationValidationService(db_session, test_settings)
    report = await service.run_certification()
    index_checks = [check for check in report.performance.checks if check.key.startswith("indexes_")]
    assert index_checks
    assert all(check.status in {"passed", "failed"} for check in index_checks)
