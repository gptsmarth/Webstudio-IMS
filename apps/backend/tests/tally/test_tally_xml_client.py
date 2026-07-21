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
COLLECTION_WITH_VOUCHER = (
    "<ENVELOPE><BODY><DATA><COLLECTION><VOUCHER REMOTEID='g3'>"
    "<VOUCHERTYPENAME>Sales</VOUCHERTYPENAME></VOUCHER></COLLECTION></DATA></BODY></ENVELOPE>"
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
    assert "<EXPLODEFLAG>Yes</EXPLODEFLAG>" in payload
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
async def test_historical_export_prefers_voucher_register(monkeypatch) -> None:
    """Historical backfill must ask Voucher Register FIRST — Day Book often
    returns only today's vouchers and looks 'successful', which previously
    short-circuited the register fallback and zeroed historical fetches."""
    client = TallyXmlClient("tally-laptop", "9000")
    sent: list[str] = []

    async def fake_post_xml(payload: str) -> str:
        sent.append(payload)
        if "Voucher Register" in payload:
            return REGISTER_WITH_VOUCHER
        # Day Book would return today's vouchers — must not be consulted first.
        return DAY_BOOK_WITH_VOUCHER

    monkeypatch.setattr(client, "post_xml", fake_post_xml)
    exports = await client.export_monitored_voucher_types(
        company_name="WEBSTUDIO",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 7, 18),
        historical=True,
    )
    assert list(exports.keys()) == ["voucher_register"]
    assert exports["voucher_register"] == REGISTER_WITH_VOUCHER
    assert len(sent) == 1
    assert "Voucher Register" in sent[0]


@pytest.mark.asyncio
async def test_historical_falls_through_to_ranged_day_book(monkeypatch) -> None:
    client = TallyXmlClient("tally-laptop", "9000")
    sent: list[str] = []

    async def fake_post_xml(payload: str) -> str:
        sent.append(payload)
        if "Voucher Register" in payload:
            return EMPTY_DAY_BOOK
        if "<REPORTNAME>Day Book</REPORTNAME>" in payload:
            return DAY_BOOK_WITH_VOUCHER
        return EMPTY_DAY_BOOK

    monkeypatch.setattr(client, "post_xml", fake_post_xml)
    exports = await client.export_monitored_voucher_types(
        company_name="WEBSTUDIO",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 7, 18),
        historical=True,
    )
    assert list(exports.keys()) == ["day_book_ranged"]
    assert len(sent) == 2


@pytest.mark.asyncio
async def test_historical_falls_through_to_collection(monkeypatch) -> None:
    client = TallyXmlClient("tally-laptop", "9000")
    sent: list[str] = []

    async def fake_post_xml(payload: str) -> str:
        sent.append(payload)
        if "WebstudioVoucherRange" in payload:
            return COLLECTION_WITH_VOUCHER
        return EMPTY_DAY_BOOK

    monkeypatch.setattr(client, "post_xml", fake_post_xml)
    exports = await client.export_monitored_voucher_types(
        company_name="WEBSTUDIO",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 7, 18),
        historical=True,
    )
    assert list(exports.keys()) == ["voucher_collection"]
    assert any("WebstudioDateFilter" in payload for payload in sent)


@pytest.mark.asyncio
async def test_incremental_day_book_also_fetches_voucher_register(monkeypatch) -> None:
    """Incremental sync supplements Day Book with Voucher Register for purchases."""
    client = TallyXmlClient("tally-laptop", "9000")
    sent: list[str] = []

    async def fake_post_xml(payload: str) -> str:
        sent.append(payload)
        if "Voucher Register" in payload:
            return REGISTER_WITH_VOUCHER
        return DAY_BOOK_WITH_VOUCHER

    monkeypatch.setattr(client, "post_xml", fake_post_xml)
    exports = await client.export_monitored_voucher_types(
        company_name="WEBSTUDIO",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 7, 18),
        historical=False,
    )
    assert set(exports.keys()) == {"day_book", "voucher_register"}
    assert len(sent) == 2
    assert any("<ID>Day Book</ID>" in payload for payload in sent)
    assert any("Voucher Register" in payload for payload in sent)


@pytest.mark.asyncio
async def test_same_day_export_includes_register_when_day_book_succeeds(monkeypatch) -> None:
    """Even a today-only window fetches Voucher Register so purchases appear."""
    client = TallyXmlClient("tally-laptop", "9000")
    sent: list[str] = []

    async def fake_post_xml(payload: str) -> str:
        sent.append(payload)
        if "Voucher Register" in payload:
            return REGISTER_WITH_VOUCHER
        return EMPTY_DAY_BOOK

    monkeypatch.setattr(client, "post_xml", fake_post_xml)
    today = date(2026, 7, 18)
    exports = await client.export_monitored_voucher_types(
        company_name="WEBSTUDIO",
        from_date=today,
        to_date=today,
        historical=False,
    )
    assert set(exports.keys()) == {"day_book", "voucher_register"}
    assert len(sent) == 2


DAY_BOOK_LINEERROR = (
    "<ENVELOPE><BODY><DATA><LINEERROR>Could not set company</LINEERROR></DATA></BODY></ENVELOPE>"
)


@pytest.mark.asyncio
async def test_incremental_day_book_lineerror_falls_back_to_voucher_register(
    monkeypatch,
) -> None:
    """LINEERROR on Day Book during incremental sync falls back to Voucher Register."""
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
        historical=False,
    )
    assert list(exports.keys()) == ["voucher_register"]
    assert any("Voucher Register" in payload for payload in sent)
    assert not any("VOUCHERTYPENAME" in payload for payload in sent)


@pytest.mark.asyncio
async def test_historical_per_type_fallback_includes_purchase(monkeypatch) -> None:
    """Last-resort per-type fallback must request Purchase as well as Sales."""
    client = TallyXmlClient("tally-laptop", "9000")
    sent: list[str] = []

    async def fake_post_xml(payload: str) -> str:
        sent.append(payload)
        return DAY_BOOK_LINEERROR

    monkeypatch.setattr(client, "post_xml", fake_post_xml)
    exports = await client.export_monitored_voucher_types(
        company_name="WEBSTUDIO",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 7, 18),
        historical=True,
    )
    assert "Sales" in exports
    assert "NEW SALE" in exports
    assert "Purchase" in exports
    assert "NEW PURCHASE" in exports
    # Register + ranged Day Book + collection + 4 per-type requests.
    assert len(sent) == 7
