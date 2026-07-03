"""HTTP client for Tally ERP 9 XML interface."""

from __future__ import annotations

from datetime import date, datetime

import httpx

from webstudio_backend.integrations.tally.connectivity import map_exception_to_user_message
from webstudio_backend.integrations.tally.constants import MONITORED_VOUCHER_TYPES


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
        <SVFROMDATE>{from_str}</SVFROMDATE>
        <SVTODATE>{to_str}</SVTODATE>
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

    async def export_monitored_voucher_types(
        self,
        *,
        company_name: str,
        from_date: date,
        to_date: date | None = None,
    ) -> dict[str, str]:
        results: dict[str, str] = {}
        for voucher_type in MONITORED_VOUCHER_TYPES:
            results[voucher_type] = await self.export_vouchers(
                company_name=company_name,
                voucher_type=voucher_type,
                from_date=from_date,
                to_date=to_date,
            )
        return results
