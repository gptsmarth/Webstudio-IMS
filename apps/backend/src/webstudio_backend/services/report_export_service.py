"""Report export — Excel and PDF generation with batched row processing."""

from __future__ import annotations

import asyncio
import io
from collections.abc import AsyncIterator, Callable, Sequence
from datetime import UTC, datetime

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from webstudio_backend.infrastructure.repositories.report_filters import ExportFormat, ReportType
from webstudio_backend.infrastructure.repositories.report_repository import (
    AggregateReportRow,
    AuditReportRow,
    InventoryReportRow,
    NotificationReportRow,
    SalesReportRow,
)

PDF_ROWS_PER_PAGE = 40


class ReportExportService:
    async def build_export(
        self,
        *,
        report_type: ReportType,
        export_format: ExportFormat,
        title: str,
        headers: Sequence[str],
        row_batches: AsyncIterator[list[Sequence[object]]],
    ) -> tuple[bytes, str, str]:
        collected = await self._collect_batches(row_batches)
        if export_format is ExportFormat.XLSX:
            content = await asyncio.to_thread(self._build_xlsx, title, headers, collected)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            extension = "xlsx"
        else:
            content = await asyncio.to_thread(self._build_pdf, title, headers, collected)
            media_type = "application/pdf"
            extension = "pdf"
        filename = (
            f"{report_type.value}-report-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.{extension}"
        )
        return content, media_type, filename

    @staticmethod
    async def _collect_batches(
        batches: AsyncIterator[list[Sequence[object]]],
    ) -> list[list[Sequence[object]]]:
        collected: list[list[Sequence[object]]] = []
        async for batch in batches:
            collected.append(batch)
        return collected

    def inventory_headers(self) -> list[str]:
        return [
            "Serial Number",
            "Brand",
            "Model Number",
            "Model Name",
            "Color",
            "Location",
            "Status",
            "Archived",
            "Purchase Date",
            "Created At",
        ]

    def inventory_row_values(self, row: InventoryReportRow) -> list[object]:
        return [
            row.serial_number,
            row.brand_name,
            row.model_number,
            row.model_name,
            row.color,
            row.location_name,
            row.status,
            row.is_archived,
            row.purchase_date.isoformat() if row.purchase_date else "",
            row.created_at.isoformat(),
        ]

    def sales_headers(self) -> list[str]:
        return [
            "Serial Number",
            "Brand",
            "Model",
            "Location",
            "Invoice",
            "Customer",
            "Payment Mode",
            "Source",
            "Sold At",
            "Recorded By User ID",
        ]

    def sales_row_values(self, row: SalesReportRow) -> list[object]:
        return [
            row.serial_number,
            row.brand_name,
            row.model_name,
            row.location_name,
            row.invoice_number,
            row.customer_name or "",
            row.payment_mode or "",
            row.sale_source,
            row.sold_at.isoformat(),
            row.recorded_by_user_id or "",
        ]

    def aggregate_headers(self) -> list[str]:
        return [
            "Group ID",
            "Group Name",
            "Available",
            "Sold",
            "Received",
            "Reserved",
            "Archived",
            "Total",
        ]

    def aggregate_row_values(self, row: AggregateReportRow) -> list[object]:
        return [
            row.group_id,
            row.group_name,
            row.available,
            row.sold,
            row.received,
            row.reserved,
            row.archived,
            row.total,
        ]

    def audit_headers(self) -> list[str]:
        return [
            "ID",
            "Entity Type",
            "Entity ID",
            "Action",
            "Source",
            "Actor",
            "Actor User ID",
            "Serial Number",
            "Description",
            "Created At",
        ]

    def audit_row_values(self, row: AuditReportRow) -> list[object]:
        return [
            str(row.id),
            row.entity_type,
            row.entity_id,
            row.action,
            row.source,
            row.actor_display_name or "",
            row.actor_user_id or "",
            row.serial_number or "",
            row.description or "",
            row.created_at.isoformat(),
        ]

    def notification_headers(self) -> list[str]:
        return [
            "ID",
            "Type",
            "Title",
            "Description",
            "Category",
            "Severity",
            "Status",
            "Created At",
            "Resolved At",
        ]

    def notification_row_values(self, row: NotificationReportRow) -> list[object]:
        return [
            row.id,
            row.notification_type,
            row.title,
            row.description,
            row.category,
            row.severity,
            row.status,
            row.created_at.isoformat(),
            row.resolved_at.isoformat() if row.resolved_at else "",
        ]

    def _build_xlsx(
        self,
        title: str,
        headers: Sequence[str],
        batches: list[list[Sequence[object]]],
    ) -> bytes:
        workbook = Workbook(write_only=True)
        worksheet = workbook.create_sheet(title=title[:31])
        worksheet.append(list(headers))
        for batch in batches:
            for row in batch:
                worksheet.append([self._cell_value(value) for value in row])
        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    def _build_pdf(
        self,
        title: str,
        headers: Sequence[str],
        batches: list[list[Sequence[object]]],
    ) -> bytes:
        buffer = io.BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=24,
            rightMargin=24,
            topMargin=24,
            bottomMargin=24,
        )
        styles = getSampleStyleSheet()
        story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]

        rows: list[list[object]] = [list(headers)]
        for batch in batches:
            rows.extend(batch)

        for chunk_start in range(0, len(rows), PDF_ROWS_PER_PAGE):
            chunk = rows[chunk_start : chunk_start + PDF_ROWS_PER_PAGE]
            table = Table(
                [[self._cell_value(value) for value in row] for row in chunk],
                repeatRows=1 if chunk_start == 0 else 0,
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
                    ],
                ),
            )
            story.append(table)
            story.append(Spacer(1, 12))

        document.build(story)
        return buffer.getvalue()

    @staticmethod
    def _cell_value(value: object) -> str | int | float | bool:
        if value is None:
            return ""
        if isinstance(value, bool):
            return value
        return str(value)


def map_row_batches(
    batches: AsyncIterator[list[object]],
    mapper: Callable[[object], Sequence[object]],
) -> AsyncIterator[list[Sequence[object]]]:
    async def _generator() -> AsyncIterator[list[Sequence[object]]]:
        async for batch in batches:
            yield [mapper(row) for row in batch]

    return _generator()
