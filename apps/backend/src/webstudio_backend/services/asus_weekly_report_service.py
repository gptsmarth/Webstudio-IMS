"""ASUS weekly sell-out workbook from recorded inventory sales."""

from __future__ import annotations

import asyncio
import io
import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Literal

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.database.enums import ProductCategory, SaleSource
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.repositories.report_repository import ReportRepository
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_repository import (
    TallyProcessedInvoiceRepository,
)
from webstudio_backend.integrations.tally.gst import (
    GST_FIELDS,
    has_line_gst_details,
    line_gst_breakdown,
    split_inventory_line,
)
from webstudio_backend.integrations.tally.quantity import parse_tally_quantity
from webstudio_backend.integrations.tally.types import TallyInventoryLine, TallyVoucherTotals
from webstudio_backend.integrations.tally.xml_parser import (
    expand_inventory_lines,
    normalize_serial,
    read_archived_voucher,
)

AsusWeeklyProducts = Literal["laptops", "accessories", "both"]
WorkbookRow = tuple[int | str, date, str, str, int, Decimal, str, str]
AsusInvoice = tuple[TallyVoucherTotals, dict[str, list[TallyInventoryLine]]]

INDIA_TIME = timezone(timedelta(hours=5, minutes=30))
ASUS_WORKBOOK_FILENAME = "ASUS_ALP_SellOut_Weekly.xlsx"
ASUS_WORKBOOK_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ASUS_END_USER_GST_NUMBER = "ASUSENDUSER1234"
ASUS_HEADERS = (
    "Invoice_No",
    "Invoice_Date(MM/DD/YYYY)",
    "Customer_Name",
    "GST_Number",
    "Quantity",
    "Unit_Price",
    "SSN_IMEI",
    "Part_Number",
)
_INVOICE_SEQUENCE = re.compile(r"[^/]+/([0-9]+)/[^/]+")


def _invoice_number(value: str) -> int | str:
    value = value.strip()
    match = _INVOICE_SEQUENCE.fullmatch(value)
    if match:
        value = match[1]
    # Preserve non-sequence references and long identifiers as text in Excel.
    if re.fullmatch(r"[0-9]+", value):
        value = value.lstrip("0") or "0"
        return int(value) if len(value) <= 15 else value
    return value


def _recorded_unit_price(sale: Sale) -> Decimal | None:
    if sale.sale_amount is None:
        return None
    gross = Decimal(str(sale.sale_amount))
    if not gross.is_finite() or gross < 0:
        return None
    if sale.sale_source == SaleSource.MANUAL:
        return gross
    taxes = [getattr(sale, f"sale_{field}") for field in GST_FIELDS]
    if sale.sale_amount_excluding_gst is None or all(tax is None for tax in taxes):
        return None
    base = Decimal(str(sale.sale_amount_excluding_gst))
    if gross == base + sum(Decimal(str(tax)) for tax in taxes if tax is not None):
        return gross
    return None


def _archived_unit_price(invoice: AsusInvoice, serial: str, position: int) -> Decimal | None:
    totals, by_serial = invoice
    for line in by_serial.get(serial, []):
        quantity = parse_tally_quantity(line.quantity, default=1)
        if position >= quantity:
            position -= quantity
            continue
        if not has_line_gst_details(line, totals):
            return None
        unit = split_inventory_line(line, quantity, limit=position + 1)[position]
        breakdown = line_gst_breakdown(unit)
        if breakdown is not None:
            return breakdown.amount_including_gst
        if totals.subtotal is not None and unit.line_total is not None:
            return Decimal(unit.line_total)
        return None
    return None


def _build_workbook(rows: list[WorkbookRow]) -> bytes:
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Sheet1")
    align = Alignment(horizontal="center", vertical="center")
    widths = (16, 29, 30, 23, 13, 17, 25, 20)
    for column, width in zip("ABCDEFGH", widths, strict=True):
        sheet.column_dimensions[column].width = width
    header = []
    for label in ASUS_HEADERS:
        cell = WriteOnlyCell(sheet, value=label)
        cell.font = Font(name="Calibri", size=11, bold=True)
        cell.fill = PatternFill("solid", fgColor="FFE66A")
        cell.alignment = align
        header.append(cell)
    sheet.append(header)
    for row in rows:
        cells = []
        for i, value in enumerate(row):
            if isinstance(value, str):
                cell = WriteOnlyCell(sheet, value=ILLEGAL_CHARACTERS_RE.sub("", value))
                cell.data_type = "s"
            else:
                cell = WriteOnlyCell(sheet, value=value)
            cell.alignment = align
            if i == 1:
                cell.number_format = "mm/dd/yyyy"
            elif i == 5:
                cell.number_format = "0.00"
            cells.append(cell)
        sheet.append(cells)
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


class AsusWeeklyReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._reports = ReportRepository(session)
        self._invoices = TallyProcessedInvoiceRepository(session)

    async def export(self, date_from: date, date_to: date, products: AsusWeeklyProducts) -> bytes:
        if date_from > date_to:
            raise AppError("VALIDATION_ERROR", "From date must be on or before To date.", 422)
        start = datetime.combine(date_from, time.min, tzinfo=INDIA_TIME)
        end = datetime.combine(date_to, time.max, tzinfo=INDIA_TIME)
        sales = await self._reports.list_asus_weekly_sales(start, end)
        category = {
            "laptops": ProductCategory.LAPTOP,
            "accessories": ProductCategory.ACCESSORY,
            "both": None,
        }[products]
        invoices: dict[tuple[str | None, str], AsusInvoice | None] = {}
        positions: defaultdict[tuple[str | None, str, str], int] = defaultdict(int)
        rows: list[WorkbookRow] = []
        issues: list[str] = []
        for record in sales:
            sale = record.sale
            invoice_number = sale.printed_invoice_number or sale.invoice_number
            if record.category is None:
                issues.append(f"{invoice_number}: product category is missing")
                continue
            if category is not None and record.category != category:
                continue
            serial_number = (record.serial_number or "").strip()
            part_number = (
                (record.model_number or "").split("-", 1)[0].strip()
                if record.category == ProductCategory.LAPTOP
                else (record.part_number or "").strip()
            )
            if not serial_number or not part_number:
                missing = "serial number" if not serial_number else "part number"
                issues.append(f"{invoice_number}: {missing} is missing")
                continue
            price = None
            sold_on = sale.sold_at.astimezone(INDIA_TIME).date()
            if sale.tally_voucher_guid:
                key = (sale.tally_company_name, sale.tally_voucher_guid)
                if key not in invoices:
                    invoices[key] = await self._load_invoice(*key)
                invoice = invoices[key]
                serial = normalize_serial(serial_number)
                if invoice is not None and serial is not None:
                    position_key = (*key, serial)
                    price = _archived_unit_price(invoice, serial, positions[position_key])
                    positions[position_key] += 1
            if price is None:
                price = _recorded_unit_price(sale)
            if price is None:
                issues.append(
                    f"{invoice_number} ({serial_number}): GST-inclusive unit price is unavailable"
                )
                continue
            rows.append(
                (
                    _invoice_number(invoice_number),
                    sold_on,
                    sale.customer_name or "",
                    ASUS_END_USER_GST_NUMBER,
                    1,
                    price,
                    serial_number,
                    part_number,
                )
            )
        if issues:
            shown = "; ".join(issues[:5])
            remaining = f"; and {len(issues)-5} more" if len(issues) > 5 else ""
            raise AppError(
                "VALIDATION_ERROR",
                f"Review these sales before exporting the ASUS report: {shown}{remaining}.",
                422,
            )
        return await asyncio.to_thread(_build_workbook, rows)

    async def _load_invoice(self, company: str | None, guid: str) -> AsusInvoice | None:
        record = await self._invoices.find_latest_by_guid(guid, company_name=company)
        if record is None:
            return None
        voucher = read_archived_voucher(record.raw_xml_gzip, guid)
        if voucher is None:
            return None
        lines: defaultdict[str, list[TallyInventoryLine]] = defaultdict(list)
        for line in expand_inventory_lines(voucher.inventory_lines):
            if line.normalized_serial:
                lines[line.normalized_serial].append(line)
        return voucher.totals, lines
