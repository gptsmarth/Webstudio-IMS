"""M14F production acceptance validation tests."""

from __future__ import annotations

import pytest

from webstudio_backend.services.production_acceptance_validation_service import (
    STOCK_MANAGER_TEMPLATE,
    UAT_CHECKLIST,
    ProductionAcceptanceValidationService,
)

ROLE_CHECK_KEYS = {
    "role_administrator",
    "role_salesperson",
    "role_stock_manager",
    "role_custom_access",
}

FUNCTIONAL_CHECK_KEYS = {
    "module_inventory",
    "module_sales",
    "module_catalogue",
    "module_reports",
    "module_notifications",
    "module_audit",
    "module_backup",
    "module_restore",
    "module_ai",
    "module_tally",
    "module_global_search",
    "module_offline_mode",
    "module_synchronization",
    "module_auto_update",
    "module_rollback",
}


@pytest.mark.asyncio
async def test_production_acceptance_includes_m14f_checks(db_session, test_settings) -> None:
    service = ProductionAcceptanceValidationService(db_session, test_settings)
    report = await service.run_acceptance_validation()
    keys = {check.key for check in report.checks}
    assert ROLE_CHECK_KEYS.issubset(keys)
    assert FUNCTIONAL_CHECK_KEYS.issubset(keys)
    assert report.overall_status in {"passed", "warning", "failed"}
    assert len(report.uat_checklist) == len(UAT_CHECKLIST)


@pytest.mark.asyncio
async def test_production_acceptance_role_matrix(db_session, test_settings) -> None:
    service = ProductionAcceptanceValidationService(db_session, test_settings)
    payload = await service.build_acceptance_report()
    assert payload["validation_scope"] == "production_acceptance"
    assert payload["role_matrix"]
    role_ids = {row["role_id"] for row in payload["role_matrix"]}
    assert "main_admin" in role_ids
    assert "salesperson" in role_ids
    assert "stock_manager" in role_ids
    assert payload["role_matrix_validation"] == "docs/milestones/m14/ROLE_MATRIX_VALIDATION.md"


def test_stock_manager_template_is_assignable() -> None:
    from webstudio_backend.core.permissions import validate_assignable_permissions

    validate_assignable_permissions(set(STOCK_MANAGER_TEMPLATE))
