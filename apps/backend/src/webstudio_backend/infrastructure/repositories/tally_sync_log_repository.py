"""Tally sync log repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import TallySyncRunStatus
from webstudio_backend.infrastructure.database.models.tally_sync_log import TallySyncLog
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


class TallySyncLogRepository(SqlAlchemyRepository[TallySyncLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TallySyncLog)

    async def create_run_log(
        self,
        *,
        sync_run_id: uuid.UUID,
        company_sync_id: int,
        correlation_id: str,
        voucher_guid: str | None = None,
        voucher_number: str | None = None,
        printed_invoice_number: str | None = None,
        voucher_type: str | None = None,
        customer_name: str | None = None,
        processed_invoice_id: int | None = None,
        status: TallySyncRunStatus = TallySyncRunStatus.SUCCESS,
    ) -> TallySyncLog:
        return await self.add(
            TallySyncLog(
                sync_run_id=sync_run_id,
                tally_company_sync_id=company_sync_id,
                tally_processed_invoice_id=processed_invoice_id,
                tally_voucher_guid=voucher_guid,
                tally_voucher_number=voucher_number,
                printed_invoice_number=printed_invoice_number,
                voucher_type=voucher_type,
                sync_started_at=datetime.now(UTC),
                processing_status=status,
                customer_name=customer_name,
                correlation_id=correlation_id,
            ),
        )

    async def finalize_log(
        self,
        log: TallySyncLog,
        *,
        status: TallySyncRunStatus,
        inventory_item_count: int = 0,
        successfully_updated: int = 0,
        already_sold: int = 0,
        missing_serial: int = 0,
        missing_model: int = 0,
        model_mismatches: int = 0,
        ignored_items: int = 0,
        error_details: str | None = None,
    ) -> TallySyncLog:
        completed = datetime.now(UTC)
        log.sync_completed_at = completed
        log.processing_duration_ms = int((completed - log.sync_started_at).total_seconds() * 1000)
        log.processing_status = status
        log.inventory_item_count = inventory_item_count
        log.successfully_updated = successfully_updated
        log.already_sold = already_sold
        log.missing_serial = missing_serial
        log.missing_model = missing_model
        log.model_mismatches = model_mismatches
        log.ignored_items = ignored_items
        log.error_details = error_details
        await self._session.flush()
        return log

    async def recent_runs(self, *, limit: int = 20) -> list[TallySyncLog]:
        statement = select(TallySyncLog).order_by(desc(TallySyncLog.sync_started_at)).limit(limit)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def aggregate_stats(self, company_sync_id: int) -> dict[str, int]:
        statement = select(TallySyncLog).where(TallySyncLog.tally_company_sync_id == company_sync_id)
        result = await self._session.execute(statement)
        logs = list(result.scalars().all())
        return {
            "invoices_processed": len(logs),
            "successfully_updated": sum(log.successfully_updated for log in logs),
            "already_sold": sum(log.already_sold for log in logs),
            "missing_serial": sum(log.missing_serial for log in logs),
            "missing_model": sum(log.missing_model for log in logs),
            "model_mismatches": sum(log.model_mismatches for log in logs),
            "ignored_items": sum(log.ignored_items for log in logs),
        }
