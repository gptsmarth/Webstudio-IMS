"""Activation matching and credit reconciliation through the normal API."""

import io
from datetime import UTC, date, datetime
from decimal import Decimal

from openpyxl import Workbook, load_workbook
from sqlalchemy import delete, func, select

from webstudio_backend.infrastructure.database.enums import SaleSource
from webstudio_backend.infrastructure.database.models.asus_activation import (
    AsusActivationReceipt,
    AsusActivationScheme,
    AsusActivationWorkbook,
)
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.services.asus_activation import purge_activation_workbooks
from webstudio_backend.services.asus_activation_workbooks import parse_scheme

API = "/api/v1/asus-activation"
MODEL = "GAMING-EXACT001"
AIO = "AIO-EXACT002"


def _workbook(sheets: dict) -> bytes:
    workbook = Workbook(write_only=True)
    for name, rows in sheets.items():
        worksheet = workbook.create_sheet(name)
        for row in rows:
            worksheet.append(row)
    result = io.BytesIO()
    workbook.save(result)
    return result.getvalue()


def _scheme_book() -> bytes:
    return _workbook(
        {
            "Gaming Price List": [
                ["Version", "16th November"],
                ["Model Name", "Supported SRP", "CN/Unit", "(NR261149) 18–30 November"],
                [MODEL, 102990, 12949.152542372874, "18–30 November"],
            ],
            "Gaming T3": [
                ["Model Name", "Supported SRP", "CN/Unit"],
                [MODEL, 102990, 13084.75],
            ],
            "AIO": [
                ["ModelName", "Nov Suported SRP", "CN per unit"],
                [AIO, 59990, 500],
            ],
        }
    )


def _receipt_book() -> bytes:
    return _workbook(
        {
            "Release": [
                [
                    "Scheme Category",
                    "Scheme",
                    "Apllication No",
                    "Model_Name",
                    "IMEI",
                    "CN Amt",
                    "GST Amt",
                    "Release Date",
                ],
                [
                    "Activation",
                    "(NR261149)",
                    "BATCH-1",
                    MODEL.lower(),
                    " gaming-a1 ",
                    12949.15,
                    2330.85,
                    date(2026, 12, 7),
                ],
                ["Activation", "", "BATCH-1", AIO, "000225588", 498.75, 89.775, date(2026, 12, 7)],
                ["Activation", "", "BATCH-1", AIO, "UNKNOWN-123", 500, 90, date(2026, 12, 7)],
            ],
        }
    )


def _sale(model, serial, day, *, price=Decimal("129800.00"), brand="ASUS"):
    return Sale(
        invoice_number="AES/0001/26-27",
        customer_name="=Literal Text",
        sold_at=datetime(2026, 11, day, 5, 0, tzinfo=UTC),
        sale_source=SaleSource.TALLY,
        sale_amount=price,
        sale_amount_excluding_gst=Decimal("110000.00"),
        sale_cgst_amount=Decimal("9900.00"),
        sale_sgst_amount=Decimal("9900.00"),
        snapshot_brand_name=brand,
        snapshot_model_number=model,
        snapshot_serial_number=serial,
    )


def test_activation_scheme_prefers_gaming_price_list_and_keeps_full_model_number():
    rules = parse_scheme(_scheme_book())
    assert rules[MODEL]["cn"] == "12949.15"
    assert rules[MODEL]["scheme_code"] == "NR261149"
    assert rules[AIO]["srp"] == "59990.00"


async def test_activation_workflow(api_client, main_admin_headers, salesperson_headers, db_session):
    db_session.add_all(
        [
            _sale(MODEL, "GAMING-A1", 16),
            _sale(AIO, "000225588", 30),
            _sale(MODEL, "OUTSIDE-16", 15),
            _sale(MODEL + "-OTHER", "WRONG-MODEL", 16),
            _sale(MODEL, "WRONG-BRAND", 16, brand="OTHER"),
        ]
    )
    await db_session.commit()
    auth = main_admin_headers

    denied = await api_client.get(API, headers=salesperson_headers)
    assert denied.status_code == 403
    no_scheme = await api_client.get(API, params={"month": "2026-11"}, headers=auth)
    assert no_scheme.json()["data"]["claims"] == []

    params = {"date_from": "2026-11-16", "date_to": "2026-11-30"}
    file = {"file": ("scheme.xlsx", _scheme_book())}
    try:
        upload = await api_client.post(API + "/schemes", files=file, data=params, headers=auth)
        assert upload.status_code == 200, upload.text
        assert upload.json()["data"]["rule_count"] == 2
        conflicting = await api_client.post(
            API + "/schemes", files=file, data={**params, "date_from": "2026-11-15"}, headers=auth
        )
        assert conflicting.status_code == 409
        dashboard = await api_client.get(API, params={"month": "2026-11"}, headers=auth)
        claims = {c["serial"]: c for c in dashboard.json()["data"]["claims"]}
        assert set(claims) == {"GAMING-A1", "000225588"}
        assert claims["GAMING-A1"]["unit_price"] == "129800.00"
        assert claims["GAMING-A1"]["expected_amount"] == "12949.15"
        assert claims["GAMING-A1"]["sold_on"] == "2026-11-16"
        assert claims["GAMING-A1"]["program_period"] == "18–30 November"

        db_session.add(_sale(AIO, "LATE-SALE", 29))
        await db_session.commit()
        dashboard = await api_client.get(API, params={"month": "2026-11"}, headers=auth)
        claims = {c["serial"]: c for c in dashboard.json()["data"]["claims"]}
        assert claims["LATE-SALE"]["status"] == "pending"

        outcome = await api_client.post(
            API + f"/claims/{claims['LATE-SALE']['sale_id']}/receipt",
            json={"action": "record", "amount": "500.00", "note": "Manually checked"},
            headers=auth,
        )
        assert outcome.status_code == 200, outcome.text
        assert outcome.json()["data"]["status"] == "received"

        files = {"file": ("received.xlsx", _receipt_book())}
        preview = await api_client.post(API + "/receipts", files=files, headers=auth)
        assert preview.status_code == 200, preview.text
        plan = preview.json()["data"]
        assert plan["counts"] == {"receive": 1, "discrepancy": 1, "unmatched": 1}
        assert plan["received_total"] == "12949.15"
        assert plan["discrepancy_total"] == "498.75"
        assert await db_session.scalar(select(func.count()).select_from(AsusActivationReceipt)) == 1

        confirm = await api_client.post(
            API + "/receipts", files=files, data={"preview_id": plan["preview_id"]}, headers=auth
        )
        assert confirm.status_code == 200, confirm.text
        stale = await api_client.post(
            API + "/receipts", files=files, data={"preview_id": plan["preview_id"]}, headers=auth
        )
        assert stale.status_code == 409
        again = await api_client.post(API + "/receipts", files=files, headers=auth)
        assert again.json()["data"]["counts"] == {"duplicate": 2, "unmatched": 1}

        response = await api_client.get(API, params={"month": "2026-11"}, headers=auth)
        claims = {c["serial"]: c for c in response.json()["data"]["claims"]}
        assert claims["GAMING-A1"]["received_amount"] == "12949.15"
        assert claims["GAMING-A1"]["release_date"] == "2026-12-07"
        assert claims["000225588"]["variance"] == "-1.25"
        assert claims["000225588"]["status"] == "discrepancy"
        resolved = await api_client.post(
            API + f"/claims/{claims['000225588']['sale_id']}/receipt",
            json={"action": "resolve", "note": "Confirmed adjusted settlement with ASUS."},
            headers=auth,
        )
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["data"]["status"] == "received"
        assert resolved.json()["data"]["received_amount"] == "498.75"

        workbook = await api_client.get(
            API + "/export", params={"month": "2026-11", "status": "received"}, headers=auth
        )
        assert workbook.status_code == 200
        sheet = load_workbook(io.BytesIO(workbook.content)).active
        assert sheet.max_row == 4
        assert sheet["C2"].data_type == "s"
        assert sheet["N2"].data_type == "n"
        assert sheet["A2"].data_type == "d"

        december_sale = _sale(AIO, "DECEMBER-AIO", 5)
        december_sale.sold_at = december_sale.sold_at.replace(month=12)
        db_session.add(december_sale)
        await db_session.commit()
        december = await api_client.get(API, params={"month": "2026-12"}, headers=auth)
        assert december.json()["data"]["claims"] == []
        december_upload = await api_client.post(
            API + "/schemes",
            files=file,
            data={"date_from": "2026-12-01", "date_to": "2026-12-15"},
            headers=auth,
        )
        assert december_upload.status_code == 200, december_upload.text
        december = await api_client.get(API, params={"month": "2026-12"}, headers=auth)
        assert [claim["serial"] for claim in december.json()["data"]["claims"]] == ["DECEMBER-AIO"]
        all_months = await api_client.get(API + "/export", params={"status": "all"}, headers=auth)
        assert load_workbook(io.BytesIO(all_months.content)).active.max_row == 5

        scheme = await db_session.scalar(
            select(AsusActivationScheme).where(AsusActivationScheme.date_from == date(2026, 11, 16))
        )
        await db_session.execute(delete(AsusActivationWorkbook))
        db_session.add(
            AsusActivationWorkbook(
                scheme_id=scheme.id, content=b"fixture", expires_at=datetime(2020, 1, 1, tzinfo=UTC)
            )
        )
        await db_session.flush()
        await purge_activation_workbooks(db_session)
        assert not await db_session.get(AsusActivationWorkbook, scheme.id)
        assert await db_session.get(AsusActivationScheme, scheme.id)
    finally:
        await db_session.rollback()
        await db_session.execute(delete(AsusActivationReceipt))
        await db_session.execute(delete(AsusActivationScheme))
        await db_session.commit()


async def test_upload_expired_scheme_finds_saved_sales_by_invoice_date(
    api_client, main_admin_headers, db_session
):
    def october_sale(model, serial, sold_at):
        sale = _sale(model, serial, 16)
        sale.sold_at = sold_at
        return sale

    # 18:30 UTC is midnight in India, independent of when the sale was synced.
    before = datetime(2025, 9, 30, 18, 29, tzinfo=UTC)
    start = datetime(2025, 9, 30, 18, 30, tzinfo=UTC)
    end = datetime(2025, 10, 15, 18, 29, tzinfo=UTC)
    after = datetime(2025, 10, 15, 18, 30, tzinfo=UTC)
    cancelled = october_sale(MODEL, "CANCELLED", start)
    cancelled.cancelled_at = after
    db_session.add_all(
        [
            october_sale(MODEL, "BEFORE", before),
            october_sale(MODEL, "AT-START", start),
            october_sale(AIO, "AT-END", end),
            october_sale(AIO, "AFTER", after),
            october_sale(MODEL + "-OTHER", "OTHER-VARIANT", start),
            cancelled,
        ]
    )
    await db_session.commit()
    headers = main_admin_headers
    month = {"month": "2025-10"}
    file = {"file": ("archived-scheme.xlsx", _scheme_book())}
    dates = {"date_from": "2025-10-01", "date_to": "2025-10-15"}

    try:
        old_month = await api_client.get(API, params=month, headers=headers)
        assert old_month.json()["data"]["claims"] == []
        imported = await api_client.post(API + "/schemes", headers=headers, files=file, data=dates)
        assert imported.status_code == 200, imported.text
        scheme = imported.json()["data"]
        assert scheme["matched_sale_count"] == 2
        again = await api_client.post(API + "/schemes", headers=headers, files=file, data=dates)
        assert again.json()["data"] == scheme
        assert (
            await db_session.scalar(select(func.count()).select_from(AsusActivationWorkbook)) == 0
        )
        old_month = await api_client.get(API, params=month, headers=headers)
        result = old_month.json()["data"]
        assert result["active_scheme"] is None
        assert result["counts"] == {"pending": 2}
        assert {(row["serial"], row["sold_on"]) for row in result["claims"]} == {
            ("AT-START", "2025-10-01"),
            ("AT-END", "2025-10-15"),
        }
        export = await api_client.get(
            API + "/export", params={**month, "status": "pending"}, headers=headers
        )
        sheet = load_workbook(io.BytesIO(export.content)).active
        assert {sheet["E2"].value, sheet["E3"].value} == {"AT-START", "AT-END"}
    finally:
        await db_session.rollback()
        await db_session.execute(delete(AsusActivationScheme))
        await db_session.commit()
