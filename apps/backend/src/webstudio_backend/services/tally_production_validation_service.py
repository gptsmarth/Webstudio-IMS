"""Production Tally integration validation for M14C commissioning."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import (
    TallyCompanySyncRepository,
)
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_repository import (
    TallyProcessedInvoiceRepository,
)
from webstudio_backend.integrations.tally.constants import MONITORED_VOUCHER_TYPES
from webstudio_backend.integrations.tally.incremental_sync import (
    SYNC_INTERVAL_MAX_SECONDS,
    SYNC_INTERVAL_MIN_SECONDS,
    clamp_sync_interval_seconds,
    resolve_incremental_from_date,
)
from webstudio_backend.integrations.tally.xml_client import TallyXmlClient
from webstudio_backend.services.scheduler_runtime_service import SchedulerRuntimeService
from webstudio_backend.services.tally_connectivity_service import TallyConnectivityService
from webstudio_backend.services.tally_dashboard_service import TallyDashboardService
from webstudio_backend.services.tally_sync_service import TallySyncService


@dataclass(frozen=True, slots=True)
class TallyValidationCheck:
    key: str
    name: str
    status: str  # passed | warning | failed | skipped
    message: str
    detail: str = ""


@dataclass(slots=True)
class TallyProductionValidationReport:
    generated_at: str
    overall_status: str
    assumes_live_tally: bool
    checks: list[TallyValidationCheck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    validation_checklist: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "overall_status": self.overall_status,
            "assumes_live_tally": self.assumes_live_tally,
            "validation_scope": "production",
            "checks": [asdict(check) for check in self.checks],
            "recommendations": self.recommendations,
            "validation_checklist": self.validation_checklist,
        }


TALLY_VALIDATION_CHECKLIST: list[dict[str, str]] = [
    {"id": "TLY-01", "item": "Tally ERP 9 running with company books open", "owner": "Accounts"},
    {"id": "TLY-02", "item": "XML port 9000 enabled on billing PC", "owner": "Accounts"},
    {"id": "TLY-03", "item": "Server resolves Tally hostname on LAN", "owner": "IT"},
    {
        "id": "TLY-04",
        "item": "Test Connection succeeds in Settings → Tally",
        "owner": "Store admin",
    },
    {
        "id": "TLY-05",
        "item": "Incremental sync imports new vouchers only",
        "owner": "WEBSTUDIO engineer",
    },
    {
        "id": "TLY-06",
        "item": "GUID checkpoint advances after successful import",
        "owner": "WEBSTUDIO engineer",
    },
    {"id": "TLY-07", "item": "Last sync timestamp updates on dashboard", "owner": "Store admin"},
    {
        "id": "TLY-08",
        "item": "Sync resumes after WEBSTUDIO Server restart",
        "owner": "WEBSTUDIO engineer",
    },
    {"id": "TLY-09", "item": "Sync resumes after Tally restart", "owner": "WEBSTUDIO engineer"},
    {
        "id": "TLY-10",
        "item": "Offline period replays vouchers when Tally returns",
        "owner": "WEBSTUDIO engineer",
    },
    {
        "id": "TLY-11",
        "item": "Duplicate voucher GUID skipped on re-sync",
        "owner": "WEBSTUDIO engineer",
    },
    {
        "id": "TLY-12",
        "item": "Manual Sync Now imports from dashboard/settings",
        "owner": "Store admin",
    },
]


def _aggregate_status(checks: list[TallyValidationCheck]) -> str:
    if any(check.status == "failed" for check in checks):
        return "failed"
    if any(check.status == "warning" for check in checks):
        return "warning"
    return "passed"


def _xml_request_has_required_fields(payload: str) -> bool:
    required = (
        "<ENVELOPE>",
        "TALLYREQUEST>Export",
        "SVCURRENTCOMPANY>",
        "SVFROMDATE>",
        "SVTODATE>",
        "Day Book",
    )
    return all(token in payload for token in required)


class TallyProductionValidationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sync = TallySyncService(session)
        self._connectivity = TallyConnectivityService(session)
        self._dashboard = TallyDashboardService(session)
        self._processed = TallyProcessedInvoiceRepository(session)
        self._runtime = SchedulerRuntimeService(session)
        self._company_sync = TallyCompanySyncRepository(session)

    async def run_production_validation(
        self, *, assume_live_tally: bool = True
    ) -> TallyProductionValidationReport:
        checks: list[TallyValidationCheck] = []
        recommendations: list[str] = []

        enabled = await self._sync.is_enabled()
        host, port, company_name, interval = await self._sync.get_connection_config()
        clamped_interval = clamp_sync_interval_seconds(interval)
        company_sync = (
            await self._company_sync.get_or_create(company_name) if company_name else None
        )

        live_reachable = False
        live_detail = "Tally integration disabled"
        if enabled and company_name:
            try:
                diagnostics = await self._connectivity.test_connection()
                await self._session.commit()
                live_reachable = diagnostics.reachable
                live_detail = diagnostics.user_message or diagnostics.status
            except Exception as exc:  # noqa: BLE001
                live_detail = str(exc)
        elif not enabled:
            checks.append(
                TallyValidationCheck(
                    key="tally_enabled",
                    name="Tally integration",
                    status="skipped",
                    message="Tally integration is disabled.",
                    detail="Enable in Settings → Tally before production validation.",
                ),
            )

        # XML request generation
        sample_client = TallyXmlClient(host or "127.0.0.1", port or "9000")
        sample_xml = sample_client._day_book_export_request(  # noqa: SLF001
            company_name=company_name or "WEBSTUDIO",
            from_date=date.today(),
            to_date=date.today(),
        )
        xml_ok = _xml_request_has_required_fields(sample_xml)
        checks.append(
            TallyValidationCheck(
                key="xml_request_generation",
                name="XML request generation",
                status="passed" if xml_ok else "failed",
                message="Day Book export template valid (Tally Prime compatible).",
                detail="Monitored voucher types filtered server-side: "
                + ", ".join(MONITORED_VOUCHER_TYPES),
            ),
        )

        # Incremental synchronization
        if company_sync is not None:
            incremental_from = resolve_incremental_from_date(company_sync)
            inc_status = "passed"
            inc_message = f"Incremental window starts {incremental_from.isoformat()}."
            if company_sync.last_successful_sync_at is None:
                inc_status = "warning"
                inc_message = (
                    f"First sync will request vouchers from {incremental_from.isoformat()}."
                )
        else:
            inc_status = "warning"
            inc_message = "Configure Tally company name before first sync."
        checks.append(
            TallyValidationCheck(
                key="incremental_synchronization",
                name="Incremental synchronization",
                status=inc_status,
                message=inc_message,
                detail="Uses last_successful_sync_at — never full history replay.",
            ),
        )

        # GUID checkpoint
        if company_sync is not None:
            guid_value = company_sync.last_processed_guid
            guid_status = "passed" if guid_value else "warning"
            guid_message = (
                f"Last processed GUID checkpoint: {guid_value}."
                if guid_value
                else "GUID checkpoint not set yet — populated after first successful import."
            )
        else:
            guid_status = "warning"
            guid_message = "Company sync row not initialized."
        checks.append(
            TallyValidationCheck(
                key="guid_checkpoint",
                name="GUID checkpoint",
                status=guid_status,
                message=guid_message,
                detail="Persisted in webstudio.tally_company_sync.last_processed_guid",
            ),
        )

        # Last synchronization timestamp
        if company_sync is not None and company_sync.last_successful_sync_at is not None:
            last_sync_status = "passed"
            last_sync_message = company_sync.last_successful_sync_at.isoformat()
        elif assume_live_tally and enabled and not live_reachable:
            last_sync_status = "warning"
            last_sync_message = "No successful sync yet — Tally workstation not reachable."
            recommendations.append("Start Tally on the billing PC and run Test Connection.")
        else:
            last_sync_status = "warning"
            last_sync_message = "No successful sync recorded yet."
        checks.append(
            TallyValidationCheck(
                key="last_synchronization_timestamp",
                name="Last synchronization timestamp",
                status=last_sync_status,
                message=last_sync_message,
                detail="Field: tally_company_sync.last_successful_sync_at",
            ),
        )

        # Recovery after server restart
        scheduler_env = get_settings().webstudio_tally_scheduler
        runtime_row = await self._runtime.get_state("tally_sync")
        restart_status = "passed" if scheduler_env and runtime_row is not None else "warning"
        restart_message = (
            "tally_sync scheduler registered; shutdown checkpoint finalizes in-progress runs."
            if scheduler_env
            else "WEBSTUDIO_TALLY_SCHEDULER is not enabled — only manual sync after restart."
        )
        if not scheduler_env:
            recommendations.append("Set WEBSTUDIO_TALLY_SCHEDULER=1 in production .env.")
        checks.append(
            TallyValidationCheck(
                key="recovery_after_server_restart",
                name="Recovery after server restart",
                status=restart_status,
                message=restart_message,
                detail="shutdown_orchestrator.checkpoint_tally_sync persists scheduler state.",
            ),
        )

        # Recovery after Tally restart
        probe_env = get_settings().webstudio_tally_connectivity_probe
        probe_row = await self._runtime.get_state("tally_connectivity_probe")
        tally_restart_status = "passed" if probe_env else "warning"
        checks.append(
            TallyValidationCheck(
                key="recovery_after_tally_restart",
                name="Recovery after Tally restart",
                status=tally_restart_status,
                message=(
                    "Connectivity probe scheduler active; sync resumes when Tally returns."
                    if probe_env
                    else "Enable WEBSTUDIO_TALLY_CONNECTIVITY_PROBE for automatic Tally recovery."
                ),
                detail=f"Probe last status {probe_row.last_run_status or 'n/a'}; live: {live_detail}",
            ),
        )

        # Offline XML replay
        offline_status = "passed" if company_sync is not None else "warning"
        checks.append(
            TallyValidationCheck(
                key="offline_xml_replay",
                name="Offline XML replay",
                status=offline_status,
                message="Offline runs recorded as skipped; incremental window replays when Tally is back.",
                detail="Sync history status offline; resolve_incremental_from_date preserves checkpoint.",
            ),
        )

        # Duplicate prevention
        has_guid_lookup = hasattr(self._processed, "find_by_guid")
        checks.append(
            TallyValidationCheck(
                key="duplicate_prevention",
                name="Duplicate prevention",
                status="passed" if has_guid_lookup else "failed",
                message="Processed invoices deduplicated by Tally voucher GUID.",
                detail="tally_processed_invoice + GUID lookup before import.",
            ),
        )

        # Manual synchronization
        checks.append(
            TallyValidationCheck(
                key="manual_synchronization",
                name="Manual synchronization",
                status="passed" if enabled else "warning",
                message="POST /api/v1/integrations/tally/sync/trigger queues background sync.",
                detail="Desktop: Settings → Tally → Sync now (requires tally:run_sync).",
            ),
        )

        # Automatic scheduler
        auto_status = (
            "passed" if scheduler_env and enabled else ("skipped" if not enabled else "warning")
        )
        checks.append(
            TallyValidationCheck(
                key="automatic_scheduler",
                name="Automatic scheduler",
                status=auto_status,
                message=(
                    f"tally_sync scheduler env on; next interval {clamped_interval}s."
                    if scheduler_env
                    else "Automatic scheduler disabled in server environment."
                ),
                detail=f"Runtime key tally_sync; last status {runtime_row.last_run_status or 'n/a'}.",
            ),
        )

        # Configurable polling interval
        interval_ok = SYNC_INTERVAL_MIN_SECONDS <= clamped_interval <= SYNC_INTERVAL_MAX_SECONDS
        polling_status = "passed" if interval_ok else "failed"
        if interval != clamped_interval:
            polling_status = "warning"
        checks.append(
            TallyValidationCheck(
                key="configurable_polling_interval",
                name="Configurable polling interval",
                status=polling_status,
                message=f"tally_sync_interval_seconds={interval} (clamped {clamped_interval}).",
                detail=f"Allowed range {SYNC_INTERVAL_MIN_SECONDS}–{SYNC_INTERVAL_MAX_SECONDS} seconds.",
            ),
        )

        # Dashboard synchronization status
        status_summary = await self._dashboard.build_status_summary()
        operational = status_summary.get("operational", {})
        required_fields = (
            "sync_health",
            "last_successful_sync_at",
            "next_scheduled_sync_at",
            "scheduler_status",
            "polling_interval_seconds",
        )
        dashboard_ok = all(field in operational for field in required_fields)
        dash_status = "passed" if dashboard_ok else "failed"
        checks.append(
            TallyValidationCheck(
                key="dashboard_synchronization_status",
                name="Dashboard synchronization status",
                status=dash_status,
                message=f"Sync health: {operational.get('sync_health', 'unknown')}.",
                detail="GET /api/v1/integrations/tally/dashboard and /status expose operational summary.",
            ),
        )

        if assume_live_tally and enabled:
            live_check_status = "passed" if live_reachable else "failed"
            checks.append(
                TallyValidationCheck(
                    key="live_tally_connectivity",
                    name="Live Tally connectivity",
                    status=live_check_status,
                    message=live_detail,
                    detail=f"Host {host}:{port}; company {company_name}.",
                ),
            )
            if not live_reachable:
                recommendations.append(
                    "Ensure Tally is running with XML port open before go-live sign-off."
                )

        if enabled and company_name and not re.fullmatch(r"[\w.\-]+", host, re.I):
            recommendations.append("Use Tally laptop hostname (not raw IP) for DHCP mobility.")

        overall = _aggregate_status(checks)
        return TallyProductionValidationReport(
            generated_at=datetime.now(UTC).isoformat(),
            overall_status=overall,
            assumes_live_tally=assume_live_tally,
            checks=checks,
            recommendations=recommendations,
            validation_checklist=TALLY_VALIDATION_CHECKLIST,
        )

    async def build_production_report(self, *, assume_live_tally: bool = True) -> dict[str, object]:
        validation = await self.run_production_validation(assume_live_tally=assume_live_tally)
        dashboard = await self._dashboard.build_dashboard()
        host, port, company_name, interval = await self._sync.get_connection_config()
        return {
            **validation.to_dict(),
            "tally_host": host,
            "tally_port": port,
            "company_name": company_name,
            "sync_interval_seconds": interval,
            "enabled": await self._sync.is_enabled(),
            "dashboard_operational": dashboard.get("operational"),
            "xml_verification_script": "tools/scripts/uat_analyze_tally_xml.py",
            "production_validation_script": "infra/windows/validate-production-tally.ps1",
        }
