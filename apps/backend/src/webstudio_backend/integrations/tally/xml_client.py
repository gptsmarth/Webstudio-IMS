"""HTTP client for Tally ERP 9 XML interface."""

from __future__ import annotations

from datetime import date, datetime

import httpx

from webstudio_backend.integrations.tally.connectivity import map_exception_to_user_message
from webstudio_backend.integrations.tally.constants import (
    MONITORED_VOUCHER_TYPES,
    PURCHASE_VOUCHER_TYPES,
)


class TallyConnectionError(Exception):
    def __init__(self, message: str, *, user_message: str | None = None) -> None:
        super().__init__(message)
        self.user_message = user_message or message


class TallyXmlClient:
    def __init__(self, host: str, port: str, *, timeout: float = 60.0) -> None:
        self._host = host.strip() or "127.0.0.1"
        self._port = port.strip() or "9000"
        self._timeout = timeout
        self._base_url = f"http://{self._host}:{self._port}"

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def resolved_host(self) -> str:
        return self._host

    async def post_xml(self, payload: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._base_url,
                    content=payload.encode("utf-8"),
                    headers={"Content-Type": "text/xml"},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TallyConnectionError(
                str(exc), user_message=map_exception_to_user_message(exc)
            ) from exc
        return response.text

    async def test_connection(self) -> bool:
        payload = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Connection Test</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""
        try:
            result = await self.post_xml(payload)
        except TallyConnectionError:
            return False
        return bool(result.strip())

    def _day_book_export_request(
        self,
        *,
        company_name: str,
        from_date: date,
        to_date: date,
    ) -> str:
        # TYPE="Date" is required — without it several Tally builds ignore the
        # period variables and export only the current date's Day Book, which
        # silently breaks historical fetches.
        from_str = from_date.strftime("%Y%m%d")
        to_str = to_date.strftime("%Y%m%d")
        return f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Day Book</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
        <SVFROMDATE TYPE="Date">{from_str}</SVFROMDATE>
        <SVTODATE TYPE="Date">{to_str}</SVTODATE>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""

    def _voucher_register_export_request(
        self,
        *,
        company_name: str,
        from_date: date,
        to_date: date,
    ) -> str:
        """Period-based report export for a date range.

        ``Voucher Register`` is the report Tally documents for ranged exports.
        Day Book frequently ignores SVFROMDATE/SVTODATE and returns only the
        current Tally date — so historical backfills must prefer this report.
        Read-only (TALLYREQUEST=Export Data).
        """
        from_str = from_date.strftime("%Y%m%d")
        to_str = to_date.strftime("%Y%m%d")
        return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Voucher Register</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
          <SVFROMDATE TYPE="Date">{from_str}</SVFROMDATE>
          <SVTODATE TYPE="Date">{to_str}</SVTODATE>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

    def _day_book_ranged_export_request(
        self,
        *,
        company_name: str,
        from_date: date,
        to_date: date,
    ) -> str:
        """Day Book via the Export Data envelope (same shape as Voucher Register).

        Some Tally builds honour date variables on this envelope even when the
        VERSION/TYPE/ID Day Book form silently returns only today.
        """
        from_str = from_date.strftime("%Y%m%d")
        to_str = to_date.strftime("%Y%m%d")
        return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Day Book</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
          <SVFROMDATE TYPE="Date">{from_str}</SVFROMDATE>
          <SVTODATE TYPE="Date">{to_str}</SVTODATE>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

    def _voucher_collection_export_request(
        self,
        *,
        company_name: str,
        from_date: date,
        to_date: date,
    ) -> str:
        """Collection export with an in-Tally date filter (last-resort historical).

        Uses a read-only TDL Collection + Formulae filter so the date window is
        applied by Tally itself rather than relying on report variables.
        """
        from_str = from_date.strftime("%Y%m%d")
        to_str = to_date.strftime("%Y%m%d")
        return f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>WebstudioVoucherRange</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
        <SVFROMDATE TYPE="Date">{from_str}</SVFROMDATE>
        <SVTODATE TYPE="Date">{to_str}</SVTODATE>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="WebstudioVoucherRange" ISMODIFY="No">
            <TYPE>Voucher</TYPE>
            <FETCH>Date, VoucherTypeName, VoucherNumber, PartyLedgerName, Amount, GUID, MasterID, Reference, AllInventoryEntries.*, LedgerEntries.*</FETCH>
            <FILTER>WebstudioDateFilter</FILTER>
          </COLLECTION>
          <SYSTEM TYPE="Formulae" NAME="WebstudioDateFilter" ISMODIFY="No">
            $$IsBetween:$Date:##SVFROMDATE:##SVTODATE
          </SYSTEM>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""

    def _export_request(
        self,
        *,
        company_name: str,
        voucher_type: str,
        from_date: date,
        to_date: date,
    ) -> str:
        from_str = from_date.strftime("%Y%m%d")
        to_str = to_date.strftime("%Y%m%d")
        return f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Vouchers</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
        <VOUCHERTYPENAME>{voucher_type}</VOUCHERTYPENAME>
        <SVFROMDATE TYPE="Date">{from_str}</SVFROMDATE>
        <SVTODATE TYPE="Date">{to_str}</SVTODATE>
      </STATICVARIABLES>
    </DESC>
    <DATA>
      <TALLYMESSAGE>
        <COLLECTION NAME="Vouchers">
          <TYPE>Voucher</TYPE>
        </COLLECTION>
      </TALLYMESSAGE>
    </DATA>
  </BODY>
</ENVELOPE>"""

    async def export_day_book(
        self,
        *,
        company_name: str,
        from_date: date,
        to_date: date | None = None,
    ) -> str:
        resolved_to = to_date or datetime.now().date()
        payload = self._day_book_export_request(
            company_name=company_name,
            from_date=from_date,
            to_date=resolved_to,
        )
        return await self.post_xml(payload)

    async def export_vouchers(
        self,
        *,
        company_name: str,
        voucher_type: str,
        from_date: date,
        to_date: date | None = None,
    ) -> str:
        resolved_to = to_date or datetime.now().date()
        payload = self._export_request(
            company_name=company_name,
            voucher_type=voucher_type,
            from_date=from_date,
            to_date=resolved_to,
        )
        return await self.post_xml(payload)

    async def export_voucher_register(
        self,
        *,
        company_name: str,
        from_date: date,
        to_date: date | None = None,
    ) -> str:
        resolved_to = to_date or datetime.now().date()
        payload = self._voucher_register_export_request(
            company_name=company_name,
            from_date=from_date,
            to_date=resolved_to,
        )
        return await self.post_xml(payload)

    async def export_monitored_voucher_types(
        self,
        *,
        company_name: str,
        from_date: date,
        to_date: date | None = None,
        historical: bool = False,
    ) -> dict[str, str]:
        """Export vouchers for sync.

        Tally Prime rejects the legacy ``Vouchers`` collection export (469-byte LINEERROR).
        Day Book returns full voucher XML and is filtered server-side by voucher type.

        ``historical=True`` (purchase/sales backfill) intentionally prefers
        ``Voucher Register`` over Day Book. Many Tally builds ignore Day Book's
        SVFROMDATE/SVTODATE and return only the current Tally date — that looks
        like a successful non-empty response, so a "fall back when empty" check
        never fires and historical fetches silently return zero. Normal
        incremental sync keeps ``historical=False`` (Day Book first) so the
        live sync path is undisturbed.
        """
        resolved_to = to_date or datetime.now().date()
        if historical:
            return await self._export_historical(
                company_name=company_name,
                from_date=from_date,
                to_date=resolved_to,
            )
        return await self._export_incremental(
            company_name=company_name,
            from_date=from_date,
            to_date=resolved_to,
        )

    async def _export_incremental(
        self,
        *,
        company_name: str,
        from_date: date,
        to_date: date,
    ) -> dict[str, str]:
        """Normal sync — Day Book for sales, plus Voucher Register for purchases.

        Day Book often omits Purchase vouchers even when the export succeeds, so
        we always supplement with a read-only Voucher Register pull and merge by
        GUID on the sync side (register wins when it carries richer line detail).

        If Register is empty/fails while Day Book still returns sales, keep trying
        the historical purchase fallbacks (ranged Day Book / TDL collection) so
        Sync Now does not silently miss invoices that Fetch older would find.
        """
        results: dict[str, str] = {}
        day_book_xml = await self.export_day_book(
            company_name=company_name,
            from_date=from_date,
            to_date=to_date,
        )
        if not _xml_response_has_line_error(day_book_xml):
            results["day_book"] = day_book_xml

        register_xml = await self._try_export(
            self._voucher_register_export_request(
                company_name=company_name,
                from_date=from_date,
                to_date=to_date,
            )
        )
        if register_xml is not None:
            results["voucher_register"] = register_xml
        else:
            for key, payload in (
                (
                    "day_book_ranged",
                    self._day_book_ranged_export_request(
                        company_name=company_name,
                        from_date=from_date,
                        to_date=to_date,
                    ),
                ),
                (
                    "voucher_collection",
                    self._voucher_collection_export_request(
                        company_name=company_name,
                        from_date=from_date,
                        to_date=to_date,
                    ),
                ),
            ):
                fallback_xml = await self._try_export(payload)
                if fallback_xml is not None:
                    results[key] = fallback_xml
                    break

        if results:
            return results

        return await self._export_per_type(
            company_name=company_name,
            from_date=from_date,
            to_date=to_date,
        )

    async def _export_historical(
        self,
        *,
        company_name: str,
        from_date: date,
        to_date: date,
    ) -> dict[str, str]:
        """Historical backfill path — Voucher Register first, then ranged Day Book,
        then TDL collection, then per-type. Never trust a Day Book that only
        returned today's vouchers when a multi-day window was requested.
        """
        register_xml = await self._try_export(
            self._voucher_register_export_request(
                company_name=company_name,
                from_date=from_date,
                to_date=to_date,
            )
        )
        if register_xml is not None:
            return {"voucher_register": register_xml}

        day_book_ranged = await self._try_export(
            self._day_book_ranged_export_request(
                company_name=company_name,
                from_date=from_date,
                to_date=to_date,
            )
        )
        if day_book_ranged is not None:
            return {"day_book_ranged": day_book_ranged}

        collection_xml = await self._try_export(
            self._voucher_collection_export_request(
                company_name=company_name,
                from_date=from_date,
                to_date=to_date,
            )
        )
        if collection_xml is not None:
            return {"voucher_collection": collection_xml}

        return await self._export_per_type(
            company_name=company_name,
            from_date=from_date,
            to_date=to_date,
        )

    async def _export_per_type(
        self,
        *,
        company_name: str,
        from_date: date,
        to_date: date,
    ) -> dict[str, str]:
        results: dict[str, str] = {}
        for voucher_type in (*MONITORED_VOUCHER_TYPES, *PURCHASE_VOUCHER_TYPES):
            results[voucher_type] = await self.export_vouchers(
                company_name=company_name,
                voucher_type=voucher_type,
                from_date=from_date,
                to_date=to_date,
            )
        return results

    async def _try_export(self, payload: str) -> str | None:
        try:
            xml_text = await self.post_xml(payload)
        except TallyConnectionError:
            return None
        if _xml_response_has_line_error(xml_text):
            return None
        if not _xml_response_has_vouchers(xml_text):
            return None
        return xml_text


def _xml_response_has_line_error(xml_text: str) -> bool:
    upper = xml_text.upper()
    return "<LINEERROR>" in upper or "<STATUS>0</STATUS>" in upper


def _xml_response_has_vouchers(xml_text: str) -> bool:
    return "<VOUCHER" in xml_text.upper()
