"""Report business logic."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, PageResult
from webstudio_backend.infrastructure.repositories.report_filters import (
    ExportFormat,
    ReportFilters,
    ReportType,
)
from webstudio_backend.infrastructure.repositories.report_repository import (
    AggregateReportRow,
    AuditReportRow,
    InventoryReportRow,
    NotificationReportRow,
    ReportRepository,
    ReportSummary,
    SaleDetailRow,
    SalesExportRow,
    SalesReportRow,
)
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_line_repository import (
    TallyProcessedInvoiceLineRepository,
)
from webstudio_backend.services.report_export_service import ReportExportService, map_row_batches


def _format_additional_products(lines: Sequence[object]) -> str:
    segments: list[str] = []
    for line in lines:
        name = (getattr(line, "stock_item_name", None) or "Item").strip()
        quantity = getattr(line, "quantity", None)
        amount = getattr(line, "line_total", None)
        segment = name
        if quantity:
            segment = f"{segment} x{quantity}"
        if amount is not None:
            segment = f"{segment} = {amount}"
        segments.append(segment)
    return "; ".join(segments)


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ReportRepository(session)
        self._exporter = ReportExportService()

    async def inventory_report(
        self,
        filters: ReportFilters,
        page_params: PageParams,
    ) -> tuple[PageResult[InventoryReportRow], ReportSummary]:
        summary = await self._repo.inventory_summary(filters)
        rows = await self._repo.search_inventory(filters, page_params)
        return rows, summary

    async def sales_report(
        self,
        filters: ReportFilters,
        page_params: PageParams,
    ) -> PageResult[SalesReportRow]:
        return await self._repo.search_sales(filters, page_params)

    async def get_sale_detail(self, sale_id: int) -> SaleDetailRow | None:
        return await self._repo.get_sale_detail_by_id(sale_id)

    async def audit_report(
        self,
        filters: ReportFilters,
        page_params: PageParams,
    ) -> PageResult[AuditReportRow]:
        return await self._repo.search_audit(filters, page_params)

    async def notifications_report(
        self,
        filters: ReportFilters,
        page_params: PageParams,
    ) -> PageResult[NotificationReportRow]:
        return await self._repo.search_notifications(filters, page_params)

    async def location_report(self, filters: ReportFilters) -> list[AggregateReportRow]:
        return await self._repo.aggregate_by_location(filters)

    async def brand_report(self, filters: ReportFilters) -> list[AggregateReportRow]:
        return await self._repo.aggregate_by_brand(filters)

    async def product_model_report(self, filters: ReportFilters) -> list[AggregateReportRow]:
        return await self._repo.aggregate_by_product_model(filters)

    async def export_report(
        self,
        *,
        report_type: ReportType,
        export_format: ExportFormat,
        filters: ReportFilters,
    ) -> tuple[bytes, str, str]:
        generated_at = datetime.now(UTC)
        title = f"WEBSTUDIO IMS {report_type.value.replace('_', ' ').title()} Report"

        if report_type is ReportType.INVENTORY:
            inventory_rows: list[InventoryReportRow] = []
            async for batch in self._repo.stream_inventory(filters):
                inventory_rows.extend(batch)
            del generated_at
            return await self._exporter.build_inventory_export(
                export_format=export_format,
                rows=inventory_rows,
            )
        if report_type is ReportType.SALES:
            sales_rows: list[SalesExportRow] = []
            async for batch in self._repo.stream_sales_export(filters):
                sales_rows.extend(batch)
            additional_by_guid = await self._additional_products_by_guid(sales_rows)
            del generated_at
            return await self._exporter.build_sales_export(
                export_format=export_format,
                rows=sales_rows,
                additional_by_guid=additional_by_guid,
            )
        if report_type is ReportType.AUDIT:
            batches = map_row_batches(
                self._repo.stream_audit(filters),
                self._exporter.audit_row_values,
            )
            headers = self._exporter.audit_headers()
        elif report_type is ReportType.NOTIFICATION:
            batches = map_row_batches(
                self._repo.stream_notifications(filters),
                self._exporter.notification_row_values,
            )
            headers = self._exporter.notification_headers()
        elif report_type is ReportType.LOCATION:
            rows = await self._repo.aggregate_by_location(filters)
            batches = self._static_batches(rows, self._exporter.aggregate_row_values)
            headers = self._exporter.aggregate_headers()
        elif report_type is ReportType.BRAND:
            rows = await self._repo.aggregate_by_brand(filters)
            batches = self._static_batches(rows, self._exporter.aggregate_row_values)
            headers = self._exporter.aggregate_headers()
        elif report_type is ReportType.PRODUCT_MODEL:
            rows = await self._repo.aggregate_by_product_model(filters)
            batches = self._static_batches(rows, self._exporter.aggregate_row_values)
            headers = self._exporter.aggregate_headers()
        else:
            raise ValueError(f"Unsupported report type: {report_type}")

        del generated_at
        return await self._exporter.build_export(
            report_type=report_type,
            export_format=export_format,
            title=title,
            headers=headers,
            row_batches=batches,
        )

    async def _additional_products_by_guid(self, rows: Sequence[SalesExportRow]) -> dict[str, str]:
        """Map each Tally voucher GUID to a readable 'additional products' summary."""
        guids = {row.tally_voucher_guid for row in rows if row.tally_voucher_guid}
        if not guids:
            return {}
        line_repo = TallyProcessedInvoiceLineRepository(self._session)
        result: dict[str, str] = {}
        for guid in guids:
            lines = await line_repo.list_additional_products_for_guid(guid)
            if lines:
                result[guid] = _format_additional_products(lines)
        return result

    @staticmethod
    def _static_batches(
        rows: Sequence[object],
        mapper: Callable[[object], Sequence[object]],
    ) -> AsyncIterator[list[Sequence[object]]]:
        async def _generator() -> AsyncIterator[list[Sequence[object]]]:
            if rows:
                yield [mapper(row) for row in rows]

        return _generator()
