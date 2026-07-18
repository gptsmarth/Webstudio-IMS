"""Tally XML client export templates."""

from __future__ import annotations

from datetime import date

import pytest

from webstudio_backend.integrations.tally.xml_client import (
    TallyXmlClient,
    _xml_response_has_line_error,
    _xml_response_has_vouchers,
)

EMPTY_DAY_BOOK = "<ENVELOPE><BODY><DATA></DATA></BODY></ENVELOPE>"
DAY_BOOK_WITH_VOUCHER = (
    "<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER REMOTEID='g1'>"
    "<VOUCHERTYPENAME>Sales</VOUCHERTYPENAME></VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"
)
REGISTER_WITH_VOUCHER = (
    "<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER REMOTEID='g2'>"
    "<VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME></VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"
)


def test_day_book_export_request_includes_company_and_typed_dates() -> None:
    client = TallyXmlClient("tally-laptop", "9000")
    payload = client._day_book_export_request(  # noqa: SLF001
        company_name="WEBSTUDIO - (from 1-Apr-2026)",
        from_date=date(2026, 7, 1),
        to_date=date(2026, 7, 31),
    )
    assert "<ID>Day Book</ID>" in payload
    assert "WEBSTUDIO - (from 1-Apr-2026)" in payload
    # TYPE="Date" is required or several Tally builds ignore the period and
    # export only the current date (breaks historical backfill).
    assert '<SVFROMDATE TYPE="Date">20260701</SVFROMDATE>' in payload
    assert '<SVTODATE TYPE="Date">20260731</SVTODATE>' in payload
    assert "VOUCHERTYPENAME" not in payload


def test_voucher_register_export_request_is_read_only_and_ranged() -> None:
    client = TallyXmlClient("tally-laptop", "9000")
    payload = client._voucher_register_export_request(  # noqa: SLF001
        company_name="WEBSTUDIO",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 7, 18),
    )
    assert "<TALLYREQUEST>Export Data</TALLYREQUEST>" in payload
    assert "<REPORTNAME>Voucher Register</REPORTNAME>" in payload
    assert '<SVFROMDATE TYPE="Date">20260601</SVFROMDATE>' in payload
    assert '<SVTODATE TYPE="Date">20260718</SVTODATE>' in payload
    # Read-only guarantee: never an Import request.
    assert "Import" not in payload


def test_xml_response_has_line_error_detects_tally_failure() -> None:
    assert _xml_response_has_line_error(
        "<ENVELOPE><BODY><DATA><LINEERROR>Could not set company</LINEERROR></DATA></BODY></ENVELOPE>"
    )
    assert not _xml_response_has_line_error(
        "<ENVELOPE><HEADER><STATUS>1</STATUS></HEADER><BODY><VOUCHER/></BODY></ENVELOPE>"
    )


def test_xml_response_has_vouchers() -> None:
    assert _xml_response_has_vouchers(DAY_BOOK_WITH_VOUCHER)
    assert not _xml_response_has_vouchers(EMPTY_DAY_BOOK)


@pytest.mark.asyncio
async def test_historical_export_falls_back_to_voucher_register(monkeypatch) -> None:
    """If a ranged Day Book comes back empty, the Voucher Register export is used."""
    client = TallyXmlClient("tally-laptop", "9000")
    sent: list[str] = []

    async def fake_post_xml(payload: str) -> str:
        sent.append(payload)
        if "Voucher Register" in payload:
            return REGISTER_WITH_VOUCHER
        return EMPTY_DAY_BOOK

    monkeypatch.setattr(client, "post_xml", fake_post_xml)
    exports = await client.export_monitored_voucher_types(
        company_name="WEBSTUDIO",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 7, 18),
    )
    assert list(exports.keys()) == ["voucher_register"]
    assert exports["voucher_register"] == REGISTER_WITH_VOUCHER
    assert len(sent) == 2


@pytest.mark.asyncio
async def test_day_book_with_vouchers_needs_no_fallback(monkeypatch) -> None:
    client = TallyXmlClient("tally-laptop", "9000")
    sent: list[str] = []

    async def fake_post_xml(payload: str) -> str:
        sent.append(payload)
        return DAY_BOOK_WITH_VOUCHER

    monkeypatch.setattr(client, "post_xml", fake_post_xml)
    exports = await client.export_monitored_voucher_types(
        company_name="WEBSTUDIO",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 7, 18),
    )
    assert list(exports.keys()) == ["day_book"]
    assert len(sent) == 1


@pytest.mark.asyncio
async def test_same_day_export_skips_register_fallback(monkeypatch) -> None:
    """Regular incremental sync (today-only window) must keep single-request behavior."""
    client = TallyXmlClient("tally-laptop", "9000")
    sent: list[str] = []

    async def fake_post_xml(payload: str) -> str:
        sent.append(payload)
        return EMPTY_DAY_BOOK

    monkeypatch.setattr(client, "post_xml", fake_post_xml)
    today = date(2026, 7, 18)
    exports = await client.export_monitored_voucher_types(
        company_name="WEBSTUDIO",
        from_date=today,
        to_date=today,
    )
    assert list(exports.keys()) == ["day_book"]
    assert len(sent) == 1


DAY_BOOK_LINEERROR = (
    "<ENVELOPE><BODY><DATA><LINEERROR>Could not set company</LINEERROR></DATA></BODY></ENVELOPE>"
)


@pytest.mark.asyncio
async def test_day_book_lineerror_falls_back_to_voucher_register(monkeypatch) -> None:
    """LINEERROR on Day Book must not fall back to Sales-only collection exports —
    that silently zeroes purchase backfill. Prefer Voucher Register (all types)."""
    client = TallyXmlClient("tally-laptop", "9000")
    sent: list[str] = []

    async def fake_post_xml(payload: str) -> str:
        sent.append(payload)
        if "Voucher Register" in payload:
            return REGISTER_WITH_VOUCHER
        return DAY_BOOK_LINEERROR

    monkeypatch.setattr(client, "post_xml", fake_post_xml)
    exports = await client.export_monitored_voucher_types(
        company_name="WEBSTUDIO",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 7, 18),
    )
    assert list(exports.keys()) == ["voucher_register"]
    assert any("Voucher Register" in payload for payload in sent)
    # Must NOT have issued Sales/NEW SALE/Purchase collection exports.
    assert not any("VOUCHERTYPENAME" in payload for payload in sent)


@pytest.mark.asyncio
async def test_lineerror_per_type_fallback_includes_purchase(monkeypatch) -> None:
    """Last-resort per-type fallback must request Purchase as well as Sales."""
    client = TallyXmlClient("tally-laptop", "9000")
    sent: list[str] = []

    async def fake_post_xml(payload: str) -> str:
        sent.append(payload)
        # Day Book and Voucher Register both fail — force the per-type path.
        return DAY_BOOK_LINEERROR

    monkeypatch.setattr(client, "post_xml", fake_post_xml)
    exports = await client.export_monitored_voucher_types(
        company_name="WEBSTUDIO",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 7, 18),
    )
    assert "Sales" in exports
    assert "NEW SALE" in exports
    assert "Purchase" in exports
    assert "NEW PURCHASE" in exports
    # Day Book + Voucher Register + 4 per-type requests.
    assert len(sent) == 6
