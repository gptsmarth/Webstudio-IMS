"""Tally XML client export templates."""

from __future__ import annotations

from datetime import date

from webstudio_backend.integrations.tally.xml_client import (
    TallyXmlClient,
    _xml_response_has_line_error,
)


def test_day_book_export_request_includes_company_and_dates() -> None:
    client = TallyXmlClient("tally-laptop", "9000")
    payload = client._day_book_export_request(  # noqa: SLF001
        company_name="WEBSTUDIO - (from 1-Apr-2026)",
        from_date=date(2026, 7, 1),
        to_date=date(2026, 7, 31),
    )
    assert "<ID>Day Book</ID>" in payload
    assert "WEBSTUDIO - (from 1-Apr-2026)" in payload
    assert "<SVFROMDATE>20260701</SVFROMDATE>" in payload
    assert "<SVTODATE>20260731</SVTODATE>" in payload
    assert "VOUCHERTYPENAME" not in payload


def test_xml_response_has_line_error_detects_tally_failure() -> None:
    assert _xml_response_has_line_error(
        "<ENVELOPE><BODY><DATA><LINEERROR>Could not set company</LINEERROR></DATA></BODY></ENVELOPE>"
    )
    assert not _xml_response_has_line_error(
        "<ENVELOPE><HEADER><STATUS>1</STATUS></HEADER><BODY><VOUCHER/></BODY></ENVELOPE>"
    )
