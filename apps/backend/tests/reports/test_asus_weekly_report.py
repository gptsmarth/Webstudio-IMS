"""ASUS sell-out template and per-unit prices."""

from __future__ import annotations

import gzip
import io
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from openpyxl import load_workbook
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies import auth
from webstudio_backend.api.routers.reports import router
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.database.enums import ProductCategory, SaleSource, UserRole
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.repositories.report_repository import AsusWeeklySaleRow
from webstudio_backend.services.asus_weekly_report_service import AsusWeeklyReportService


def _service() -> AsusWeeklyReportService:
    return AsusWeeklyReportService(AsyncMock(spec=AsyncSession))


def _invoice_xml() -> bytes:
    return gzip.compress(b"""
        <VOUCHER><GUID>weekly-report-example</GUID>
        <VOUCHERTYPENAME>NEW SALE</VOUCHERTYPENAME><DATE>20261031</DATE>
        <PARTYLEDGERNAME>Customer</PARTYLEDGERNAME>
        <LEDGERENTRIES.LIST><LEDGERNAME>Customer</LEDGERNAME><AMOUNT>-68000</AMOUNT></LEDGERENTRIES.LIST>
        <LEDGERENTRIES.LIST><LEDGERNAME>Output CGST</LEDGERNAME><AMOUNT>5186.44</AMOUNT></LEDGERENTRIES.LIST>
        <LEDGERENTRIES.LIST><LEDGERNAME>Output SGST</LEDGERNAME><AMOUNT>5186.44</AMOUNT></LEDGERENTRIES.LIST>
        <ALLINVENTORYENTRIES.LIST><STOCKITEMNAME>Laptop</STOCKITEMNAME>
        <SERIALNUMBER>000123TEST</SERIALNUMBER><AMOUNT>56779.67</AMOUNT>
        </ALLINVENTORYENTRIES.LIST>
        <ALLINVENTORYENTRIES.LIST><STOCKITEMNAME>Backpack</STOCKITEMNAME>
        <AMOUNT>846.60</AMOUNT></ALLINVENTORYENTRIES.LIST>
        <ALLINVENTORYENTRIES.LIST><STOCKITEMNAME>Keyboard and mouse</STOCKITEMNAME>
        <SERIALNUMBER>ACCESSORY001</SERIALNUMBER><AMOUNT>0.85</AMOUNT>
        </ALLINVENTORYENTRIES.LIST>
        </VOUCHER>
        """)


def _sale(*, source: SaleSource = SaleSource.TALLY, gross: float | None = 56779.67) -> Sale:
    return Sale(
        invoice_number="AES/0482/26-27",
        customer_name="=Customer (literal text)",
        sold_at=datetime(2026, 10, 30, 19, 0, tzinfo=UTC),
        sale_source=source,
        sale_amount=gross,
        tally_company_name="AES" if source == SaleSource.TALLY else None,
        tally_voucher_guid="weekly-report-example" if source == SaleSource.TALLY else None,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("products", "expected"),
    [
        ("laptops", [(67000.01, "000123TEST", "X1504VAP")]),
        ("accessories", [(1.01, "ACCESSORY001", "90XBTEST")]),
        ("both", [(67000.01, "000123TEST", "X1504VAP"), (1.01, "ACCESSORY001", "90XBTEST")]),
    ],
)
async def test_weekly_export_template_and_corrected_invoice_prices(products, expected) -> None:
    service = _service()
    sales = [
        AsusWeeklySaleRow(_sale(), ProductCategory.LAPTOP, "X1504VAP-IN011WS", None, "000123TEST"),
        AsusWeeklySaleRow(
            _sale(gross=0.85), ProductCategory.ACCESSORY, "CW101", "90XBTEST", "ACCESSORY001"
        ),
    ]
    service._reports.list_asus_weekly_sales = AsyncMock(return_value=sales)
    service._invoices.find_latest_by_guid = AsyncMock(
        return_value=SimpleNamespace(raw_xml_gzip=_invoice_xml())
    )

    report = await service.export(date(2026, 10, 31), date(2026, 10, 31), products)

    workbook = load_workbook(io.BytesIO(report))
    assert workbook.sheetnames == ["Sheet1"]
    sheet = workbook.active
    assert [cell.value for cell in sheet[1]] == [
        "Invoice_No",
        "Invoice_Date(MM/DD/YYYY)",
        "Customer_Name",
        "GST_Number",
        "Quantity",
        "Unit_Price",
        "SSN_IMEI",
        "Part_Number",
    ]
    assert sheet["A1"].font.bold
    assert sheet["A1"].fill.patternType == "solid"
    rows = list(sheet.iter_rows(min_row=2))
    assert len(rows) == len(expected)
    for cells, values in zip(rows, expected, strict=True):
        assert [cell.value for cell in cells] == [
            482,
            datetime(2026, 10, 31),
            "=Customer (literal text)",
            "ASUSENDUSER1234",
            1,
            *values,
        ]
        assert cells[1].number_format == "mm/dd/yyyy"
        assert cells[2].data_type == "s"
        assert cells[5].number_format == "0.00"
        assert cells[6].data_type == "s"
    service._invoices.find_latest_by_guid.assert_awaited_once_with(
        "weekly-report-example", company_name="AES"
    )
    start, end = service._reports.list_asus_weekly_sales.await_args.args
    assert start.astimezone(UTC) == datetime(2026, 10, 30, 18, 30, tzinfo=UTC)
    assert end.astimezone(UTC) == datetime(2026, 10, 31, 18, 29, 59, 999999, tzinfo=UTC)


@pytest.mark.asyncio
async def test_report_refuses_unverified_tally_unit_price() -> None:
    service = _service()
    service._reports.list_asus_weekly_sales = AsyncMock(
        return_value=[
            AsusWeeklySaleRow(_sale(), ProductCategory.LAPTOP, "X1504VAP-IN011WS", None, "SERIAL")
        ]
    )
    service._invoices.find_latest_by_guid = AsyncMock(return_value=None)

    with pytest.raises(AppError, match="GST-inclusive unit price is unavailable"):
        await service.export(date(2026, 10, 31), date(2026, 10, 31), "laptops")


@pytest.mark.asyncio
async def test_report_rejects_reversed_dates() -> None:
    service = _service()
    service._reports.list_asus_weekly_sales = AsyncMock()

    with pytest.raises(AppError, match="From date must be on or before To date"):
        await service.export(date(2026, 11, 1), date(2026, 10, 31), "both")
    service._reports.list_asus_weekly_sales.assert_not_awaited()


@pytest.mark.asyncio
async def test_download_route_checks_permission_and_returns_excel(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router)
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = [
        (
            _sale(source=SaleSource.MANUAL, gross=67000.01),
            ProductCategory.LAPTOP,
            "X1504VAP-IN011WS",
            None,
            "LAPTOP001",
        )
    ]
    permissions = ["reports:view"]
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[auth.get_current_user] = lambda: auth.AuthenticatedUser(
        user=User(id=1, role=UserRole.ADMIN), permissions=permissions
    )
    monkeypatch.setattr(auth, "_audit_permission_denied", AsyncMock())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        params = {"date_from": "2026-10-31", "date_to": "2026-10-31", "products": "laptops"}
        denied = await client.get("/api/v1/reports/asus-weekly", params=params)
        assert denied.status_code == 403
        session.execute.assert_not_awaited()
        permissions.append("reports:export")
        allowed = await client.get("/api/v1/reports/asus-weekly", params=params)

    assert allowed.status_code == 200
    assert allowed.headers["content-disposition"] == (
        'attachment; filename="ASUS_ALP_SellOut_Weekly.xlsx"'
    )
    assert allowed.headers["content-type"].endswith("spreadsheetml.sheet")
    assert load_workbook(io.BytesIO(allowed.content)).active["F2"].value == 67000.01
    statement = session.execute.await_args.args[0].compile(dialect=postgresql.dialect())
    assert "sales.cancelled_at IS NULL" in str(statement)
    assert "ASUS" in statement.params.values()
