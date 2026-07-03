"""Tally dashboard aggregation service."""

from __future__ import annotations

import csv
import io
import os
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import NotificationCategory
from webstudio_backend.infrastructure.database.models.notification import Notification
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import TallyCompanySyncRepository
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_repository import TallyProcessedInvoiceRepository
from webstudio_backend.infrastructure.repositories.tally_sync_history_repository import TallySyncHistoryRepository
from webstudio_backend.infrastructure.repositories.tally_sync_log_repository import TallySyncLogRepository
from webstudio_backend.integrations.tally.constants import MONITORED_VOUCHER_TYPES
from webstudio_backend.services.scheduler_runtime_service import SchedulerRuntimeService
from webstudio_backend.services.tally_sync_service import TallySyncService


class TallyDashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = SystemSettingRepository(session)
        self._company_sync = TallyCompanySyncRepository(session)
        self._processed_invoices = TallyProcessedInvoiceRepository(session)
        self._sync_logs = TallySyncLogRepository(session)
        self._sync_history = TallySyncHistoryRepository(session)
        self._sync = TallySyncService(session)

    async def build_dashboard(self) -> dict:
        enabled = await self._sync.is_enabled()
        host, port, company_name, interval = await self._sync.get_connection_config()
        companies = await self._company_sync.list_active()
        if not companies and company_name:
            companies = [await self._company_sync.get_or_create(company_name)]

        company = companies[0] if companies else None
        company_id = company.id if company else None

        connection_status = "disconnected"
        connectivity_status = "offline"
        last_error: str | None = None
        last_resolved_ip: str | None = None
        last_successful_connection_at = None
        last_failed_connection_at = None
        if company:
            connection_status = company.connection_status
            connectivity_status = company.connectivity_status or "offline"
            last_error = company.last_error
            last_resolved_ip = company.last_resolved_ip
            last_successful_connection_at = company.last_successful_connection_at
            last_failed_connection_at = company.last_failed_connection_at

        last_sync = company.last_successful_sync_at if company and company.last_successful_sync_at else None
        next_sync = await self._resolve_next_scheduled_sync(last_sync=last_sync, interval=interval)

        pending_notifications = await self._pending_notification_count()
        recent_history = (
            await self._sync_history.recent_runs(company_sync_id=company_id, limit=10)
            if company_id is not None
            else []
        )

        stats = {"invoices_processed": 0, "inventory_entries": 0, "duplicates": 0, "missing_serials": 0, "model_mismatches": 0, "failures": 0}
        if company_id is not None:
            aggregated = await self._sync_logs.aggregate_stats(company_id)
            stats = {
                "invoices_processed": aggregated["invoices_processed"],
                "inventory_entries": aggregated["successfully_updated"] + aggregated["missing_serial"] + aggregated["missing_model"],
                "duplicates": aggregated["already_sold"],
                "missing_serials": aggregated["missing_serial"],
                "model_mismatches": aggregated["model_mismatches"],
                "failures": aggregated["missing_model"],
            }

        operational = await self._build_operational_summary(
            enabled=enabled,
            interval=interval,
            company=company,
            connection_status=connection_status if enabled else "disconnected",
            connectivity_status=connectivity_status if enabled else "offline",
            last_sync=last_sync,
            next_sync=next_sync,
            last_error=last_error,
            company_id=company_id,
        )

        return {
            "connection_status": connection_status if enabled else "disconnected",
            "connectivity_status": connectivity_status if enabled else "offline",
            "enabled": enabled,
            "tally_host": host,
            "tally_port": port,
            "resolved_ip": last_resolved_ip,
            "sync_interval_seconds": interval,
            "next_scheduled_sync_at": next_sync.isoformat() if next_sync else None,
            "last_successful_sync_at": last_sync.isoformat() if last_sync else None,
            "last_successful_connection_at": (
                last_successful_connection_at.isoformat() if last_successful_connection_at else None
            ),
            "last_failed_connection_at": (
                last_failed_connection_at.isoformat() if last_failed_connection_at else None
            ),
            "voucher_types": list(MONITORED_VOUCHER_TYPES),
            "companies": [
                {
                    "company_name": item.company_name,
                    "last_successful_sync_time": item.last_successful_sync_at.isoformat()
                    if item.last_successful_sync_at
                    else None,
                    "last_error": item.last_error,
                    "connection_status": item.connection_status,
                    "connectivity_status": item.connectivity_status,
                    "sync_in_progress": item.sync_in_progress,
                }
                for item in companies
            ],
            "pending_notifications_count": pending_notifications,
            "last_error": last_error,
            "stats": stats,
            "operational": operational,
            "recent_synchronizations": [self._history_entry(entry) for entry in recent_history],
        }

    async def _resolve_next_scheduled_sync(
        self,
        *,
        last_sync: datetime | None,
        interval: int,
    ) -> datetime:
        runtime = SchedulerRuntimeService(self._session)
        persisted = await runtime.get_next_run_at("tally_sync")
        if persisted is not None and persisted > datetime.now(UTC):
            return persisted
        if last_sync is not None:
            return last_sync + timedelta(seconds=interval)
        return datetime.now(UTC) + timedelta(seconds=interval)

    async def _build_operational_summary(
        self,
        *,
        enabled: bool,
        interval: int,
        company,
        connection_status: str,
        connectivity_status: str,
        last_sync: datetime | None,
        next_sync: datetime,
        last_error: str | None,
        company_id: int | None,
    ) -> dict:
        now = datetime.now(UTC)
        today_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=UTC)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)

        imported_today = 0
        imported_week = 0
        imported_month = 0
        total_imported = 0
        last_invoice_imported: str | None = None
        last_invoice_date: str | None = None
        last_sync_duration_ms = company.last_sync_duration_ms if company else None

        if company_id is not None:
            imported_today = await self._sync_history.sum_imported_since(company_id, today_start)
            imported_week = await self._sync_history.sum_imported_since(company_id, week_start)
            imported_month = await self._sync_history.sum_imported_since(company_id, month_start)
            total_imported = await self._sync_history.sum_total_imported(company_id)
            last_invoice = await self._processed_invoices.get_last_successful_import(company_id)
            if last_invoice:
                last_invoice_imported = last_invoice.printed_invoice_number or last_invoice.tally_voucher_number
                if last_invoice.voucher_date:
                    last_invoice_date = last_invoice.voucher_date.isoformat()

        is_connected = enabled and connection_status == "connected" and connectivity_status not in {"offline", "xml_error"}
        scheduler_env = os.getenv("WEBSTUDIO_TALLY_SCHEDULER", "0") == "1"
        sync_in_progress = bool(company and company.sync_in_progress)

        if not enabled:
            scheduler_status = "disabled"
            scheduler_label = "Auto sync disabled"
        elif sync_in_progress:
            scheduler_status = "syncing"
            scheduler_label = "Synchronization in progress"
        elif not scheduler_env:
            scheduler_status = "manual"
            scheduler_label = "Manual sync only (scheduler not active on server)"
        elif connectivity_status in {"offline", "xml_error"} or connection_status in {"disconnected", "error"}:
            scheduler_status = "waiting"
            scheduler_label = "Waiting for Tally workstation"
        else:
            scheduler_status = "idle"
            scheduler_label = "Scheduler idle — next sync scheduled"

        retry_countdown_seconds: int | None = None
        pending_retry = not is_connected and enabled
        if enabled and next_sync:
            retry_countdown_seconds = max(0, int((next_sync - now).total_seconds()))

        if pending_retry and retry_countdown_seconds is not None:
            scheduler_label = f"Retry in {_format_countdown(retry_countdown_seconds)}"

        sync_health = "healthy"
        if not enabled:
            sync_health = "offline"
        elif pending_retry or connection_status == "error":
            sync_health = "offline"
        elif last_error or connectivity_status == "degraded":
            sync_health = "degraded"

        return {
            "connection_label": "Connected" if is_connected else "Disconnected",
            "is_connected": is_connected,
            "auto_sync_enabled": enabled,
            "polling_interval_seconds": interval,
            "polling_interval_label": _format_interval(interval),
            "last_successful_sync_at": last_sync.isoformat() if last_sync else None,
            "last_invoice_imported": last_invoice_imported,
            "last_invoice_date": last_invoice_date,
            "next_scheduled_sync_at": next_sync.isoformat() if next_sync else None,
            "last_sync_duration_ms": last_sync_duration_ms,
            "last_sync_duration_label": _format_duration_ms(last_sync_duration_ms),
            "imported_today": imported_today,
            "imported_this_week": imported_week,
            "imported_this_month": imported_month,
            "total_imported": total_imported,
            "scheduler_status": scheduler_status,
            "scheduler_status_label": scheduler_label,
            "retry_countdown_seconds": retry_countdown_seconds if pending_retry else None,
            "retry_countdown_label": _format_countdown(retry_countdown_seconds) if pending_retry and retry_countdown_seconds is not None else None,
            "sync_health": sync_health,
            "pending_retry": pending_retry,
            "todays_imports": imported_today,
        }

    @staticmethod
    def _history_entry(entry) -> dict:
        started = entry.started_at
        completed = entry.completed_at
        return {
            "sync_date": started.date().isoformat(),
            "start_time": started.strftime("%H:%M:%S"),
            "end_time": completed.strftime("%H:%M:%S") if completed else None,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat() if completed else None,
            "duration_ms": entry.duration_ms,
            "duration_label": _format_duration_ms(entry.duration_ms),
            "invoices_checked": entry.invoices_checked,
            "invoices_imported": entry.invoices_imported,
            "invoices_skipped": entry.invoices_skipped,
            "errors_count": entry.errors_count,
            "error_summary": entry.error_summary,
            "status": entry.status,
            "status_label": _format_status_label(entry.status),
        }

    async def build_sync_history(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
    ) -> list[dict]:
        company_id = await self._primary_company_id()
        if company_id is None:
            return []
        runs = await self._sync_history.list_runs(
            company_sync_id=company_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            search=search,
            limit=limit,
            offset=offset,
        )
        return [self._history_entry(entry) for entry in runs]

    async def export_sync_history_csv(
        self,
        *,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
    ) -> str:
        rows = await self.build_sync_history(
            limit=5000,
            offset=0,
            status=status,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "Date",
            "Start Time",
            "End Time",
            "Duration",
            "Invoices Checked",
            "Imported",
            "Skipped",
            "Errors",
            "Status",
            "Error Summary",
        ])
        for row in rows:
            writer.writerow([
                row["sync_date"],
                row["start_time"],
                row["end_time"] or "",
                row["duration_label"],
                row["invoices_checked"],
                row["invoices_imported"],
                row["invoices_skipped"],
                row["errors_count"],
                row["status_label"],
                row["error_summary"] or "",
            ])
        return buffer.getvalue()

    async def build_status_summary(self) -> dict:
        dashboard = await self.build_dashboard()
        operational = dashboard["operational"]
        stats = dashboard["stats"]
        return {
            "is_healthy": operational["sync_health"] == "healthy" and dashboard["enabled"],
            "available": dashboard["enabled"],
            "last_sync": dashboard["last_successful_sync_at"] or "",
            "next_scheduled_sync": dashboard["next_scheduled_sync_at"],
            "connection_status": dashboard["connection_status"],
            "connectivity_status": dashboard.get("connectivity_status", "offline"),
            "resolved_ip": dashboard.get("resolved_ip"),
            "last_successful_connection_at": dashboard.get("last_successful_connection_at"),
            "last_failed_connection_at": dashboard.get("last_failed_connection_at"),
            "connection_health": operational["sync_health"],
            "connected_companies": len(dashboard["companies"]),
            "invoices_processed": stats["invoices_processed"],
            "inventory_entries_processed": stats["inventory_entries"],
            "skipped_invoices": sum(
                entry.get("invoices_skipped", 0)
                for entry in dashboard["recent_synchronizations"]
                if isinstance(entry, dict)
            ),
            "duplicate_invoices": stats["duplicates"],
            "model_mismatches": stats["model_mismatches"],
            "missing_serials": stats["missing_serials"],
            "sync_failures": stats["failures"],
            "pending_issues": dashboard["pending_notifications_count"],
            "last_error": dashboard["last_error"],
            "voucher_types": dashboard["voucher_types"],
            "operational": operational,
            "pending_retry": operational["pending_retry"],
            "todays_imports": operational["todays_imports"],
            "connection_label": operational["connection_label"],
            "is_connected": operational["is_connected"],
        }

    async def _primary_company_id(self) -> int | None:
        companies = await self._company_sync.list_active()
        if companies:
            return companies[0].id
        _, _, company_name, _ = await self._sync.get_connection_config()
        if company_name:
            return (await self._company_sync.get_or_create(company_name)).id
        return None

    async def _pending_notification_count(self) -> int:
        statement = select(func.count()).select_from(Notification).where(
            Notification.category == NotificationCategory.TALLY_SYNC,
            Notification.is_resolved.is_(False),
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())


def _format_duration_ms(duration_ms: int | None) -> str:
    if duration_ms is None:
        return "—"
    total_seconds = max(0, duration_ms // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _format_interval(seconds: int) -> str:
    if seconds % 3600 == 0:
        return f"{seconds // 3600} hour{'s' if seconds // 3600 != 1 else ''}"
    if seconds % 60 == 0:
        return f"{seconds // 60} minute{'s' if seconds // 60 != 1 else ''}"
    return f"{seconds} seconds"


def _format_countdown(total_seconds: int) -> str:
    minutes, seconds = divmod(max(0, total_seconds), 60)
    return f"{minutes}:{seconds:02d}"


def _format_status_label(status: str) -> str:
    labels = {
        "success": "Success",
        "partial": "Partial",
        "failed": "Failed",
        "offline": "Skipped (offline)",
        "running": "Running",
    }
    return labels.get(status, status.replace("_", " ").title())
