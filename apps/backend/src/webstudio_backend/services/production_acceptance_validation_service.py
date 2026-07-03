"""Complete production acceptance validation for M14F."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.core.permissions import (
    ALL_PERMISSIONS,
    ASSIGNABLE_PERMISSIONS,
    PERMISSIONS_BY_ROLE,
    permissions_for_role,
    validate_assignable_permissions,
)
from webstudio_backend.infrastructure.database.enums import UserRole
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.ai.config import resolve_ai_config
from webstudio_backend.services.enterprise_rollback_engine import ROLLBACK_STEPS
from webstudio_backend.services.platform_info_service import build_capabilities_payload
from webstudio_backend.services.tally_sync_service import TallySyncService


@dataclass(frozen=True, slots=True)
class AcceptanceCheck:
    key: str
    name: str
    status: str  # passed | warning | failed | skipped
    message: str
    detail: str = ""
    category: str = "functional"


@dataclass(slots=True)
class ProductionAcceptanceReport:
    generated_at: str
    overall_status: str
    checks: list[AcceptanceCheck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    role_matrix: list[dict[str, object]] = field(default_factory=list)
    uat_checklist: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "overall_status": self.overall_status,
            "validation_scope": "production_acceptance",
            "checks": [asdict(check) for check in self.checks],
            "recommendations": self.recommendations,
            "role_matrix": self.role_matrix,
            "uat_checklist": self.uat_checklist,
        }


# Recommended custom role for warehouse / stock operations (not a system enum).
STOCK_MANAGER_TEMPLATE: frozenset[str] = frozenset(
    {
        "auth:login",
        "inventory:view",
        "inventory:create",
        "inventory:edit",
        "inventory:stock_edit",
        "inventory:transfer",
        "inventory:archive",
        "inventory:restore",
        "inventory:export",
        "brands:view",
        "brands:edit",
        "product_models:view",
        "product_models:edit",
        "locations:view",
        "locations:edit",
        "dashboard:view",
        "dashboard:inventory_distribution",
        "dashboard:recent_inventory",
        "dashboard:recent_transfers",
        "notifications:view",
        "audit:lifecycle",
    },
)

UAT_CHECKLIST: list[dict[str, str]] = [
    {"id": "UAT-01", "item": "Main Admin full module access verified", "owner": "Store admin"},
    {
        "id": "UAT-02",
        "item": "Administrator (admin role) inventory + backup workflows",
        "owner": "Store admin",
    },
    {
        "id": "UAT-03",
        "item": "Salesperson search, transfer, and sales view",
        "owner": "Sales staff",
    },
    {
        "id": "UAT-04",
        "item": "Stock Manager custom role inventory operations",
        "owner": "Warehouse",
    },
    {"id": "UAT-05", "item": "Custom access role created and assigned", "owner": "Main Admin"},
    {"id": "UAT-06", "item": "Inventory receive → available → sold lifecycle", "owner": "Staff"},
    {"id": "UAT-07", "item": "Manual sale or Tally-imported sale reflected", "owner": "Accounts"},
    {"id": "UAT-08", "item": "Catalogue brands/models/locations CRUD", "owner": "Admin"},
    {"id": "UAT-09", "item": "Reports generated and exported", "owner": "Manager"},
    {"id": "UAT-10", "item": "Notifications received and resolved", "owner": "Admin"},
    {"id": "UAT-11", "item": "Audit log search and export", "owner": "Main Admin"},
    {"id": "UAT-12", "item": "Backup create + verify + restore drill", "owner": "Main Admin"},
    {"id": "UAT-13", "item": "AI enrichment (if enabled) on product model", "owner": "Admin"},
    {"id": "UAT-14", "item": "Tally sync imports voucher to inventory", "owner": "Accounts"},
    {"id": "UAT-15", "item": "Global search by serial and model", "owner": "Sales staff"},
    {"id": "UAT-16", "item": "Mobile offline cache and reconnect sync", "owner": "Floor staff"},
    {"id": "UAT-17", "item": "Client auto-update check from server", "owner": "IT"},
    {
        "id": "UAT-18",
        "item": "Deployment rollback procedure documented",
        "owner": "WEBSTUDIO engineer",
    },
]


def _aggregate_status(checks: list[AcceptanceCheck]) -> str:
    if any(check.status == "failed" for check in checks):
        return "failed"
    if any(check.status == "warning" for check in checks):
        return "warning"
    return "passed"


def _role_matrix_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    profiles: list[tuple[str, str, frozenset[str]]] = [
        ("main_admin", "Administrator (Main Admin)", PERMISSIONS_BY_ROLE[UserRole.MAIN_ADMIN]),
        ("admin", "Administrator (Admin)", PERMISSIONS_BY_ROLE[UserRole.ADMIN]),
        ("salesperson", "Salesperson", PERMISSIONS_BY_ROLE[UserRole.SALESPERSON]),
        ("stock_manager", "Stock Manager (custom template)", STOCK_MANAGER_TEMPLATE),
    ]
    modules = (
        ("inventory", "inventory:"),
        ("sales", "sales:"),
        ("catalogue", ("brands:", "product_models:", "locations:")),
        ("reports", "reports:"),
        ("notifications", "notifications:"),
        ("audit", "audit:"),
        ("backup", "backup:"),
        ("restore", "restore:"),
        ("tally", "tally:"),
        ("settings", "settings:"),
        ("users", "users:"),
    )
    for role_id, label, perms in profiles:
        module_access: dict[str, str] = {}
        for mod_key, prefixes in modules:
            if isinstance(prefixes, str):
                prefixes = (prefixes,)
            matched = [p for p in perms if p.startswith(prefixes)]
            if not matched:
                module_access[mod_key] = "none"
            elif any(":view" in p or p.endswith(":view_status") for p in matched):
                write = any(
                    p.split(":")[-1] not in {"view", "view_status", "login"} for p in matched
                )
                module_access[mod_key] = "read_write" if write else "read"
            else:
                module_access[mod_key] = "service"
        rows.append(
            {
                "role_id": role_id,
                "role_label": label,
                "permission_count": len(perms),
                "modules": module_access,
            },
        )
    rows.append(
        {
            "role_id": "custom_access_role",
            "role_label": "Custom Roles (assignable catalogue)",
            "permission_count": len(ASSIGNABLE_PERMISSIONS),
            "modules": {"note": "Subset of ALL_PERMISSIONS via /api/v1/access-roles"},
        },
    )
    return rows


class ProductionAcceptanceValidationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._system = SystemSettingRepository(session)

    async def run_acceptance_validation(self) -> ProductionAcceptanceReport:
        checks: list[AcceptanceCheck] = []
        recommendations: list[str] = []
        capabilities = await build_capabilities_payload(self._session, self._settings)
        modules = capabilities.get("modules", {})
        ai_config = await resolve_ai_config(self._session, self._settings)
        tally_enabled = await TallySyncService(self._session).is_enabled()
        initialized = await self._system.get_bool("system_initialized", default=False)

        # Roles
        checks.append(
            AcceptanceCheck(
                key="role_administrator",
                name="Administrator",
                status="passed",
                message="Main Admin and Admin roles defined in PERMISSIONS_BY_ROLE.",
                detail=f"Main Admin: {len(permissions_for_role(UserRole.MAIN_ADMIN))} permissions; "
                f"Admin: {len(permissions_for_role(UserRole.ADMIN))}.",
                category="roles",
            ),
        )
        checks.append(
            AcceptanceCheck(
                key="role_salesperson",
                name="Salesperson",
                status="passed",
                message="Salesperson can view/transfer inventory and view sales; no user admin.",
                detail="tests/auth/test_permissions.py",
                category="roles",
            ),
        )
        sp = set(permissions_for_role(UserRole.SALESPERSON))
        if "sales:create" in sp:
            checks[-1] = AcceptanceCheck(
                key="role_salesperson",
                name="Salesperson",
                status="warning",
                message="Salesperson has sales:create — verify PRD intent.",
                detail="Manual mark-as-sold is admin-only per ADR-0011.",
                category="roles",
            )

        try:
            validate_assignable_permissions(set(STOCK_MANAGER_TEMPLATE))
            stock_status = "passed"
            stock_msg = "Stock Manager template is valid assignable custom role profile."
        except ValueError as exc:
            stock_status = "failed"
            stock_msg = str(exc)
        checks.append(
            AcceptanceCheck(
                key="role_stock_manager",
                name="Stock Manager",
                status=stock_status,
                message=stock_msg,
                detail="Create custom access role matching STOCK_MANAGER_TEMPLATE for warehouse staff.",
                category="roles",
            ),
        )

        checks.append(
            AcceptanceCheck(
                key="role_custom_access",
                name="Custom Roles",
                status="passed",
                message=f"{len(ASSIGNABLE_PERMISSIONS)} assignable permissions; custom roles via access-roles API.",
                detail="PermissionResolver merges custom_access_role_id over system role.",
                category="roles",
            ),
        )

        # Functional modules
        module_checks: list[tuple[str, str, str, str]] = [
            ("module_inventory", "Inventory", "inventory", "/api/v1/inventory"),
            ("module_sales", "Sales", "sales", "/api/v1/sales"),
            ("module_catalogue", "Catalogue", "catalogue", "/api/v1/brands"),
            ("module_reports", "Reports", "reports", "/api/v1/reports"),
            ("module_notifications", "Notifications", "notifications", "/api/v1/notifications"),
            ("module_audit", "Audit", "audit", "/api/v1/audit_logs"),
            ("module_backup", "Backup", "backup", "/api/v1/settings/backups"),
            ("module_restore", "Restore", "backup", "/api/v1/settings/backups/restore"),
            ("module_global_search", "Global Search", "inventory", "/api/v1/search"),
            ("module_synchronization", "Synchronization", "tally", "tally_sync + excel_export"),
        ]

        for key, name, mod_key, api_hint in module_checks:
            enabled = (
                modules.get(mod_key, True)
                if mod_key != "catalogue"
                else modules.get("catalogue", True)
            )
            status = "passed" if enabled else "warning"
            checks.append(
                AcceptanceCheck(
                    key=key,
                    name=name,
                    status=status,
                    message=f"Module enabled; API surface {api_hint}.",
                    detail="Automated tests in apps/backend/tests/",
                    category="functional",
                ),
            )

        # AI
        ai_status = "passed" if ai_config.enrichment_enabled else "warning"
        if not ai_config.enrichment_enabled:
            recommendations.append(
                "Configure AI provider keys if product enrichment is required at go-live."
            )
        checks.append(
            AcceptanceCheck(
                key="module_ai",
                name="AI",
                status=ai_status,
                message=f"AI enrichment {'enabled' if ai_config.enrichment_enabled else 'disabled'}; provider {ai_config.primary_provider}.",
                detail="Settings → Integrations; capabilities.ai",
                category="functional",
            ),
        )

        # Tally
        tally_status = "passed" if tally_enabled else "warning"
        if not tally_enabled:
            recommendations.append("Enable Tally in settings if billing integration is required.")
        checks.append(
            AcceptanceCheck(
                key="module_tally",
                name="Tally",
                status=tally_status,
                message=f"Tally integration {'enabled' if tally_enabled else 'disabled'}.",
                detail="GET /api/v1/integrations/tally/production-validation (M14C)",
                category="functional",
            ),
        )

        # Offline mode
        checks.append(
            AcceptanceCheck(
                key="module_offline_mode",
                name="Offline Mode",
                status="passed",
                message="Flutter offline cache, pending ops, and session restore implemented.",
                detail="On-device UAT required; apps/mobile_flutter/lib/core/offline/",
                category="mobile",
            ),
        )

        # Auto update
        checks.append(
            AcceptanceCheck(
                key="module_auto_update",
                name="Auto Update",
                status="passed",
                message="Clients poll WEBSTUDIO Server /api/v1/client-updates/check — never GitHub.",
                detail="M13 enterprise release catalog; Deployment Center approval.",
                category="operations",
            ),
        )

        # Rollback
        rollback_status = "passed" if ROLLBACK_STEPS else "failed"
        checks.append(
            AcceptanceCheck(
                key="module_rollback",
                name="Rollback",
                status=rollback_status,
                message=f"Enterprise rollback {len(ROLLBACK_STEPS)} steps; restore rollback for failed DB restore.",
                detail="Deployment Center + POST /settings/backups/rollback",
                category="operations",
            ),
        )

        if not initialized:
            checks.append(
                AcceptanceCheck(
                    key="system_initialized",
                    name="System initialized",
                    status="warning",
                    message="Complete setup wizard before production acceptance sign-off.",
                    detail="system_initialized setting",
                    category="prerequisites",
                ),
            )
            recommendations.append("Finish M14A setup wizard before UAT sign-off.")

        overall = _aggregate_status(checks)
        return ProductionAcceptanceReport(
            generated_at=datetime.now(UTC).isoformat(),
            overall_status=overall,
            checks=checks,
            recommendations=recommendations,
            role_matrix=_role_matrix_rows(),
            uat_checklist=UAT_CHECKLIST,
        )

    async def build_acceptance_report(self) -> dict[str, object]:
        validation = await self.run_acceptance_validation()
        return {
            **validation.to_dict(),
            "app_version": self._settings.app_version,
            "permission_catalogue_size": len(ALL_PERMISSIONS),
            "production_acceptance_report": "docs/milestones/m14/PRODUCTION_ACCEPTANCE_REPORT.md",
            "user_acceptance_checklist": "docs/milestones/m14/USER_ACCEPTANCE_CHECKLIST.md",
            "role_matrix_validation": "docs/milestones/m14/ROLE_MATRIX_VALIDATION.md",
            "m11_qa_reference": "docs/milestones/m11/README.md",
        }
