"""Production Tally ERP 9 synchronization service."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import func, select
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
    TallySyncRunStatus,
)
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.models.tally_company_sync import TallyCompanySync
from webstudio_backend.infrastructure.repositories.inventory_item_repository import InventoryItemRepository
from webstudio_backend.infrastructure.repositories.location_repository import LocationRepository
from webstudio_backend.infrastructure.repositories.notification_repository import NotificationRepository
from webstudio_backend.infrastructure.repositories.product_model_repository import ProductModelRepository
from webstudio_backend.infrastructure.repositories.sale_repository import SaleRepository
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import TallyCompanySyncRepository
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_line_repository import (
    TallyProcessedInvoiceLineRepository,
)
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_repository import (
    TallyProcessedInvoiceRepository,
)
from webstudio_backend.infrastructure.repositories.tally_sync_log_repository import TallySyncLogRepository
from webstudio_backend.integrations.tally.constants import MONITORED_VOUCHER_TYPES, VOUCHER_TYPE_STORE_MAP
from webstudio_backend.integrations.tally.types import TallyInventoryLine, TallyVoucher
from webstudio_backend.integrations.tally.xml_client import TallyConnectionError, TallyXmlClient
from webstudio_backend.integrations.tally.xml_parser import models_equivalent, parse_vouchers_xml
from webstudio_backend.services.notification_service import NotificationService

_sync_lock = asyncio.Lock()


@dataclass(slots=True)
class TallySyncCounters:
    vouchers_processed: int = 0
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
        self._sync_logs = TallySyncLogRepository(session)
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
        interval = await self._get_int("tally_sync_interval_seconds", 1800)
        return host, port, company, interval

    async def test_connection(self) -> bool:
        host, port, _, _ = await self.get_connection_config()
        client = TallyXmlClient(host, port)
        return await client.test_connection()

    async def run_sync(self, *, correlation_id: str, triggered_by_user_id: int | None = None) -> TallySyncResult:
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

        if not await self.is_enabled():
            return TallySyncResult(
                sync_run_id=str(sync_run_id),
                success=False,
                message="Tally integration is disabled.",
            )

        host, port, company_name, _ = await self.get_connection_config()
        company_sync = await self._company_sync.get_or_create(company_name)
        client = TallyXmlClient(host, port)

        await self._notifications.create_notification(
            notification_type=NotificationType.TALLY_SYNC_STARTED,
            severity=NotificationSeverity.INFO,
            title="Tally synchronization started",
            message=f"Synchronization run {sync_run_id} started for {company_name}.",
            category=NotificationCategory.TALLY_SYNC,
            tally_company_name=company_name,
        )
        await self._recorder.record_system_action(
            entity_type="tally_sync",
            entity_id=str(sync_run_id),
            description="Tally sync started",
            source=AuditSource.TALLY_SYNC,
        )

        try:
            connected = await client.test_connection()
        except TallyConnectionError as exc:
            await self._company_sync.update_sync_state(
                company_sync,
                connection_status="error",
                last_error=str(exc),
            )
            await self._notify_connection_lost(company_name, str(exc))
            return TallySyncResult(
                sync_run_id=str(sync_run_id),
                success=False,
                message=str(exc),
                counters=counters,
                connection_status="error",
                last_error=str(exc),
            )

        if not connected:
            message = "Unable to reach Tally ERP 9."
            await self._company_sync.update_sync_state(
                company_sync,
                connection_status="disconnected",
                last_error=message,
            )
            await self._notify_connection_lost(company_name, message)
            return TallySyncResult(
                sync_run_id=str(sync_run_id),
                success=False,
                message=message,
                counters=counters,
                connection_status="disconnected",
                last_error=message,
            )

        previous_status = company_sync.connection_status
        await self._company_sync.update_sync_state(company_sync, connection_status="connected", last_error="")
        if previous_status in {"disconnected", "error"}:
            await self._notifications.create_notification(
                notification_type=NotificationType.CONNECTION_RESTORED,
                severity=NotificationSeverity.INFO,
                title="Tally connection restored",
                message=f"Connection to Tally ERP 9 at {host}:{port} is healthy.",
                category=NotificationCategory.TALLY_SYNC,
                tally_company_name=company_name,
            )

        from_date = (
            company_sync.last_successful_sync_at.date()
            if company_sync.last_successful_sync_at
            else datetime.now(UTC).date() - timedelta(days=30)
        )

        all_vouchers: list[TallyVoucher] = []
        try:
            exports = await client.export_monitored_voucher_types(
                company_name=company_name,
                from_date=from_date,
            )
            for voucher_type, xml_text in exports.items():
                parsed = parse_vouchers_xml(xml_text)
                all_vouchers.extend(parsed)
        except TallyConnectionError as exc:
            await self._company_sync.update_sync_state(
                company_sync,
                connection_status="error",
                last_error=str(exc),
            )
            counters.failures += 1
            await self._finalize_run(
                sync_run_id=sync_run_id,
                company_sync=company_sync,
                correlation_id=correlation_id,
                counters=counters,
                success=False,
                message=str(exc),
            )
            return TallySyncResult(
                sync_run_id=str(sync_run_id),
                success=False,
                message=str(exc),
                counters=counters,
                connection_status="error",
                last_error=str(exc),
            )

        all_vouchers.sort(key=lambda voucher: (voucher.voucher_date, voucher.guid))
        last_guid: str | None = company_sync.last_processed_guid

        for voucher in all_vouchers:
            if voucher.voucher_type not in MONITORED_VOUCHER_TYPES:
                continue
            if last_guid and voucher.guid == last_guid:
                continue

            invoice, created = await self._processed_invoices.get_or_create_pending(
                company_sync_id=company_sync.id,
                guid=voucher.guid,
                master_id=voucher.master_id,
                voucher_number=voucher.voucher_number,
                printed_invoice_number=voucher.printed_invoice_number,
                voucher_type=voucher.voucher_type,
            )
            if not created and invoice.processing_status is TallyProcessingStatus.SUCCESS:
                counters.skipped_vouchers += 1
                await self._sync_logs.create_run_log(
                    sync_run_id=sync_run_id,
                    company_sync_id=company_sync.id,
                    correlation_id=correlation_id,
                    voucher_guid=voucher.guid,
                    voucher_number=voucher.voucher_number,
                    printed_invoice_number=voucher.printed_invoice_number,
                    voucher_type=voucher.voucher_type,
                    customer_name=voucher.party_name,
                    processed_invoice_id=invoice.id,
                    status=TallySyncRunStatus.SKIPPED,
                )
                continue

            counters.vouchers_processed += 1
            line_stats = await self._process_voucher(
                voucher=voucher,
                company_sync=company_sync,
                invoice_id=invoice.id,
                company_name=company_name,
                sync_run_id=sync_run_id,
                correlation_id=correlation_id,
                counters=counters,
            )

            if line_stats["failed"] == 0 and line_stats["completed"] > 0:
                await self._processed_invoices.update_status(invoice, TallyProcessingStatus.SUCCESS)
                run_status = TallySyncRunStatus.SUCCESS
            elif line_stats["completed"] > 0:
                await self._processed_invoices.update_status(invoice, TallyProcessingStatus.PARTIAL_SUCCESS)
                run_status = TallySyncRunStatus.PARTIAL_SUCCESS
            else:
                await self._processed_invoices.update_status(invoice, TallyProcessingStatus.FAILED)
                run_status = TallySyncRunStatus.FAILED
                counters.failures += 1

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

            last_guid = voucher.guid
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

        now = datetime.now(UTC)
        await self._company_sync.update_sync_state(
            company_sync,
            last_successful_sync_at=now,
            last_processed_guid=last_guid,
            last_processed_master_id=all_vouchers[-1].master_id if all_vouchers else company_sync.last_processed_master_id,
            connection_status="connected",
            last_error="",
        )

        await self._finalize_run(
            sync_run_id=sync_run_id,
            company_sync=company_sync,
            correlation_id=correlation_id,
            counters=counters,
            success=True,
            message="Synchronization completed.",
        )

        return TallySyncResult(
            sync_run_id=str(sync_run_id),
            success=True,
            message="Synchronization completed.",
            counters=counters,
            connection_status="connected",
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
        }
        mapped_location = await self._resolve_store_location(voucher.voucher_type)

        for line in voucher.inventory_lines:
            stats["total"] += 1
            counters.inventory_entries_processed += 1
            line_row = await self._processed_lines.get_or_create_line(
                invoice_id=invoice_id,
                line_index=line.line_index,
                serial_number=line.serial_number,
                stock_item_name=line.stock_item_name,
            )
            if line_row.line_status.value == "completed":
                stats["completed"] += 1
                continue

            try:
                outcome = await self._process_inventory_line(
                    voucher=voucher,
                    line=line,
                    company_name=company_name,
                    mapped_location_id=mapped_location.id if mapped_location else None,
                )
            except Exception as exc:  # noqa: BLE001 — line isolation
                await self._processed_lines.fail_line(
                    line_row,
                    outcome=TallyLineOutcome.ERROR,
                    error_message=str(exc),
                )
                stats["failed"] += 1
                counters.failures += 1
                continue

            if outcome == TallyLineOutcome.SALE_APPLIED:
                await self._processed_lines.complete_line(line_row, outcome=outcome)
                stats["completed"] += 1
                stats["sales"] += 1
                counters.sales_created += 1
            elif outcome == TallyLineOutcome.DUPLICATE_SALE:
                await self._processed_lines.complete_line(line_row, outcome=outcome)
                stats["completed"] += 1
                stats["duplicates"] += 1
                counters.duplicates += 1
            elif outcome == TallyLineOutcome.SERIAL_NUMBER_MISSING:
                await self._processed_lines.fail_line(line_row, outcome=outcome)
                stats["failed"] += 1
                stats["missing_serial"] += 1
                counters.missing_serials += 1
            elif outcome == TallyLineOutcome.PRODUCT_MODEL_MISSING:
                await self._processed_lines.fail_line(line_row, outcome=outcome)
                stats["failed"] += 1
                stats["missing_model"] += 1
                counters.missing_models += 1
            elif outcome == TallyLineOutcome.PRODUCT_MODEL_MISMATCH:
                await self._processed_lines.complete_line(line_row, outcome=outcome)
                stats["completed"] += 1
                stats["model_mismatches"] += 1
                counters.model_mismatches += 1
            else:
                await self._processed_lines.complete_line(line_row, outcome=outcome)
                stats["completed"] += 1
                stats["ignored"] += 1

        return stats

    async def _process_inventory_line(
        self,
        *,
        voucher: TallyVoucher,
        line: TallyInventoryLine,
        company_name: str,
        mapped_location_id: int | None,
    ) -> TallyLineOutcome:
        inventory_item: InventoryItem | None = None
        model_mismatch = False

        if line.serial_number:
            inventory_item = await self._inventory.find_by_serial_number(line.serial_number)
            if inventory_item is None:
                await self._notifications.create_notification(
                    notification_type=NotificationType.SERIAL_NUMBER_MISSING,
                    severity=NotificationSeverity.WARNING,
                    title="Missing serial number",
                    message=(
                        f"Serial {line.serial_number} from invoice {voucher.printed_invoice_number} "
                        "was not found in inventory."
                    ),
                    category=NotificationCategory.TALLY_SYNC,
                    invoice_number=voucher.printed_invoice_number,
                    tally_company_name=company_name,
                    tally_voucher_number=voucher.voucher_number,
                    voucher_type=voucher.voucher_type,
                    customer_name=voucher.party_name,
                    serial_number=line.serial_number,
                    product_model_number=line.stock_item_name,
                )
                return TallyLineOutcome.SERIAL_NUMBER_MISSING

            if inventory_item.status is InventoryStatus.SOLD:
                await self._notifications.create_duplicate_sale_notification(
                    title="Duplicate sale detected",
                    message=(
                        f"Invoice {voucher.printed_invoice_number} references serial {line.serial_number} "
                        "which is already sold."
                    ),
                    invoice_number=voucher.printed_invoice_number,
                    serial_number=line.serial_number,
                    tally_company_name=company_name,
                    tally_voucher_number=voucher.voucher_number,
                    voucher_type=voucher.voucher_type,
                    customer_name=voucher.party_name,
                    product_model_number=line.stock_item_name,
                    inventory_item_id=inventory_item.id,
                )
                return TallyLineOutcome.DUPLICATE_SALE

            if inventory_item.status is not InventoryStatus.AVAILABLE:
                return TallyLineOutcome.IGNORED

            detail = await self._inventory.get_detail(inventory_item.id)
            if detail and not models_equivalent(
                f"{detail.brand.name} {detail.product_model.model_name} {detail.product_model.model_number}",
                line.stock_item_name,
            ):
                model_mismatch = True
        else:
            inventory_item = await self._match_inventory_by_model(line.stock_item_name)
            if inventory_item is None:
                await self._notifications.create_notification(
                    notification_type=NotificationType.PRODUCT_MODEL_MISSING,
                    severity=NotificationSeverity.WARNING,
                    title="Product model not matched",
                    message=(
                        f"Could not match product '{line.stock_item_name}' from invoice "
                        f"{voucher.printed_invoice_number}."
                    ),
                    category=NotificationCategory.TALLY_SYNC,
                    invoice_number=voucher.printed_invoice_number,
                    tally_company_name=company_name,
                    tally_voucher_number=voucher.voucher_number,
                    voucher_type=voucher.voucher_type,
                    customer_name=voucher.party_name,
                    product_model_number=line.stock_item_name,
                )
                return TallyLineOutcome.PRODUCT_MODEL_MISSING

        assert inventory_item is not None
        old_status = inventory_item.status
        inventory_item.status = InventoryStatus.SOLD
        if mapped_location_id is not None:
            inventory_item.current_location_id = mapped_location_id
        await self._session.flush()

        sold_at = datetime.combine(voucher.voucher_date, time.min, tzinfo=UTC)
        idempotency_key = f"{voucher.guid}:{inventory_item.id}"
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

        if model_mismatch:
            detail = await self._inventory.get_detail(inventory_item.id)
            inventory_model = (
                f"{detail.brand.name} {detail.product_model.model_name}"
                if detail
                else "Unknown"
            )
            await self._notifications.create_notification(
                notification_type=NotificationType.PRODUCT_MODEL_MISMATCH,
                severity=NotificationSeverity.INFO,
                title="Product model mismatch",
                message=(
                    f"Serial {line.serial_number} was sold from invoice {voucher.printed_invoice_number}, "
                    f"but invoice model '{line.stock_item_name}' differs from inventory model '{inventory_model}'."
                ),
                category=NotificationCategory.TALLY_SYNC,
                invoice_number=voucher.printed_invoice_number,
                tally_company_name=company_name,
                tally_voucher_number=voucher.voucher_number,
                voucher_type=voucher.voucher_type,
                customer_name=voucher.party_name,
                serial_number=line.serial_number,
                product_model_number=line.stock_item_name,
                inventory_item_id=inventory_item.id,
            )
            return TallyLineOutcome.PRODUCT_MODEL_MISMATCH

        return TallyLineOutcome.SALE_APPLIED

    async def _match_inventory_by_model(self, stock_item_name: str) -> InventoryItem | None:
        statement = (
            select(InventoryItem)
            .join(ProductModel, InventoryItem.product_model_id == ProductModel.id)
            .where(InventoryItem.status == InventoryStatus.AVAILABLE)
            .where(InventoryItem.is_archived.is_(False))
        )
        result = await self._session.execute(statement)
        candidates = list(result.scalars().all())
        matches: list[InventoryItem] = []
        for item in candidates:
            detail = await self._inventory.get_detail(item.id)
            if not detail:
                continue
            inventory_label = (
                f"{detail.brand.name} {detail.product_model.model_name} {detail.product_model.model_number}"
            )
            if models_equivalent(inventory_label, stock_item_name):
                matches.append(item)
        if len(matches) == 1:
            return matches[0]
        return None

    async def _resolve_store_location(self, voucher_type: str):
        store_name = VOUCHER_TYPE_STORE_MAP.get(voucher_type)
        if not store_name:
            return None
        return await self._locations.get_by_name(store_name)

    async def _notify_connection_lost(self, company_name: str, message: str) -> None:
        await self._notifications.create_notification(
            notification_type=NotificationType.CONNECTION_LOST,
            severity=NotificationSeverity.ERROR,
            title="Tally connection lost",
            message=message,
            category=NotificationCategory.TALLY_SYNC,
            tally_company_name=company_name,
        )
        await self._notifications.create_notification(
            notification_type=NotificationType.SYNC_FAILURE,
            severity=NotificationSeverity.ERROR,
            title="Tally synchronization failed",
            message=message,
            category=NotificationCategory.TALLY_SYNC,
            tally_company_name=company_name,
        )

    async def _finalize_run(
        self,
        *,
        sync_run_id: uuid.UUID,
        company_sync: TallyCompanySync,
        correlation_id: str,
        counters: TallySyncCounters,
        success: bool,
        message: str,
    ) -> None:
        await self._notifications.create_notification(
            notification_type=NotificationType.TALLY_SYNC_COMPLETED,
            severity=NotificationSeverity.INFO if success else NotificationSeverity.WARNING,
            title="Tally synchronization completed" if success else "Tally synchronization finished with issues",
            message=(
                f"{message} Vouchers: {counters.vouchers_processed}, "
                f"sales: {counters.sales_created}, duplicates: {counters.duplicates}, "
                f"missing serials: {counters.missing_serials}, mismatches: {counters.model_mismatches}."
            ),
            category=NotificationCategory.TALLY_SYNC,
            tally_company_name=company_sync.company_name,
        )
        await self._recorder.record_system_action(
            entity_type="tally_sync",
            entity_id=str(sync_run_id),
            description="Tally sync completed" if success else "Tally sync completed with issues",
            source=AuditSource.TALLY_SYNC,
            new_value={
                "vouchers_processed": counters.vouchers_processed,
                "sales_created": counters.sales_created,
                "duplicates": counters.duplicates,
                "missing_serials": counters.missing_serials,
                "model_mismatches": counters.model_mismatches,
                "failures": counters.failures,
            },
        )

    async def process_voucher_xml(
        self,
        xml_text: str,
        *,
        correlation_id: str,
        company_name: str | None = None,
    ) -> TallySyncResult:
        """Process vouchers from XML text (used in tests and manual imports)."""
        host, port, configured_company, _ = await self.get_connection_config()
        resolved_company = company_name or configured_company
        company_sync = await self._company_sync.get_or_create(resolved_company)
        sync_run_id = uuid.uuid4()
        counters = TallySyncCounters()
        vouchers = parse_vouchers_xml(xml_text)
        for voucher in vouchers:
            if voucher.voucher_type not in MONITORED_VOUCHER_TYPES:
                continue
            invoice, _ = await self._processed_invoices.get_or_create_pending(
                company_sync_id=company_sync.id,
                guid=voucher.guid,
                master_id=voucher.master_id,
                voucher_number=voucher.voucher_number,
                printed_invoice_number=voucher.printed_invoice_number,
                voucher_type=voucher.voucher_type,
            )
            counters.vouchers_processed += 1
            await self._process_voucher(
                voucher=voucher,
                company_sync=company_sync,
                invoice_id=invoice.id,
                company_name=resolved_company,
                sync_run_id=sync_run_id,
                correlation_id=correlation_id,
                counters=counters,
            )
        return TallySyncResult(
            sync_run_id=str(sync_run_id),
            success=True,
            message="XML processed.",
            counters=counters,
            connection_status="connected",
        )
