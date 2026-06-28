"""Report business logic."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, PageResult
from webstudio_backend.infrastructure.repositories.report_filters import ExportFormat, ReportFilters, ReportType
from webstudio_backend.infrastructure.repositories.report_repository import (
    AggregateReportRow,
    AuditReportRow,
    InventoryReportRow,
    NotificationReportRow,
    ReportRepository,
    ReportSummary,
    SaleDetailRow,
    SalesReportRow,
)
from webstudio_backend.services.report_export_service import ReportExportService, map_row_batches


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
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
            batches = map_row_batches(
                self._repo.stream_inventory(filters),
                self._exporter.inventory_row_values,
            )
            headers = self._exporter.inventory_headers()
        elif report_type is ReportType.SALES:
            batches = map_row_batches(
                self._repo.stream_sales(filters),
                self._exporter.sales_row_values,
            )
            headers = self._exporter.sales_headers()
        elif report_type is ReportType.AUDIT:
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

    @staticmethod
    def _static_batches(
        rows: Sequence[object],
        mapper: Callable[[object], Sequence[object]],
    ) -> AsyncIterator[list[Sequence[object]]]:
        async def _generator() -> AsyncIterator[list[Sequence[object]]]:
            if rows:
                yield [mapper(row) for row in rows]

        return _generator()
