"""Tally dashboard aggregation service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import NotificationCategory, NotificationStatus
from webstudio_backend.infrastructure.database.models.notification import Notification
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import TallyCompanySyncRepository
from webstudio_backend.infrastructure.repositories.tally_sync_log_repository import TallySyncLogRepository
from webstudio_backend.integrations.tally.constants import MONITORED_VOUCHER_TYPES
from webstudio_backend.services.tally_sync_service import TallySyncService


class TallyDashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = SystemSettingRepository(session)
        self._company_sync = TallyCompanySyncRepository(session)
        self._sync_logs = TallySyncLogRepository(session)
        self._sync = TallySyncService(session)

    async def build_dashboard(self) -> dict:
        enabled = await self._sync.is_enabled()
        host, port, company_name, interval = await self._sync.get_connection_config()
        companies = await self._company_sync.list_active()
        if not companies and company_name:
            companies = [await self._company_sync.get_or_create(company_name)]

        connection_status = "disconnected"
        last_error: str | None = None
        if companies:
            connection_status = companies[0].connection_status
            last_error = companies[0].last_error

        last_sync = max(
            (company.last_successful_sync_at for company in companies if company.last_successful_sync_at),
            default=None,
        )
        next_sync = (last_sync + timedelta(seconds=interval)) if last_sync else datetime.now(UTC) + timedelta(seconds=interval)

        pending_notifications = await self._pending_notification_count()
        recent_logs = await self._sync_logs.recent_runs(limit=10)

        stats = {"invoices_processed": 0, "inventory_entries": 0, "duplicates": 0, "missing_serials": 0, "model_mismatches": 0, "failures": 0}
        if companies:
            aggregated = await self._sync_logs.aggregate_stats(companies[0].id)
            stats = {
                "invoices_processed": aggregated["invoices_processed"],
                "inventory_entries": aggregated["successfully_updated"] + aggregated["missing_serial"] + aggregated["missing_model"],
                "duplicates": aggregated["already_sold"],
                "missing_serials": aggregated["missing_serial"],
                "model_mismatches": aggregated["model_mismatches"],
                "failures": aggregated["missing_model"],
            }

        return {
            "connection_status": connection_status if enabled else "disconnected",
            "enabled": enabled,
            "tally_host": host,
            "tally_port": port,
            "sync_interval_seconds": interval,
            "next_scheduled_sync_at": next_sync.isoformat() if next_sync else None,
            "last_successful_sync_at": last_sync.isoformat() if last_sync else None,
            "voucher_types": list(MONITORED_VOUCHER_TYPES),
            "companies": [
                {
                    "company_name": company.company_name,
                    "last_successful_sync_time": company.last_successful_sync_at.isoformat()
                    if company.last_successful_sync_at
                    else None,
                    "last_processed_voucher_identifier": company.last_processed_guid,
                    "last_processed_guid": company.last_processed_guid,
                    "last_error": company.last_error,
                    "connection_status": company.connection_status,
                }
                for company in companies
            ],
            "pending_notifications_count": pending_notifications,
            "last_error": last_error,
            "stats": stats,
            "recent_synchronizations": [
                {
                    "sync_run_id": str(log.sync_run_id),
                    "voucher_type": log.voucher_type,
                    "printed_invoice_number": log.printed_invoice_number,
                    "voucher_number": log.tally_voucher_number,
                    "status": log.processing_status.value,
                    "started_at": log.sync_started_at.isoformat(),
                    "completed_at": log.sync_completed_at.isoformat() if log.sync_completed_at else None,
                    "successfully_updated": log.successfully_updated,
                    "already_sold": log.already_sold,
                    "missing_serial": log.missing_serial,
                    "model_mismatches": log.model_mismatches,
                }
                for log in recent_logs
            ],
        }

    async def build_status_summary(self) -> dict:
        dashboard = await self.build_dashboard()
        stats = dashboard["stats"]
        return {
            "is_healthy": dashboard["connection_status"] == "connected" and dashboard["enabled"],
            "last_sync": dashboard["last_successful_sync_at"] or "",
            "next_scheduled_sync": dashboard["next_scheduled_sync_at"],
            "connection_status": dashboard["connection_status"],
            "connection_health": (
                "healthy"
                if dashboard["connection_status"] == "connected" and not dashboard["last_error"]
                else "offline"
                if dashboard["connection_status"] == "error"
                else "degraded"
            ),
            "connected_companies": len(dashboard["companies"]),
            "invoices_processed": stats["invoices_processed"],
            "inventory_entries_processed": stats["inventory_entries"],
            "skipped_invoices": 0,
            "duplicate_invoices": stats["duplicates"],
            "model_mismatches": stats["model_mismatches"],
            "missing_serials": stats["missing_serials"],
            "sync_failures": stats["failures"],
            "pending_issues": dashboard["pending_notifications_count"],
            "last_error": dashboard["last_error"],
            "voucher_types": dashboard["voucher_types"],
        }

    async def _pending_notification_count(self) -> int:
        statement = select(func.count()).select_from(Notification).where(
            Notification.category == NotificationCategory.TALLY_SYNC,
            Notification.is_resolved.is_(False),
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())
