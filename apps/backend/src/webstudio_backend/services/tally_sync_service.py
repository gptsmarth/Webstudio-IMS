"""Production Tally ERP 9 synchronization service."""

from __future__ import annotations

import asyncio
import gzip
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import (
    AuditSource,
    InventoryStatus,
    NotificationCategory,
    NotificationSeverity,
    NotificationType,
    TallyLineOutcome,
    TallyProcessingStatus,
    TallyPurchaseStatus,
    TallySyncRunStatus,
)
from webstudio_backend.infrastructure.database.models.tally_company_sync import TallyCompanySync
from webstudio_backend.infrastructure.database.models.tally_purchase_line import TallyPurchaseLine
from webstudio_backend.infrastructure.database.models.tally_purchase_voucher import (
    TallyPurchaseVoucher,
)
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemRepository,
)
from webstudio_backend.infrastructure.repositories.location_repository import LocationRepository
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.infrastructure.repositories.sale_repository import SaleRepository
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import (
    TallyCompanySyncRepository,
)
from webstudio_backend.infrastructure.repositories.tally_line_decision_log_repository import (
    TallyLineDecisionLogRepository,
)
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_line_repository import (
    TallyProcessedInvoiceLineRepository,
)
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_repository import (
    TallyProcessedInvoiceRepository,
)
from webstudio_backend.infrastructure.repositories.tally_purchase_repository import (
    TallyPurchaseRepository,
)
from webstudio_backend.infrastructure.repositories.tally_sync_history_repository import (
    TallySyncHistoryRepository,
)
from webstudio_backend.infrastructure.repositories.tally_sync_log_repository import (
    TallySyncLogRepository,
)
from webstudio_backend.integrations.tally.constants import (
    DEFAULT_SYNC_INTERVAL_SECONDS,
    MONITORED_VOUCHER_TYPES,
    PURCHASE_VOUCHER_TYPES,
    VOUCHER_TYPE_STORE_MAP,
)
from webstudio_backend.integrations.tally.gst import resolve_line_sale_amounts
from webstudio_backend.integrations.tally.incremental_sync import (
    REPEATED_FAILURE_NOTIFICATION_THRESHOLD,
    STALE_SYNC_IN_PROGRESS_SECONDS,
    clamp_sync_interval_seconds,
    partition_by_guid_watermark,
    resolve_incremental_from_date,
    tally_sync_had_meaningful_progress,
)
from webstudio_backend.integrations.tally.purchase_normalization import _collapse
from webstudio_backend.integrations.tally.types import TallyInventoryLine, TallyVoucher
from webstudio_backend.integrations.tally.xml_client import TallyConnectionError
from webstudio_backend.integrations.tally.xml_parser import (
    catalog_model_matches_invoice,
    expand_inventory_lines,
    normalize_serial,
    parse_vouchers_xml,
    resolve_inventory_line_sale_amount,
)
from webstudio_backend.services.notification_service import NotificationService
from webstudio_backend.services.sale_snapshot import SaleProductSnapshot
from webstudio_backend.services.tally_connectivity_service import TallyConnectivityService

_sync_lock = asyncio.Lock()


def is_tally_sync_active() -> bool:
    return _sync_lock.locked()


def _filter_vouchers_in_date_window(
    vouchers: list[TallyVoucher],
    *,
    from_date: date,
    to_date: date,
) -> list[TallyVoucher]:
    """Keep vouchers whose DATE falls inside the requested window.

    Safety net for Tally builds that ignore SVFROMDATE/SVTODATE and return
    today's Day Book even for a historical request. Vouchers without a parsed
    date are kept (better to attempt processing than silently drop).
    """
    kept: list[TallyVoucher] = []
    for voucher in vouchers:
        voucher_date = voucher.voucher_date
        if voucher_date is None or from_date <= voucher_date <= to_date:
            kept.append(voucher)
    return kept


class TallyBackfillBusyError(Exception):
    """Raised when a backfill is requested while a sync is already running."""


@dataclass(slots=True)
class TallySyncCounters:
    vouchers_processed: int = 0
    invoices_checked: int = 0
    invoices_imported: int = 0
    invoices_skipped: int = 0
    watermark_skipped: int = 0
    inventory_entries_processed: int = 0
    sales_created: int = 0
    duplicates: int = 0
    missing_serials: int = 0
    missing_models: int = 0
    model_mismatches: int = 0
    failures: int = 0
    skipped_vouchers: int = 0


@dataclass(slots=True)
class TallySyncResult:
    sync_run_id: str
    success: bool
    message: str
    counters: TallySyncCounters = field(default_factory=TallySyncCounters)
    connection_status: str = "disconnected"
    last_error: str | None = None


class TallySyncService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = SystemSettingRepository(session)
        self._company_sync = TallyCompanySyncRepository(session)
        self._processed_invoices = TallyProcessedInvoiceRepository(session)
        self._processed_lines = TallyProcessedInvoiceLineRepository(session)
        self._purchase = TallyPurchaseRepository(session)
        self._decision_logs = TallyLineDecisionLogRepository(session)
        self._sync_logs = TallySyncLogRepository(session)
        self._sync_history = TallySyncHistoryRepository(session)
        self._inventory = InventoryItemRepository(session)
        self._sales = SaleRepository(session)
        self._locations = LocationRepository(session)
        self._product_models = ProductModelRepository(session)
        self._notifications = NotificationService(session)
        self._recorder = AuditRecorder(session)

    async def _get_bool(self, key: str, default: bool) -> bool:
        row = await self._settings.get_by_key(key)
        if row is None:
            return default
        return row.setting_value.lower() in {"1", "true", "yes"}

    async def _get_str(self, key: str, default: str = "") -> str:
        row = await self._settings.get_by_key(key)
        return row.setting_value if row and row.setting_value else default

    async def _get_int(self, key: str, default: int) -> int:
        row = await self._settings.get_by_key(key)
        if row is None:
            return default
        try:
            return int(row.setting_value)
        except ValueError:
            return default

    async def is_enabled(self) -> bool:
        return await self._get_bool("tally_enabled", False)

    async def get_connection_config(self) -> tuple[str, str, str, int]:
        host = await self._get_str("tally_host", "127.0.0.1")
        port = await self._get_str("tally_port", "9000")
        company = await self._get_str("tally_company_name", "WEBSTUDIO")
        interval = clamp_sync_interval_seconds(
            await self._get_int("tally_sync_interval_seconds", DEFAULT_SYNC_INTERVAL_SECONDS),
        )
        return host, port, company, interval

    async def test_connection(self) -> bool:
        diagnostics = await TallyConnectivityService(self._session).test_connection()
        return diagnostics.reachable

    async def backfill_purchases(
        self, *, from_date: date, to_date: date | None = None
    ) -> dict[str, int]:
        """Read-only historical fetch of PURCHASE vouchers into the review queue.

        Independent of the Sales pipeline: never advances the GUID watermark,
        never processes sales, and never creates inventory. Idempotent by
        voucher GUID (already-seen purchases are only touched). Raises
        ``TallyConnectionError`` when the workstation is unreachable.
        """
        _, _, company_name, _ = await self.get_connection_config()
        company_sync = await self._company_sync.get_or_create(company_name)

        connectivity = TallyConnectivityService(self._session)
        diagnostics = await connectivity.ensure_workstation_reachable(company_name=company_name)
        if not diagnostics.reachable:
            raise TallyConnectionError(
                diagnostics.user_message,
                user_message=diagnostics.user_message,
            )
        client = await connectivity.build_client_for_sync(diagnostics)

        resolved_to = to_date or datetime.now(UTC).date()
        exports = await client.export_monitored_voucher_types(
            company_name=company_name,
            from_date=from_date,
            to_date=resolved_to,
            historical=True,
        )
        vouchers: list[TallyVoucher] = []
        for xml_text in exports.values():
            vouchers.extend(parse_vouchers_xml(xml_text))
        vouchers = _filter_vouchers_in_date_window(
            vouchers, from_date=from_date, to_date=resolved_to
        )

        purchase_vouchers = [
            voucher for voucher in vouchers if voucher.voucher_type in PURCHASE_VOUCHER_TYPES
        ]
        guids = [voucher.guid for voucher in purchase_vouchers]
        existing_before = await self._purchase.count_existing_guids(company_sync.id, guids)
        await self._project_purchase_queue(vouchers, company_sync)
        unique = len(set(guids))
        return {
            "fetched": len(purchase_vouchers),
            "new": max(0, unique - existing_before),
            "export_source": next(iter(exports.keys()), "none"),
        }

    async def backfill_sales(
        self,
        *,
        from_date: date,
        to_date: date | None = None,
        correlation_id: str,
    ) -> dict[str, int]:
        """Historical SALES sync: fetch vouchers for a past window and process
        any that were never imported (mark matching serials sold, create sales).

        Reuses the exact per-voucher pipeline of the regular sync, with two
        deliberate differences:
          * The GUID watermark is NOT used for skipping and is NEVER advanced —
            the incremental sync continues exactly where it was.
          * Already-processed invoices (GUID / fingerprint) are skipped, so the
            backfill is idempotent and can never double-sell a serial.
        """
        if _sync_lock.locked():
            raise TallyBackfillBusyError("Synchronization already in progress. Try again shortly.")

        async with _sync_lock:
            _, _, company_name, _ = await self.get_connection_config()
            company_sync = await self._company_sync.get_or_create(company_name)

            connectivity = TallyConnectivityService(self._session)
            diagnostics = await connectivity.ensure_workstation_reachable(company_name=company_name)
            if not diagnostics.reachable:
                raise TallyConnectionError(
                    diagnostics.user_message,
                    user_message=diagnostics.user_message,
                )
            client = await connectivity.build_client_for_sync(diagnostics)

            resolved_to = to_date or datetime.now(UTC).date()
            exports = await client.export_monitored_voucher_types(
                company_name=company_name,
                from_date=from_date,
                to_date=resolved_to,
                historical=True,
            )
            all_vouchers: list[TallyVoucher] = []
            for xml_text in exports.values():
                all_vouchers.extend(parse_vouchers_xml(xml_text))
            all_vouchers = _filter_vouchers_in_date_window(
                all_vouchers, from_date=from_date, to_date=resolved_to
            )
            all_vouchers.sort(key=lambda voucher: (voucher.voucher_date, voucher.guid))

            sales_vouchers = [
                voucher
                for voucher in all_vouchers
                if voucher.voucher_type in MONITORED_VOUCHER_TYPES
            ]

            sync_run_id = uuid.uuid4()
            counters = TallySyncCounters()
            history = await self._sync_history.create_started(
                company_sync_id=company_sync.id,
                sync_run_id=sync_run_id,
                correlation_id=correlation_id,
            )

            error_messages: list[str] = []
            for voucher in sales_vouchers:
                counters.invoices_checked += 1
                if await self._should_skip_voucher(company_sync.id, voucher):
                    counters.invoices_skipped += 1
                    continue

                invoice, created = await self._processed_invoices.get_or_create_pending(
                    company_sync_id=company_sync.id,
                    guid=voucher.guid,
                    master_id=voucher.master_id,
                    voucher_number=voucher.voucher_number,
                    printed_invoice_number=voucher.printed_invoice_number,
                    voucher_type=voucher.voucher_type,
                    voucher_date=voucher.voucher_date,
                    party_name=voucher.party_name,
                    amount=voucher.amount,
                )
                if not created and invoice.processing_status in {
                    TallyProcessingStatus.SUCCESS,
                    TallyProcessingStatus.COMPLETED_WITH_REVIEW_REQUIRED,
                    TallyProcessingStatus.SKIPPED,
                }:
                    counters.invoices_skipped += 1
                    continue

                counters.vouchers_processed += 1
                if created:
                    counters.invoices_imported += 1

                try:
                    line_stats = await self._process_voucher(
                        voucher=voucher,
                        company_sync=company_sync,
                        invoice_id=invoice.id,
                        company_name=company_name,
                        sync_run_id=sync_run_id,
                        correlation_id=correlation_id,
                        counters=counters,
                    )
                    status = self._derive_voucher_status(line_stats)
                    await self._processed_invoices.update_status(invoice, status)
                    run_status = (
                        TallySyncRunStatus.SUCCESS
                        if status
                        in {
                            TallyProcessingStatus.SUCCESS,
                            TallyProcessingStatus.COMPLETED_WITH_REVIEW_REQUIRED,
                        }
                        else (
                            TallySyncRunStatus.PARTIAL_SUCCESS
                            if status is TallyProcessingStatus.PARTIAL_SUCCESS
                            else TallySyncRunStatus.FAILED
                        )
                    )
                    if status is TallyProcessingStatus.FAILED:
                        counters.failures += 1
                        error_messages.append(
                            f"{voucher.printed_invoice_number}: processing failed"
                        )
                except Exception as exc:  # noqa: BLE001 — isolate voucher failures
                    counters.failures += 1
                    error_messages.append(f"{voucher.printed_invoice_number}: {exc}")
                    company_sync = await self._company_sync.get_or_create(company_name)
                    invoice, _ = await self._processed_invoices.get_or_create_pending(
                        company_sync_id=company_sync.id,
                        guid=voucher.guid,
                        master_id=voucher.master_id,
                        voucher_number=voucher.voucher_number,
                        printed_invoice_number=voucher.printed_invoice_number,
                        voucher_type=voucher.voucher_type,
                        voucher_date=voucher.voucher_date,
                        party_name=voucher.party_name,
                        amount=voucher.amount,
                    )
                    await self._processed_invoices.update_status(
                        invoice, TallyProcessingStatus.FAILED
                    )
                    run_status = TallySyncRunStatus.FAILED
                    line_stats = {
                        "total": 0,
                        "completed": 0,
                        "failed": 1,
                        "sales": 0,
                        "duplicates": 0,
                        "missing_serial": 0,
                        "missing_model": 0,
                        "model_mismatches": 0,
                        "ignored": 0,
                    }

                log = await self._sync_logs.create_run_log(
                    sync_run_id=sync_run_id,
                    company_sync_id=company_sync.id,
                    correlation_id=correlation_id,
                    voucher_guid=voucher.guid,
                    voucher_number=voucher.voucher_number,
                    printed_invoice_number=voucher.printed_invoice_number,
                    voucher_type=voucher.voucher_type,
                    customer_name=voucher.party_name,
                    processed_invoice_id=invoice.id,
                    status=run_status,
                )
                await self._sync_logs.finalize_log(
                    log,
                    status=run_status,
                    inventory_item_count=line_stats["total"],
                    successfully_updated=line_stats["sales"],
                    already_sold=line_stats["duplicates"],
                    missing_serial=line_stats["missing_serial"],
                    missing_model=line_stats["missing_model"],
                    model_mismatches=line_stats["model_mismatches"],
                    ignored_items=line_stats["ignored"],
                )

            # Purchases seen in the window are also projected into the review
            # queue (idempotent) — same as the regular sync cycle.
            await self._project_purchase_queue(all_vouchers, company_sync)

            await self._sync_history.finalize(
                history,
                status="success" if counters.failures == 0 else "partial",
                invoices_checked=counters.invoices_checked,
                invoices_imported=counters.invoices_imported,
                invoices_skipped=counters.invoices_skipped,
                errors_count=counters.failures,
                error_summary=("; ".join(error_messages[:5]) if error_messages else None),
            )
            await self._recorder.record_system_action(
                entity_type="tally_sync",
                entity_id=str(sync_run_id),
                description=f"Historical sales backfill from {from_date.isoformat()}",
                source=AuditSource.TALLY_SYNC,
                new_value={
                    "from_date": from_date.isoformat(),
                    "to_date": (to_date or datetime.now(UTC).date()).isoformat(),
                    "fetched": len(sales_vouchers),
                    "invoices_checked": counters.invoices_checked,
                    "invoices_imported": counters.invoices_imported,
                    "invoices_skipped": counters.invoices_skipped,
                    "sales_created": counters.sales_created,
                    "failures": counters.failures,
                },
            )

            return {
                "fetched": len(sales_vouchers),
                "checked": counters.invoices_checked,
                "imported": counters.invoices_imported,
                "skipped": counters.invoices_skipped,
                "sales_created": counters.sales_created,
                "duplicates": counters.duplicates,
                "missing_serials": counters.missing_serials,
                "failures": counters.failures,
                "export_source": next(iter(exports.keys()), "none"),
            }

    async def run_sync(
        self, *, correlation_id: str, triggered_by_user_id: int | None = None
    ) -> TallySyncResult:
        if _sync_lock.locked():
            return TallySyncResult(
                sync_run_id=str(uuid.uuid4()),
                success=False,
                message="Synchronization already in progress.",
                connection_status="connected",
            )

        async with _sync_lock:
            return await self._run_sync_locked(
                correlation_id=correlation_id,
                triggered_by_user_id=triggered_by_user_id,
            )

    async def _run_sync_locked(
        self,
        *,
        correlation_id: str,
        triggered_by_user_id: int | None,
    ) -> TallySyncResult:
        sync_run_id = uuid.uuid4()
        counters = TallySyncCounters()
        started_at = datetime.now(UTC)

        if not await self.is_enabled():
            return TallySyncResult(
                sync_run_id=str(sync_run_id),
                success=False,
                message="Tally integration is disabled.",
            )

        host, port, company_name, _ = await self.get_connection_config()
        company_sync = await self._company_sync.get_or_create(company_name)

        if company_sync.sync_in_progress:
            open_run = await self._sync_history.get_open_for_company(company_sync.id)
            stale = False
            if open_run is None:
                stale = True
            else:
                age_seconds = (datetime.now(UTC) - open_run.started_at).total_seconds()
                stale = age_seconds > STALE_SYNC_IN_PROGRESS_SECONDS
            if stale:
                await self._company_sync.update_sync_state(company_sync, sync_in_progress=False)
                if open_run is not None:
                    await self._sync_history.finalize(
                        open_run,
                        status="failed",
                        invoices_checked=0,
                        invoices_imported=0,
                        invoices_skipped=0,
                        errors_count=0,
                        error_summary="Sync interrupted — stale lock cleared automatically.",
                    )
            else:
                return TallySyncResult(
                    sync_run_id=str(sync_run_id),
                    success=False,
                    message="Synchronization already in progress.",
                    connection_status=company_sync.connection_status,
                )

        history = await self._sync_history.create_started(
            company_sync_id=company_sync.id,
            sync_run_id=sync_run_id,
            correlation_id=correlation_id,
        )
        await self._company_sync.update_sync_state(company_sync, sync_in_progress=True)

        try:
            return await self._execute_sync_cycle(
                sync_run_id=sync_run_id,
                company_sync=company_sync,
                company_name=company_name,
                correlation_id=correlation_id,
                counters=counters,
                history=history,
                started_at=started_at,
            )
        finally:
            await self._company_sync.update_sync_state(company_sync, sync_in_progress=False)

    async def _execute_sync_cycle(
        self,
        *,
        sync_run_id: uuid.UUID,
        company_sync: TallyCompanySync,
        company_name: str,
        correlation_id: str,
        counters: TallySyncCounters,
        history,
        started_at: datetime,
    ) -> TallySyncResult:
        connectivity = TallyConnectivityService(self._session)
        diagnostics = await connectivity.ensure_workstation_reachable(company_name=company_name)

        if not diagnostics.reachable:
            message = diagnostics.user_message
            await self._sync_history.finalize(
                history,
                status="offline",
                invoices_checked=0,
                invoices_imported=0,
                invoices_skipped=0,
                errors_count=0,
            )
            await self._recorder.record_system_action(
                entity_type="tally_sync",
                entity_id=str(sync_run_id),
                description="Tally sync skipped — workstation offline",
                source=AuditSource.TALLY_SYNC,
            )
            return TallySyncResult(
                sync_run_id=str(sync_run_id),
                success=False,
                message=message,
                counters=counters,
                connection_status="disconnected",
                last_error=message,
            )

        try:
            client = await connectivity.build_client_for_sync(diagnostics)
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            await self._company_sync.update_sync_state(
                company_sync,
                connection_status="error",
                last_error=message,
            )
            await self._sync_history.finalize(
                history,
                status="offline",
                invoices_checked=0,
                invoices_imported=0,
                invoices_skipped=0,
                errors_count=0,
                error_summary=message,
            )
            return TallySyncResult(
                sync_run_id=str(sync_run_id),
                success=False,
                message=message,
                counters=counters,
                connection_status="error",
                last_error=message,
            )

        await self._company_sync.update_sync_state(
            company_sync,
            connection_status="connected",
            clear_last_error=True,
        )

        from_date = resolve_incremental_from_date(company_sync)
        all_vouchers: list[TallyVoucher] = []
        try:
            exports = await client.export_monitored_voucher_types(
                company_name=company_name,
                from_date=from_date,
            )
            for _voucher_type, xml_text in exports.items():
                all_vouchers.extend(parse_vouchers_xml(xml_text))
        except TallyConnectionError as exc:
            message = exc.user_message
            await self._company_sync.update_sync_state(
                company_sync,
                connection_status="error",
                last_error=message,
            )
            await self._sync_history.finalize(
                history,
                status="offline",
                invoices_checked=counters.invoices_checked,
                invoices_imported=counters.invoices_imported,
                invoices_skipped=counters.invoices_skipped,
                errors_count=0,
                error_summary=message,
            )
            return TallySyncResult(
                sync_run_id=str(sync_run_id),
                success=False,
                message=message,
                counters=counters,
                connection_status="error",
                last_error=message,
            )

        all_vouchers.sort(key=lambda voucher: (voucher.voucher_date, voucher.guid))
        last_imported_guid: str | None = company_sync.last_processed_guid
        last_imported_voucher_date: date | None = company_sync.last_imported_voucher_date
        last_processed_master_id: str | None = company_sync.last_processed_master_id
        last_processed_invoice_number: str | None = company_sync.last_processed_invoice_number
        last_processed_voucher_type: str | None = company_sync.last_processed_voucher_type
        error_messages: list[str] = []

        monitored = [
            voucher for voucher in all_vouchers if voucher.voucher_type in MONITORED_VOUCHER_TYPES
        ]
        watermark = partition_by_guid_watermark(monitored, last_imported_guid)
        if watermark.historical_skipped:
            counters.invoices_checked += watermark.historical_skipped
            counters.invoices_skipped += watermark.historical_skipped
            counters.watermark_skipped += watermark.historical_skipped

        for voucher in watermark.to_process:
            counters.invoices_checked += 1
            if await self._should_skip_voucher(company_sync.id, voucher):
                counters.invoices_skipped += 1
                await self._sync_logs.create_run_log(
                    sync_run_id=sync_run_id,
                    company_sync_id=company_sync.id,
                    correlation_id=correlation_id,
                    voucher_guid=voucher.guid,
                    voucher_number=voucher.voucher_number,
                    printed_invoice_number=voucher.printed_invoice_number,
                    voucher_type=voucher.voucher_type,
                    customer_name=voucher.party_name,
                    status=TallySyncRunStatus.SKIPPED,
                )
                continue

            invoice, created = await self._processed_invoices.get_or_create_pending(
                company_sync_id=company_sync.id,
                guid=voucher.guid,
                master_id=voucher.master_id,
                voucher_number=voucher.voucher_number,
                printed_invoice_number=voucher.printed_invoice_number,
                voucher_type=voucher.voucher_type,
                voucher_date=voucher.voucher_date,
                party_name=voucher.party_name,
                amount=voucher.amount,
            )
            if not created and invoice.processing_status in {
                TallyProcessingStatus.SUCCESS,
                TallyProcessingStatus.COMPLETED_WITH_REVIEW_REQUIRED,
                TallyProcessingStatus.SKIPPED,
            }:
                counters.invoices_skipped += 1
                continue

            counters.vouchers_processed += 1
            if created:
                counters.invoices_imported += 1

            try:
                line_stats = await self._process_voucher(
                    voucher=voucher,
                    company_sync=company_sync,
                    invoice_id=invoice.id,
                    company_name=company_name,
                    sync_run_id=sync_run_id,
                    correlation_id=correlation_id,
                    counters=counters,
                )
                status = self._derive_voucher_status(line_stats)
                await self._processed_invoices.update_status(invoice, status)
                run_status = (
                    TallySyncRunStatus.SUCCESS
                    if status
                    in {
                        TallyProcessingStatus.SUCCESS,
                        TallyProcessingStatus.COMPLETED_WITH_REVIEW_REQUIRED,
                    }
                    else (
                        TallySyncRunStatus.PARTIAL_SUCCESS
                        if status is TallyProcessingStatus.PARTIAL_SUCCESS
                        else TallySyncRunStatus.FAILED
                    )
                )
                if status is TallyProcessingStatus.FAILED:
                    counters.failures += 1
                    error_messages.append(
                        f"{voucher.printed_invoice_number}: processing failed",
                    )
            except Exception as exc:  # noqa: BLE001
                counters.failures += 1
                error_messages.append(f"{voucher.printed_invoice_number}: {exc}")
                company_sync = await self._company_sync.get_or_create(company_name)
                invoice, _ = await self._processed_invoices.get_or_create_pending(
                    company_sync_id=company_sync.id,
                    guid=voucher.guid,
                    master_id=voucher.master_id,
                    voucher_number=voucher.voucher_number,
                    printed_invoice_number=voucher.printed_invoice_number,
                    voucher_type=voucher.voucher_type,
                    voucher_date=voucher.voucher_date,
                    party_name=voucher.party_name,
                    amount=voucher.amount,
                )
                await self._processed_invoices.update_status(invoice, TallyProcessingStatus.FAILED)
                run_status = TallySyncRunStatus.FAILED
                line_stats = {
                    "total": 0,
                    "completed": 0,
                    "failed": 1,
                    "sales": 0,
                    "duplicates": 0,
                    "missing_serial": 0,
                    "missing_model": 0,
                    "model_mismatches": 0,
                    "ignored": 0,
                }

            log = await self._sync_logs.create_run_log(
                sync_run_id=sync_run_id,
                company_sync_id=company_sync.id,
                correlation_id=correlation_id,
                voucher_guid=voucher.guid,
                voucher_number=voucher.voucher_number,
                printed_invoice_number=voucher.printed_invoice_number,
                voucher_type=voucher.voucher_type,
                customer_name=voucher.party_name,
                processed_invoice_id=invoice.id,
                status=run_status,
            )
            await self._sync_logs.finalize_log(
                log,
                status=run_status,
                inventory_item_count=line_stats["total"],
                successfully_updated=line_stats["sales"],
                already_sold=line_stats["duplicates"],
                missing_serial=line_stats["missing_serial"],
                missing_model=line_stats["missing_model"],
                model_mismatches=line_stats["model_mismatches"],
                ignored_items=line_stats["ignored"],
            )

            last_imported_guid = voucher.guid
            last_processed_master_id = voucher.master_id
            last_processed_invoice_number = voucher.printed_invoice_number or voucher.voucher_number
            last_processed_voucher_type = voucher.voucher_type
            if (
                last_imported_voucher_date is None
                or voucher.voucher_date >= last_imported_voucher_date
            ):
                last_imported_voucher_date = voucher.voucher_date

            await self._recorder.record_system_action(
                entity_type="tally_voucher",
                entity_id=voucher.guid,
                description=f"Voucher processed ({voucher.printed_invoice_number})",
                source=AuditSource.TALLY_SYNC,
                new_value={
                    "printed_invoice_number": voucher.printed_invoice_number,
                    "voucher_number": voucher.voucher_number,
                    "voucher_type": voucher.voucher_type,
                    "status": run_status.value,
                },
            )

        # Additive Purchase Import Queue projection. Runs AFTER sales processing and
        # is fully isolated: any failure here NEVER affects the sales sync outcome,
        # the GUID watermark, or company-sync state.
        await self._project_purchase_queue(all_vouchers, company_sync)

        now = datetime.now(UTC)
        duration_ms = int((now - started_at).total_seconds() * 1000)
        run_success = counters.failures == 0
        had_meaningful_progress = tally_sync_had_meaningful_progress(
            invoices_imported=counters.invoices_imported,
            sales_created=counters.sales_created,
        )
        history_status = (
            "success" if run_success else "partial" if had_meaningful_progress else "failed"
        )
        consecutive_failures = await self._finalize_company_sync_state(
            company_sync=company_sync,
            counters=counters,
            run_success=run_success,
            had_meaningful_progress=had_meaningful_progress,
            finished_at=now,
            duration_ms=duration_ms,
            last_imported_guid=last_imported_guid,
            last_imported_voucher_date=last_imported_voucher_date,
            last_processed_master_id=last_processed_master_id,
            last_processed_invoice_number=last_processed_invoice_number,
            last_processed_voucher_type=last_processed_voucher_type,
        )

        await self._sync_history.finalize(
            history,
            status=history_status,
            invoices_checked=counters.invoices_checked,
            invoices_imported=counters.invoices_imported,
            invoices_skipped=counters.invoices_skipped,
            errors_count=counters.failures,
            error_summary="; ".join(error_messages[:5]) if error_messages else None,
        )

        await self._notify_sync_outcome(
            company_name=company_name,
            counters=counters,
            consecutive_failures=consecutive_failures if not run_success else 0,
            success=run_success,
        )
        await self._recorder.record_system_action(
            entity_type="tally_sync",
            entity_id=str(sync_run_id),
            description=(
                "Tally sync completed" if run_success else "Tally sync completed with issues"
            ),
            source=AuditSource.TALLY_SYNC,
            new_value={
                "invoices_checked": counters.invoices_checked,
                "invoices_imported": counters.invoices_imported,
                "invoices_skipped": counters.invoices_skipped,
                "vouchers_processed": counters.vouchers_processed,
                "sales_created": counters.sales_created,
                "failures": counters.failures,
            },
        )

        return TallySyncResult(
            sync_run_id=str(sync_run_id),
            success=run_success,
            message=(
                "Synchronization completed."
                if run_success
                else "Synchronization completed with issues."
            ),
            counters=counters,
            connection_status="connected",
        )

    async def _should_skip_voucher(self, company_sync_id: int, voucher: TallyVoucher) -> bool:
        terminal = {
            TallyProcessingStatus.SUCCESS,
            TallyProcessingStatus.COMPLETED_WITH_REVIEW_REQUIRED,
            TallyProcessingStatus.SKIPPED,
        }
        by_guid = await self._processed_invoices.find_by_guid(company_sync_id, voucher.guid)
        if by_guid is not None and by_guid.processing_status in terminal:
            return True
        by_fallback = await self._processed_invoices.find_by_fallback_fingerprint(
            company_sync_id,
            voucher_date=voucher.voucher_date,
            voucher_number=voucher.voucher_number,
            amount=voucher.amount,
            party_name=voucher.party_name,
        )
        return by_fallback is not None and by_fallback.processing_status in terminal

    async def _finalize_company_sync_state(
        self,
        *,
        company_sync: TallyCompanySync,
        counters: TallySyncCounters,
        run_success: bool,
        had_meaningful_progress: bool,
        finished_at: datetime,
        duration_ms: int,
        last_imported_guid: str | None,
        last_imported_voucher_date: date | None,
        last_processed_master_id: str | None = None,
        last_processed_invoice_number: str | None = None,
        last_processed_voucher_type: str | None = None,
    ) -> int:
        """Persist sync metadata and return consecutive failure count after this run."""
        common_state = {
            "last_sync_duration_ms": duration_ms,
            "last_invoices_imported_count": counters.invoices_imported,
            "connection_status": "connected",
        }

        if run_success or had_meaningful_progress:
            progress_state: dict[str, object] = {"clear_last_error": True}
            if run_success:
                progress_state["last_successful_sync_at"] = finished_at
            if had_meaningful_progress or run_success:
                if last_imported_guid is not None:
                    progress_state["last_processed_guid"] = last_imported_guid
                if last_imported_voucher_date is not None:
                    progress_state["last_imported_voucher_date"] = last_imported_voucher_date
                if last_processed_master_id is not None:
                    progress_state["last_processed_master_id"] = last_processed_master_id
                if last_processed_invoice_number is not None:
                    progress_state["last_processed_invoice_number"] = last_processed_invoice_number
                if last_processed_voucher_type is not None:
                    progress_state["last_processed_voucher_type"] = last_processed_voucher_type
            await self._company_sync.update_sync_state(
                company_sync,
                consecutive_sync_failures=0,
                **common_state,
                **progress_state,
            )
            return 0

        consecutive_failures = company_sync.consecutive_sync_failures + 1
        await self._company_sync.update_sync_state(
            company_sync,
            consecutive_sync_failures=consecutive_failures,
            **common_state,
        )
        return consecutive_failures

    async def _notify_sync_outcome(
        self,
        *,
        company_name: str,
        counters: TallySyncCounters,
        consecutive_failures: int,
        success: bool,
    ) -> None:
        if not await self._get_bool("tally_alerts_enabled", True):
            return
        if counters.invoices_imported > 0:
            await self._notifications.create_notification(
                notification_type=NotificationType.TALLY_SYNC_COMPLETED,
                severity=NotificationSeverity.INFO,
                title="New Tally invoices imported",
                message=(
                    f"{counters.invoices_imported} invoice(s) imported from Tally "
                    f"({counters.invoices_skipped} skipped as already processed)."
                ),
                category=NotificationCategory.TALLY_SYNC,
                tally_company_name=company_name,
            )
        if not success and consecutive_failures >= REPEATED_FAILURE_NOTIFICATION_THRESHOLD:
            await self._notifications.create_notification(
                notification_type=NotificationType.SYNC_FAILURE,
                severity=NotificationSeverity.ERROR,
                title="Tally synchronization failing repeatedly",
                message=(
                    f"Tally sync has failed {consecutive_failures} consecutive times. "
                    "Check Tally connectivity and sync logs."
                ),
                category=NotificationCategory.TALLY_SYNC,
                tally_company_name=company_name,
            )

    async def _process_voucher(
        self,
        *,
        voucher: TallyVoucher,
        company_sync: TallyCompanySync,
        invoice_id: int,
        company_name: str,
        sync_run_id: uuid.UUID,
        correlation_id: str,
        counters: TallySyncCounters,
    ) -> dict[str, int]:
        """
        Process one voucher atomically.

        Technical exceptions roll back the voucher. Business outcomes
        (additional product / review required) complete the voucher safely.
        """
        del company_sync, sync_run_id, correlation_id  # reserved for future tracing
        stats = {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "sales": 0,
            "duplicates": 0,
            "missing_serial": 0,
            "missing_model": 0,
            "model_mismatches": 0,
            "ignored": 0,
            "additional_products": 0,
            "review_required": 0,
        }
        mapped_location = await self._resolve_store_location(voucher.voucher_type)
        invoice = await self._processed_invoices.get_by_id(invoice_id)
        if invoice is None:
            raise RuntimeError(f"Processed invoice {invoice_id} missing")

        try:
            async with self._session.begin_nested():
                await self._attach_invoice_archive_and_totals(invoice, voucher)
                for line in expand_inventory_lines(voucher.inventory_lines):
                    stats["total"] += 1
                    counters.inventory_entries_processed += 1
                    line_row = await self._processed_lines.get_or_create_line(
                        invoice_id=invoice_id,
                        line_index=line.line_index,
                        serial_number=line.serial_number,
                        stock_item_name=line.stock_item_name,
                        serial_source=line.serial_source,
                        normalized_serial=line.normalized_serial,
                        quantity=line.quantity,
                        rate=line.rate,
                        taxable_amount=line.taxable_amount,
                        cgst_amount=line.cgst_amount,
                        sgst_amount=line.sgst_amount,
                        igst_amount=line.igst_amount,
                        cess_amount=line.cess_amount,
                        line_total=line.line_total or line.amount,
                    )
                    if line_row.line_status.value == "completed":
                        stats["completed"] += 1
                        continue

                    await self._process_inventory_line(
                        voucher=voucher,
                        line=line,
                        line_row=line_row,
                        invoice_id=invoice_id,
                        company_name=company_name,
                        mapped_location_id=mapped_location.id if mapped_location else None,
                        stats=stats,
                        counters=counters,
                    )
        except Exception:
            # Nested transaction rolls back only this voucher's work.
            raise

        if stats["review_required"] > 0 and stats["failed"] == 0:
            invoice.review_required = True
            await self._session.flush()

        return stats

    async def _attach_invoice_archive_and_totals(
        self,
        invoice,
        voucher: TallyVoucher,
    ) -> None:
        if voucher.raw_xml and not invoice.raw_xml_gzip:
            invoice.raw_xml_gzip = gzip.compress(voucher.raw_xml.encode("utf-8"))
        invoice.payment_mode = voucher.payment_mode
        invoice.narration = voucher.narration
        invoice.imported_at = datetime.now(UTC)
        totals = voucher.totals
        invoice.subtotal = totals.subtotal
        invoice.discount_amount = totals.discount_amount
        invoice.round_off = totals.round_off
        invoice.cgst_amount = totals.cgst_amount
        invoice.sgst_amount = totals.sgst_amount
        invoice.igst_amount = totals.igst_amount
        invoice.cess_amount = totals.cess_amount
        invoice.grand_total = totals.grand_total or (
            Decimal(voucher.amount) if voucher.amount else None
        )
        await self._session.flush()

    async def _process_inventory_line(
        self,
        *,
        voucher: TallyVoucher,
        line: TallyInventoryLine,
        line_row,
        invoice_id: int,
        company_name: str,
        mapped_location_id: int | None,
        stats: dict[str, int],
        counters: TallySyncCounters,
    ) -> TallyLineOutcome:
        """
        Deterministic serial-only matching.

        CASE A — serial found, model matches → sell
        CASE B — serial found, model differs → sell + review required
        CASE C1 — no serial extracted → additional product (no inventory change)
        CASE C2 — serial extracted but not in IMS → unmatched serialized item (visible, no sell)
        CASE D — duplicate serial rows in IMS → review required (no sell)
        CASE E — serial already sold → review required (no duplicate sale)
        """
        extracted = line.serial_number
        normalized = line.normalized_serial or normalize_serial(extracted)

        # CASE C1 — no serial: bag / warranty / software / consumables → additional product
        if not normalized:
            await self._complete_additional_product(
                voucher=voucher,
                line=line,
                line_row=line_row,
                invoice_id=invoice_id,
                reason="No serial on invoice line — stored as additional product.",
            )
            stats["completed"] += 1
            stats["additional_products"] += 1
            stats["ignored"] += 1
            return TallyLineOutcome.ADDITIONAL_PRODUCT

        matches = await self._inventory.find_all_by_serial_number(normalized)

        # EAN-as-serial pool — matched unit(s) belong to a duplicate-serial (EAN)
        # brand. Treat this line as a QUANTITY sale from the shared pool: deduct
        # `quantity` available units FIFO. Non-shared (normal) brands never enter
        # this branch, so the unique-serial path below is unchanged.
        if any(match.serial_is_shared for match in matches):
            return await self._process_shared_ean_sale(
                voucher=voucher,
                line=line,
                line_row=line_row,
                invoice_id=invoice_id,
                company_name=company_name,
                mapped_location_id=mapped_location_id,
                extracted=extracted,
                normalized=normalized,
                stats=stats,
                counters=counters,
            )

        # CASE D — duplicate serials in IMS
        if len(matches) > 1:
            reason = (
                f"Duplicate serial {normalized} found in IMS "
                f"({len(matches)} rows) — review required."
            )
            await self._processed_lines.complete_line(
                line_row,
                outcome=TallyLineOutcome.REVIEW_REQUIRED_DUPLICATE_SERIAL,
                match_result="duplicate_serial_in_ims",
                decision="review_required",
                decision_reason=reason,
                review_required=True,
            )
            await self._decision_logs.record(
                invoice_id=invoice_id,
                line_id=line_row.id,
                voucher_guid=voucher.guid,
                line_index=line.line_index,
                serial_source=line.serial_source,
                extracted_serial=extracted,
                normalized_serial=normalized,
                inventory_item_id=None,
                match_result="duplicate_serial_in_ims",
                decision="review_required",
                reason=reason,
            )
            await self._notifications.create_notification(
                notification_type=NotificationType.DUPLICATE_SALE,
                severity=NotificationSeverity.WARNING,
                title="Duplicate serial in inventory",
                message=reason,
                category=NotificationCategory.TALLY_SYNC,
                invoice_number=voucher.printed_invoice_number,
                tally_company_name=company_name,
                tally_voucher_number=voucher.voucher_number,
                voucher_type=voucher.voucher_type,
                customer_name=voucher.party_name,
                serial_number=normalized,
                product_model_number=line.stock_item_name,
            )
            stats["completed"] += 1
            stats["review_required"] += 1
            return TallyLineOutcome.REVIEW_REQUIRED_DUPLICATE_SERIAL

        # CASE C2 — serial extracted but not managed in IMS
        if not matches:
            await self._complete_unmatched_serialized_item(
                voucher=voucher,
                line=line,
                line_row=line_row,
                invoice_id=invoice_id,
                reason="Serial not managed in IMS",
            )
            stats["completed"] += 1
            stats["missing_serial"] += 1
            counters.missing_serials += 1
            return TallyLineOutcome.UNMATCHED_SERIALIZED_ITEM

        inventory_item = matches[0]

        # CASE E — already sold
        if inventory_item.status is InventoryStatus.SOLD:
            reason = (
                f"Serial {normalized} is already sold in IMS — "
                "duplicate sale blocked; review required."
            )
            await self._processed_lines.complete_line(
                line_row,
                outcome=TallyLineOutcome.REVIEW_REQUIRED_ALREADY_SOLD,
                inventory_item_id=inventory_item.id,
                match_result="already_sold",
                decision="review_required",
                decision_reason=reason,
                review_required=True,
            )
            await self._decision_logs.record(
                invoice_id=invoice_id,
                line_id=line_row.id,
                voucher_guid=voucher.guid,
                line_index=line.line_index,
                serial_source=line.serial_source,
                extracted_serial=extracted,
                normalized_serial=normalized,
                inventory_item_id=inventory_item.id,
                match_result="already_sold",
                decision="review_required",
                reason=reason,
            )
            await self._notifications.create_duplicate_sale_notification(
                title="Duplicate sale detected",
                message=(
                    f"Invoice {voucher.printed_invoice_number} references serial {normalized} "
                    "which is already sold."
                ),
                invoice_number=voucher.printed_invoice_number,
                serial_number=normalized,
                tally_company_name=company_name,
                tally_voucher_number=voucher.voucher_number,
                voucher_type=voucher.voucher_type,
                customer_name=voucher.party_name,
                product_model_number=line.stock_item_name,
                inventory_item_id=inventory_item.id,
            )
            stats["completed"] += 1
            stats["duplicates"] += 1
            stats["review_required"] += 1
            counters.duplicates += 1
            return TallyLineOutcome.REVIEW_REQUIRED_ALREADY_SOLD

        if inventory_item.status is not InventoryStatus.AVAILABLE:
            reason = (
                f"Serial {normalized} status is {inventory_item.status.value} — "
                "not available for sale; review required (no inventory change)."
            )
            await self._processed_lines.complete_line(
                line_row,
                outcome=TallyLineOutcome.REVIEW_REQUIRED_NOT_AVAILABLE,
                inventory_item_id=inventory_item.id,
                match_result="not_available",
                decision="review_required",
                decision_reason=reason,
                review_required=True,
            )
            await self._decision_logs.record(
                invoice_id=invoice_id,
                line_id=line_row.id,
                voucher_guid=voucher.guid,
                line_index=line.line_index,
                serial_source=line.serial_source,
                extracted_serial=extracted,
                normalized_serial=normalized,
                inventory_item_id=inventory_item.id,
                match_result="not_available",
                decision="review_required",
                reason=reason,
            )
            await self._notifications.create_notification(
                notification_type=NotificationType.SERIAL_NUMBER_MISSING,
                severity=NotificationSeverity.WARNING,
                title="Serial not available for sale",
                message=reason,
                category=NotificationCategory.TALLY_SYNC,
                invoice_number=voucher.printed_invoice_number,
                tally_company_name=company_name,
                tally_voucher_number=voucher.voucher_number,
                voucher_type=voucher.voucher_type,
                customer_name=voucher.party_name,
                serial_number=normalized,
                product_model_number=line.stock_item_name,
                inventory_item_id=inventory_item.id,
            )
            stats["completed"] += 1
            stats["review_required"] += 1
            return TallyLineOutcome.REVIEW_REQUIRED_NOT_AVAILABLE

        detail = await self._inventory.get_detail(inventory_item.id)
        ims_label = ""
        if detail:
            ims_label = self._inventory_catalog_label(
                detail.brand.name,
                model_name=detail.product_model.model_name,
                model_number=detail.product_model.model_number,
                part_number=detail.product_model.part_number,
            )
        model_matches = catalog_model_matches_invoice(ims_label, line.stock_item_name)
        review_required = not model_matches
        review_reason = None
        if review_required:
            review_reason = (
                f"Serial matched but invoice model '{line.stock_item_name}' "
                f"differs from IMS model '{ims_label}'. "
                "Inventory updated because serial uniquely identifies the unit."
            )

        # CASE A / B — create sale (serial authoritative)
        old_status = inventory_item.status
        inventory_item.status = InventoryStatus.SOLD
        if mapped_location_id is not None:
            inventory_item.current_location_id = mapped_location_id
        await self._session.flush()

        sold_at = datetime.combine(voucher.voucher_date, time.min, tzinfo=UTC)
        idempotency_key = f"{voucher.guid}:{inventory_item.id}"
        snapshot = SaleProductSnapshot.from_detail(detail) if detail is not None else None
        sale_amount_excluding_gst, sale_amount_inclusive = resolve_line_sale_amounts(line)
        if sale_amount_inclusive is None:
            sale_amount_inclusive = resolve_inventory_line_sale_amount(line, voucher)
        sale = await self._sales.create_tally(
            inventory_item_id=inventory_item.id,
            sold_at=sold_at,
            printed_invoice_number=voucher.printed_invoice_number,
            internal_voucher_number=voucher.voucher_number,
            customer_name=voucher.party_name,
            payment_mode=voucher.payment_mode,
            tally_company_name=company_name,
            tally_voucher_guid=voucher.guid,
            tally_master_id=voucher.master_id,
            tally_voucher_type=voucher.voucher_type,
            mapped_location_id=mapped_location_id,
            notes=voucher.narration,
            idempotency_key=idempotency_key,
            snapshot=snapshot,
            sale_amount=sale_amount_inclusive,
            sale_amount_excluding_gst=sale_amount_excluding_gst,
            review_required=review_required,
            review_reason=review_reason,
            invoice_model_name=line.stock_item_name,
            ims_model_name=ims_label or None,
            serial_source=line.serial_source,
        )

        actor = AuditActor.system(display_name="Tally Sync", role="system")
        await self._recorder.record_inventory_status_change(
            inventory_item,
            old_status=old_status,
            new_status=InventoryStatus.SOLD,
            actor=actor,
            source=AuditSource.TALLY_SYNC,
            extra_new_value={
                "printed_invoice_number": voucher.printed_invoice_number,
                "tally_voucher_number": voucher.voucher_number,
                "sale_id": sale.id,
            },
        )
        await self._recorder.record_system_action(
            entity_type="inventory_item",
            entity_id=str(inventory_item.id),
            description=f"Inventory sold via Tally sync ({voucher.printed_invoice_number})",
            inventory_item_id=inventory_item.id,
            source=AuditSource.TALLY_SYNC,
        )

        outcome = (
            TallyLineOutcome.SALE_APPLIED_WITH_REVIEW
            if review_required
            else TallyLineOutcome.SALE_APPLIED
        )
        await self._processed_lines.complete_line(
            line_row,
            outcome=outcome,
            inventory_item_id=inventory_item.id,
            match_result="serial_exact_match",
            decision="sale_applied_with_review" if review_required else "sale_applied",
            decision_reason=review_reason or "Exact serial match — inventory deducted.",
            ims_model_name=ims_label or None,
            sale_id=sale.id,
            review_required=review_required,
        )
        await self._decision_logs.record(
            invoice_id=invoice_id,
            line_id=line_row.id,
            voucher_guid=voucher.guid,
            line_index=line.line_index,
            serial_source=line.serial_source,
            extracted_serial=extracted,
            normalized_serial=normalized,
            inventory_item_id=inventory_item.id,
            match_result="serial_exact_match",
            decision="sale_applied_with_review" if review_required else "sale_applied",
            reason=review_reason or "Exact serial match.",
        )

        if review_required:
            await self._notifications.create_notification(
                notification_type=NotificationType.PRODUCT_MODEL_MISMATCH,
                severity=NotificationSeverity.INFO,
                title="Sale completed with review required",
                message=review_reason or "Model description differs after serial match.",
                category=NotificationCategory.TALLY_SYNC,
                invoice_number=voucher.printed_invoice_number,
                tally_company_name=company_name,
                tally_voucher_number=voucher.voucher_number,
                voucher_type=voucher.voucher_type,
                customer_name=voucher.party_name,
                serial_number=normalized,
                product_model_number=line.stock_item_name,
                inventory_item_id=inventory_item.id,
            )
            stats["model_mismatches"] += 1
            stats["review_required"] += 1
            counters.model_mismatches += 1

        stats["completed"] += 1
        stats["sales"] += 1
        counters.sales_created += 1
        return outcome

    @staticmethod
    def _parse_line_quantity(raw: str | None) -> int:
        """Leading integer quantity from a Tally qty string (e.g. '5 Nos' -> 5)."""
        if not raw:
            return 1
        digits = ""
        for char in raw.strip():
            if char.isdigit():
                digits += char
            elif char in {".", ","} and digits:
                break  # stop at decimal — whole units only
            elif digits:
                break
        if not digits:
            return 1
        try:
            value = int(digits)
        except ValueError:
            return 1
        return value if value > 0 else 1

    async def _process_shared_ean_sale(
        self,
        *,
        voucher: TallyVoucher,
        line: TallyInventoryLine,
        line_row,
        invoice_id: int,
        company_name: str,
        mapped_location_id: int | None,
        extracted: str | None,
        normalized: str,
        stats: dict[str, int],
        counters: TallySyncCounters,
    ) -> TallyLineOutcome:
        """Deduct a quantity of shared-EAN units (FIFO) for one Tally sales line.

        The invoice line carries the EAN (as the serial) and a billed quantity N.
        We sell up to N AVAILABLE units of the shared pool, oldest first. A
        shortfall (fewer available than billed) completes the sale for what exists
        and flags review — it never blocks or double-sells (each unit uses a
        per-unit idempotency key and the whole voucher runs in one savepoint).
        """
        quantity = self._parse_line_quantity(line.quantity)
        units = await self._inventory.find_available_shared_units_fifo(
            serial_number=normalized,
            limit=quantity,
        )

        # No available units — everything for this EAN is already sold. Block the
        # (probable duplicate) sale and flag for review, mirroring CASE E.
        if not units:
            reason = (
                f"EAN {normalized} has no available units in IMS for the billed "
                f"quantity {quantity} — review required (no inventory change)."
            )
            await self._processed_lines.complete_line(
                line_row,
                outcome=TallyLineOutcome.REVIEW_REQUIRED_ALREADY_SOLD,
                match_result="ean_pool_exhausted",
                decision="review_required",
                decision_reason=reason,
                review_required=True,
            )
            await self._decision_logs.record(
                invoice_id=invoice_id,
                line_id=line_row.id,
                voucher_guid=voucher.guid,
                line_index=line.line_index,
                serial_source=line.serial_source,
                extracted_serial=extracted,
                normalized_serial=normalized,
                inventory_item_id=None,
                match_result="ean_pool_exhausted",
                decision="review_required",
                reason=reason,
            )
            await self._notifications.create_notification(
                notification_type=NotificationType.DUPLICATE_SALE,
                severity=NotificationSeverity.WARNING,
                title="EAN pool exhausted",
                message=reason,
                category=NotificationCategory.TALLY_SYNC,
                invoice_number=voucher.printed_invoice_number,
                tally_company_name=company_name,
                tally_voucher_number=voucher.voucher_number,
                voucher_type=voucher.voucher_type,
                customer_name=voucher.party_name,
                serial_number=normalized,
                product_model_number=line.stock_item_name,
            )
            stats["completed"] += 1
            stats["review_required"] += 1
            return TallyLineOutcome.REVIEW_REQUIRED_ALREADY_SOLD

        shortfall = quantity - len(units)

        # Verify the invoice model against the resolved pool model once (all units
        # share a model). Mismatch still sells but flags review, like CASE B.
        first_detail = await self._inventory.get_detail(units[0].id)
        ims_label = ""
        if first_detail:
            ims_label = self._inventory_catalog_label(
                first_detail.brand.name,
                model_name=first_detail.product_model.model_name,
                model_number=first_detail.product_model.model_number,
                part_number=first_detail.product_model.part_number,
            )
        model_mismatch = bool(ims_label) and not catalog_model_matches_invoice(
            ims_label, line.stock_item_name
        )
        review_required = model_mismatch or shortfall > 0

        # Per-unit sale amounts = line total split across the BILLED quantity.
        sale_amount_excluding_gst, sale_amount_inclusive = resolve_line_sale_amounts(line)
        if sale_amount_inclusive is None:
            sale_amount_inclusive = resolve_inventory_line_sale_amount(line, voucher)
        divisor = quantity if quantity > 0 else 1
        per_unit_incl = self._split_amount(sale_amount_inclusive, divisor)
        per_unit_excl = self._split_amount(sale_amount_excluding_gst, divisor)

        sold_at = datetime.combine(voucher.voucher_date, time.min, tzinfo=UTC)
        actor = AuditActor.system(display_name="Tally Sync", role="system")
        sold_ids: list[uuid.UUID] = []
        last_sale_id: int | None = None

        for unit in units:
            detail = await self._inventory.get_detail(unit.id)
            old_status = unit.status
            unit.status = InventoryStatus.SOLD
            if mapped_location_id is not None:
                unit.current_location_id = mapped_location_id
            await self._session.flush()

            snapshot = SaleProductSnapshot.from_detail(detail) if detail is not None else None
            sale = await self._sales.create_tally(
                inventory_item_id=unit.id,
                sold_at=sold_at,
                printed_invoice_number=voucher.printed_invoice_number,
                internal_voucher_number=voucher.voucher_number,
                customer_name=voucher.party_name,
                payment_mode=voucher.payment_mode,
                tally_company_name=company_name,
                tally_voucher_guid=voucher.guid,
                tally_master_id=voucher.master_id,
                tally_voucher_type=voucher.voucher_type,
                mapped_location_id=mapped_location_id,
                notes=voucher.narration,
                idempotency_key=f"{voucher.guid}:{unit.id}",
                snapshot=snapshot,
                sale_amount=per_unit_incl,
                sale_amount_excluding_gst=per_unit_excl,
                review_required=review_required,
                review_reason=None,
                invoice_model_name=line.stock_item_name,
                ims_model_name=ims_label or None,
                serial_source=line.serial_source,
            )
            last_sale_id = sale.id
            sold_ids.append(unit.id)
            await self._recorder.record_inventory_status_change(
                unit,
                old_status=old_status,
                new_status=InventoryStatus.SOLD,
                actor=actor,
                source=AuditSource.TALLY_SYNC,
                extra_new_value={
                    "printed_invoice_number": voucher.printed_invoice_number,
                    "tally_voucher_number": voucher.voucher_number,
                    "sale_id": sale.id,
                    "ean_pool": True,
                },
            )
            await self._recorder.record_system_action(
                entity_type="inventory_item",
                entity_id=str(unit.id),
                description=(f"EAN unit sold via Tally sync ({voucher.printed_invoice_number})"),
                inventory_item_id=unit.id,
                source=AuditSource.TALLY_SYNC,
            )

        reason_parts = [f"EAN {normalized}: sold {len(units)} unit(s) FIFO."]
        if shortfall > 0:
            reason_parts.append(
                f"Billed {quantity} but only {len(units)} available — "
                f"{shortfall} unit(s) short; review required."
            )
        if model_mismatch:
            reason_parts.append(
                f"Invoice model '{line.stock_item_name}' differs from IMS model " f"'{ims_label}'."
            )
        decision_reason = " ".join(reason_parts)
        outcome = (
            TallyLineOutcome.SALE_APPLIED_WITH_REVIEW
            if review_required
            else TallyLineOutcome.SALE_APPLIED
        )
        await self._processed_lines.complete_line(
            line_row,
            outcome=outcome,
            inventory_item_id=sold_ids[0],
            match_result="ean_pool_match",
            decision="sale_applied_with_review" if review_required else "sale_applied",
            decision_reason=decision_reason,
            ims_model_name=ims_label or None,
            sale_id=last_sale_id,
            review_required=review_required,
        )
        await self._decision_logs.record(
            invoice_id=invoice_id,
            line_id=line_row.id,
            voucher_guid=voucher.guid,
            line_index=line.line_index,
            serial_source=line.serial_source,
            extracted_serial=extracted,
            normalized_serial=normalized,
            inventory_item_id=sold_ids[0],
            match_result="ean_pool_match",
            decision="sale_applied_with_review" if review_required else "sale_applied",
            reason=decision_reason,
        )
        if review_required:
            await self._notifications.create_notification(
                notification_type=NotificationType.PRODUCT_MODEL_MISMATCH,
                severity=NotificationSeverity.INFO,
                title="EAN sale completed with review required",
                message=decision_reason,
                category=NotificationCategory.TALLY_SYNC,
                invoice_number=voucher.printed_invoice_number,
                tally_company_name=company_name,
                tally_voucher_number=voucher.voucher_number,
                voucher_type=voucher.voucher_type,
                customer_name=voucher.party_name,
                serial_number=normalized,
                product_model_number=line.stock_item_name,
                inventory_item_id=sold_ids[0],
            )
            stats["review_required"] += 1

        stats["completed"] += 1
        stats["sales"] += len(units)
        counters.sales_created += len(units)
        return outcome

    @staticmethod
    def _split_amount(total: Decimal | float | None, divisor: int) -> Decimal | None:
        if total is None or divisor <= 0:
            return None if total is None else Decimal(str(total))
        return (Decimal(str(total)) / Decimal(divisor)).quantize(Decimal("0.01"))

    async def _complete_additional_product(
        self,
        *,
        voucher: TallyVoucher,
        line: TallyInventoryLine,
        line_row,
        invoice_id: int,
        reason: str,
        inventory_item_id: uuid.UUID | None = None,
    ) -> None:
        await self._processed_lines.complete_line(
            line_row,
            outcome=TallyLineOutcome.ADDITIONAL_PRODUCT,
            inventory_item_id=inventory_item_id,
            match_result="additional_product",
            decision="store_additional_product",
            decision_reason=reason,
            is_additional_product=True,
            is_unmatched_serialized=False,
            review_required=False,
        )
        await self._decision_logs.record(
            invoice_id=invoice_id,
            line_id=line_row.id,
            voucher_guid=voucher.guid,
            line_index=line.line_index,
            serial_source=line.serial_source,
            extracted_serial=line.serial_number,
            normalized_serial=line.normalized_serial,
            inventory_item_id=inventory_item_id,
            match_result="additional_product",
            decision="store_additional_product",
            reason=reason,
        )

    async def _complete_unmatched_serialized_item(
        self,
        *,
        voucher: TallyVoucher,
        line: TallyInventoryLine,
        line_row,
        invoice_id: int,
        reason: str,
    ) -> None:
        """Case C2 — serial present but not managed in IMS (visible, no inventory change)."""
        await self._processed_lines.complete_line(
            line_row,
            outcome=TallyLineOutcome.UNMATCHED_SERIALIZED_ITEM,
            match_result="unmatched_serialized_item",
            decision="store_unmatched_serialized",
            decision_reason=reason,
            is_additional_product=False,
            is_unmatched_serialized=True,
            review_required=False,
        )
        await self._decision_logs.record(
            invoice_id=invoice_id,
            line_id=line_row.id,
            voucher_guid=voucher.guid,
            line_index=line.line_index,
            serial_source=line.serial_source,
            extracted_serial=line.serial_number,
            normalized_serial=line.normalized_serial,
            inventory_item_id=None,
            match_result="unmatched_serialized_item",
            decision="store_unmatched_serialized",
            reason=reason,
        )

    @staticmethod
    def _inventory_catalog_label(
        brand_name: str,
        *,
        model_name: str,
        model_number: str,
        part_number: str | None = None,
    ) -> str:
        label = f"{brand_name} {model_name} {model_number}"
        if part_number:
            label = f"{label} {part_number}"
        return label

    @staticmethod
    def _purchase_decimal(value: str | Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (ValueError, ArithmeticError):
            return None

    async def _project_purchase_queue(
        self,
        vouchers: list[TallyVoucher],
        company_sync: TallyCompanySync,
    ) -> None:
        """Project Purchase vouchers into the Purchase Import Queue (idempotent by GUID).

        This creates NO inventory and NEVER raises into the sales pipeline. Each
        voucher is upserted inside its own SAVEPOINT so a single bad voucher cannot
        poison the rest of the sync transaction.
        """
        purchase_vouchers = [
            voucher for voucher in vouchers if voucher.voucher_type in PURCHASE_VOUCHER_TYPES
        ]
        if not purchase_vouchers:
            return
        for voucher in purchase_vouchers:
            try:
                async with self._session.begin_nested():
                    await self._upsert_purchase_voucher(voucher, company_sync)
            except Exception as exc:  # noqa: BLE001 — never break sales sync
                logger.warning(
                    "Purchase queue projection skipped voucher {}: {}", voucher.guid, exc
                )

    async def _upsert_purchase_voucher(
        self,
        voucher: TallyVoucher,
        company_sync: TallyCompanySync,
    ) -> None:
        now = datetime.now(UTC)
        existing = await self._purchase.get_voucher_by_guid(company_sync.id, voucher.guid)
        if existing is not None:
            existing.last_seen_at = now
            if existing.raw_xml_gzip is None and voucher.raw_xml:
                existing.raw_xml_gzip = gzip.compress(voucher.raw_xml.encode("utf-8"))
            await self._session.flush()
            return

        totals = voucher.totals
        reference_number = None
        if voucher.printed_invoice_number and (
            voucher.printed_invoice_number != voucher.voucher_number
        ):
            reference_number = voucher.printed_invoice_number

        header = TallyPurchaseVoucher(
            tally_company_sync_id=company_sync.id,
            tally_voucher_guid=voucher.guid,
            tally_master_id=voucher.master_id,
            tally_voucher_number=voucher.voucher_number,
            printed_invoice_number=voucher.printed_invoice_number,
            reference_number=reference_number,
            voucher_type=voucher.voucher_type,
            voucher_date=voucher.voucher_date,
            supplier_name=voucher.party_name,
            subtotal=totals.subtotal,
            discount_amount=totals.discount_amount,
            round_off=totals.round_off,
            cgst_amount=totals.cgst_amount,
            sgst_amount=totals.sgst_amount,
            igst_amount=totals.igst_amount,
            cess_amount=totals.cess_amount,
            grand_total=totals.grand_total or (self._purchase_decimal(voucher.amount)),
            narration=voucher.narration,
            raw_xml_gzip=(
                gzip.compress(voucher.raw_xml.encode("utf-8")) if voucher.raw_xml else None
            ),
            status=TallyPurchaseStatus.PENDING,
            first_seen_at=now,
            last_seen_at=now,
        )
        for idx, line in enumerate(voucher.inventory_lines):
            serials = list(line.batch_allocations)
            if not serials and line.serial_number:
                serials = [line.serial_number]
            header.lines.append(
                TallyPurchaseLine(
                    line_index=idx,
                    stock_item_name=line.stock_item_name or "",
                    group_key=_collapse(line.stock_item_name or ""),
                    quantity=line.quantity,
                    serials_json=json.dumps(serials),
                    serial_source=line.serial_source,
                    rate=self._purchase_decimal(line.rate),
                    amount=self._purchase_decimal(line.amount),
                    taxable_amount=self._purchase_decimal(line.taxable_amount),
                    cgst_amount=self._purchase_decimal(line.cgst_amount),
                    sgst_amount=self._purchase_decimal(line.sgst_amount),
                    igst_amount=self._purchase_decimal(line.igst_amount),
                    cess_amount=self._purchase_decimal(line.cess_amount),
                    line_total=self._purchase_decimal(line.line_total or line.amount),
                )
            )
        await self._purchase.add_voucher(header)

    async def _resolve_store_location(self, voucher_type: str):
        store_name = VOUCHER_TYPE_STORE_MAP.get(voucher_type)
        if not store_name:
            return None
        return await self._locations.get_by_name(store_name)

    def _derive_voucher_status(self, line_stats: dict[str, int]) -> TallyProcessingStatus:
        """
        Invoice-level status:
          Failed | Processed With Warnings | Processed
        (Skipped is set by GUID idempotency before processing.)
        """
        if line_stats["failed"] > 0 and line_stats["completed"] == 0:
            return TallyProcessingStatus.FAILED
        if line_stats["failed"] > 0:
            return TallyProcessingStatus.PARTIAL_SUCCESS
        if line_stats["review_required"] > 0:
            return TallyProcessingStatus.COMPLETED_WITH_REVIEW_REQUIRED
        if line_stats["completed"] > 0:
            return TallyProcessingStatus.SUCCESS
        return TallyProcessingStatus.FAILED

    async def process_voucher_xml(
        self,
        xml_text: str,
        *,
        correlation_id: str,
        company_name: str | None = None,
    ) -> TallySyncResult:
        """Process vouchers from XML text (used in tests and manual imports)."""
        configured_company = (await self.get_connection_config())[2]
        resolved_company = company_name or configured_company
        company_sync = await self._company_sync.get_or_create(resolved_company)
        sync_run_id = uuid.uuid4()
        counters = TallySyncCounters()
        vouchers = parse_vouchers_xml(xml_text)
        started_at = datetime.now(UTC)
        last_imported_guid = company_sync.last_processed_guid
        last_imported_voucher_date = company_sync.last_imported_voucher_date
        last_processed_master_id = company_sync.last_processed_master_id
        last_processed_invoice_number = company_sync.last_processed_invoice_number
        last_processed_voucher_type = company_sync.last_processed_voucher_type
        vouchers.sort(key=lambda voucher: (voucher.voucher_date, voucher.guid))
        monitored = [
            voucher for voucher in vouchers if voucher.voucher_type in MONITORED_VOUCHER_TYPES
        ]
        watermark = partition_by_guid_watermark(monitored, last_imported_guid)
        if watermark.historical_skipped:
            counters.invoices_checked += watermark.historical_skipped
            counters.invoices_skipped += watermark.historical_skipped
            counters.watermark_skipped += watermark.historical_skipped
        for voucher in watermark.to_process:
            counters.invoices_checked += 1
            if await self._should_skip_voucher(company_sync.id, voucher):
                counters.invoices_skipped += 1
                continue
            invoice, created = await self._processed_invoices.get_or_create_pending(
                company_sync_id=company_sync.id,
                guid=voucher.guid,
                master_id=voucher.master_id,
                voucher_number=voucher.voucher_number,
                printed_invoice_number=voucher.printed_invoice_number,
                voucher_type=voucher.voucher_type,
                voucher_date=voucher.voucher_date,
                party_name=voucher.party_name,
                amount=voucher.amount,
            )
            if not created and invoice.processing_status in {
                TallyProcessingStatus.SUCCESS,
                TallyProcessingStatus.COMPLETED_WITH_REVIEW_REQUIRED,
            }:
                counters.invoices_skipped += 1
                continue
            counters.vouchers_processed += 1
            if created:
                counters.invoices_imported += 1
            try:
                line_stats = await self._process_voucher(
                    voucher=voucher,
                    company_sync=company_sync,
                    invoice_id=invoice.id,
                    company_name=resolved_company,
                    sync_run_id=sync_run_id,
                    correlation_id=correlation_id,
                    counters=counters,
                )
                status = self._derive_voucher_status(line_stats)
                await self._processed_invoices.update_status(invoice, status)
            except Exception as exc:  # noqa: BLE001
                counters.failures += 1
                # Re-load invoice after rollback
                company_sync = await self._company_sync.get_or_create(resolved_company)
                invoice, _ = await self._processed_invoices.get_or_create_pending(
                    company_sync_id=company_sync.id,
                    guid=voucher.guid,
                    master_id=voucher.master_id,
                    voucher_number=voucher.voucher_number,
                    printed_invoice_number=voucher.printed_invoice_number,
                    voucher_type=voucher.voucher_type,
                    voucher_date=voucher.voucher_date,
                    party_name=voucher.party_name,
                    amount=voucher.amount,
                )
                await self._processed_invoices.update_status(invoice, TallyProcessingStatus.FAILED)
                del exc
            last_imported_guid = voucher.guid
            last_processed_master_id = voucher.master_id
            last_processed_invoice_number = voucher.printed_invoice_number or voucher.voucher_number
            last_processed_voucher_type = voucher.voucher_type
            if (
                last_imported_voucher_date is None
                or voucher.voucher_date >= last_imported_voucher_date
            ):
                last_imported_voucher_date = voucher.voucher_date

        await self._project_purchase_queue(vouchers, company_sync)

        now = datetime.now(UTC)
        duration_ms = int((now - started_at).total_seconds() * 1000)
        run_success = counters.failures == 0
        had_meaningful_progress = tally_sync_had_meaningful_progress(
            invoices_imported=counters.invoices_imported,
            sales_created=counters.sales_created,
        )
        await self._finalize_company_sync_state(
            company_sync=company_sync,
            counters=counters,
            run_success=run_success,
            had_meaningful_progress=had_meaningful_progress,
            finished_at=now,
            duration_ms=duration_ms,
            last_imported_guid=last_imported_guid,
            last_imported_voucher_date=last_imported_voucher_date,
            last_processed_master_id=last_processed_master_id,
            last_processed_invoice_number=last_processed_invoice_number,
            last_processed_voucher_type=last_processed_voucher_type,
        )
        return TallySyncResult(
            sync_run_id=str(sync_run_id),
            success=run_success,
            message=("XML processed." if run_success else "XML processed with issues."),
            counters=counters,
            connection_status="connected",
        )
