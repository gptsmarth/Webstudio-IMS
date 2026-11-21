"""Purchase quantity parsing and multi-serial extraction from Tally XML."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import TallyPurchaseStatus
from webstudio_backend.infrastructure.database.models.tally_purchase_voucher import (
    TallyPurchaseVoucher,
)
from webstudio_backend.integrations.tally.quantity import parse_tally_quantity
from webstudio_backend.integrations.tally.xml_parser import (
    merge_vouchers_by_guid,
    parse_vouchers_xml,
)
from webstudio_backend.services.tally_connectivity_service import TallyConnectivityService
from webstudio_backend.services.tally_sync_service import TallySyncService


def test_parse_tally_quantity_handles_nos_suffix() -> None:
    assert parse_tally_quantity("4 Nos") == 4
    assert parse_tally_quantity("1.00 Nos") == 1
    assert parse_tally_quantity("2") == 2
    assert parse_tally_quantity(None, default=0) == 0


def test_extract_serial_collects_multiple_basicuserdescription_lines() -> None:
    """Matches Tally UI: one stock item row, qty 4, serial on each description line."""
    xml = """
    <ENVELOPE>
      <BODY>
        <DATA>
          <TALLYMESSAGE>
            <VOUCHER REMOTEID="purchase-basic-multi" VCHTYPE="Purchase">
              <DATE>20260701</DATE>
              <VOUCHERNUMBER>88</VOUCHERNUMBER>
              <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>ASUS NUX3405CA-QL1111WS</STOCKITEMNAME>
                <ACTUALQTY>4 Nos</ACTUALQTY>
                <BASICUSERDESCRIPTION.LIST>
                  <BASICUSERDESCRIPTION>W1N0CX049069045</BASICUSERDESCRIPTION>
                  <BASICUSERDESCRIPTION>W1N0CX049096048</BASICUSERDESCRIPTION>
                  <BASICUSERDESCRIPTION>W1N0CX049097042</BASICUSERDESCRIPTION>
                  <BASICUSERDESCRIPTION>W1N0CX04918204F</BASICUSERDESCRIPTION>
                </BASICUSERDESCRIPTION.LIST>
              </ALLINVENTORYENTRIES.LIST>
            </VOUCHER>
          </TALLYMESSAGE>
        </DATA>
      </BODY>
    </ENVELOPE>
    """
    vouchers = parse_vouchers_xml(xml)
    line = vouchers[0].inventory_lines[0]
    assert line.quantity == "4 Nos"
    assert line.batch_allocations == [
        "W1N0CX049069045",
        "W1N0CX049096048",
        "W1N0CX049097042",
        "W1N0CX04918204F",
    ]


def test_extract_serial_splits_comma_separated_basicuserdescription() -> None:
    xml = """
    <ENVELOPE><BODY><DATA><TALLYMESSAGE>
      <VOUCHER REMOTEID="purchase-comma-serials">
        <DATE>20260701</DATE>
        <ALLINVENTORYENTRIES.LIST>
          <STOCKITEMNAME>ASUS NUX3405CA-QL1111WS</STOCKITEMNAME>
          <ACTUALQTY>4 Nos</ACTUALQTY>
          <BASICUSERDESCRIPTION.LIST>
            <BASICUSERDESCRIPTION>W1N0CX049069045, W1N0CX049096048, W1N0CX049097042, W1N0CX04918204F</BASICUSERDESCRIPTION>
          </BASICUSERDESCRIPTION.LIST>
        </ALLINVENTORYENTRIES.LIST>
      </VOUCHER>
    </TALLYMESSAGE></DATA></BODY></ENVELOPE>
    """
    line = parse_vouchers_xml(xml)[0].inventory_lines[0]
    assert line.batch_allocations == [
        "W1N0CX049069045",
        "W1N0CX049096048",
        "W1N0CX049097042",
        "W1N0CX04918204F",
    ]


def test_extract_serial_splits_comma_separated_batch_serialnumber() -> None:
    xml = """
    <ENVELOPE><BODY><DATA><TALLYMESSAGE>
      <VOUCHER REMOTEID="purchase-comma-batch">
        <DATE>20260701</DATE>
        <ALLINVENTORYENTRIES.LIST>
          <STOCKITEMNAME>ASUS NUX3405CA-QL1111WS</STOCKITEMNAME>
          <ACTUALQTY>2 Nos</ACTUALQTY>
          <BATCHALLOCATIONS.LIST>
            <SERIALNUMBER>W1N0CX049069045, W1N0CX049096048</SERIALNUMBER>
          </BATCHALLOCATIONS.LIST>
        </ALLINVENTORYENTRIES.LIST>
      </VOUCHER>
    </TALLYMESSAGE></DATA></BODY></ENVELOPE>
    """
    line = parse_vouchers_xml(xml)[0].inventory_lines[0]
    assert line.batch_allocations == ["W1N0CX049069045", "W1N0CX049096048"]


def test_extract_serial_skips_warranty_in_basicuserdescription() -> None:
    xml = """
    <ENVELOPE><BODY><DATA><TALLYMESSAGE>
      <VOUCHER REMOTEID="sale-one-serial">
        <DATE>20260701</DATE>
        <ALLINVENTORYENTRIES.LIST>
          <STOCKITEMNAME>ASUS Laptop</STOCKITEMNAME>
          <BASICUSERDESCRIPTION.LIST>
            <BASICUSERDESCRIPTION>TBN0CX00904345A</BASICUSERDESCRIPTION>
            <BASICUSERDESCRIPTION>Warranty by ASUS</BASICUSERDESCRIPTION>
          </BASICUSERDESCRIPTION.LIST>
        </ALLINVENTORYENTRIES.LIST>
      </VOUCHER>
    </TALLYMESSAGE></DATA></BODY></ENVELOPE>
    """
    line = parse_vouchers_xml(xml)[0].inventory_lines[0]
    assert line.batch_allocations == ["TBN0CX00904345A"]


def test_extract_serial_prefers_multiple_batch_over_basicuserdescription() -> None:
    xml = """
    <ENVELOPE>
      <BODY>
        <DATA>
          <TALLYMESSAGE>
            <VOUCHER REMOTEID="purchase-multi" VCHTYPE="Purchase">
              <DATE>20260701</DATE>
              <VOUCHERNUMBER>77</VOUCHERNUMBER>
              <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>ASUS F1504FA-BQ2113WS</STOCKITEMNAME>
                <ACTUALQTY>4 Nos</ACTUALQTY>
                <BASICUSERDESCRIPTION.LIST>
                  <BASICUSERDESCRIPTION>SN-FIRST-ONLY</BASICUSERDESCRIPTION>
                </BASICUSERDESCRIPTION.LIST>
                <BATCHALLOCATIONS.LIST><SERIALNUMBER>SN-001</SERIALNUMBER></BATCHALLOCATIONS.LIST>
                <BATCHALLOCATIONS.LIST><SERIALNUMBER>SN-002</SERIALNUMBER></BATCHALLOCATIONS.LIST>
                <BATCHALLOCATIONS.LIST><SERIALNUMBER>SN-003</SERIALNUMBER></BATCHALLOCATIONS.LIST>
                <BATCHALLOCATIONS.LIST><SERIALNUMBER>SN-004</SERIALNUMBER></BATCHALLOCATIONS.LIST>
              </ALLINVENTORYENTRIES.LIST>
            </VOUCHER>
          </TALLYMESSAGE>
        </DATA>
      </BODY>
    </ENVELOPE>
    """
    vouchers = parse_vouchers_xml(xml)
    assert len(vouchers) == 1
    line = vouchers[0].inventory_lines[0]
    assert line.quantity == "4 Nos"
    assert line.batch_allocations == ["SN-001", "SN-002", "SN-003", "SN-004"]
    assert line.serial_number == "SN-001"


def test_purchase_invoice_with_two_different_models() -> None:
    """Voucher 119 shape: qty 1 model A + qty 4 model B on one purchase."""
    xml = """
    <ENVELOPE><BODY><DATA><TALLYMESSAGE>
      <VOUCHER REMOTEID="purchase-119" VCHTYPE="Purchase">
        <DATE>20260718</DATE>
        <VOUCHERNUMBER>119</VOUCHERNUMBER>
        <ALLINVENTORYENTRIES.LIST>
          <STOCKITEMNAME>ASUS NUX3405CA-QL1014WS</STOCKITEMNAME>
          <ACTUALQTY>1 Nos</ACTUALQTY>
          <BASICUSERDESCRIPTION.LIST>
            <BASICUSERDESCRIPTION>W2N0CX01W43406E</BASICUSERDESCRIPTION>
          </BASICUSERDESCRIPTION.LIST>
        </ALLINVENTORYENTRIES.LIST>
        <ALLINVENTORYENTRIES.LIST>
          <STOCKITEMNAME>ASUS NUX3405CA-QL1111WS</STOCKITEMNAME>
          <ACTUALQTY>4 Nos</ACTUALQTY>
          <BASICUSERDESCRIPTION.LIST>
            <BASICUSERDESCRIPTION>W1N0CX049069045</BASICUSERDESCRIPTION>
            <BASICUSERDESCRIPTION>W1N0CX049096048</BASICUSERDESCRIPTION>
            <BASICUSERDESCRIPTION>W1N0CX049097042</BASICUSERDESCRIPTION>
            <BASICUSERDESCRIPTION>W1N0CX04918204F</BASICUSERDESCRIPTION>
          </BASICUSERDESCRIPTION.LIST>
        </ALLINVENTORYENTRIES.LIST>
      </VOUCHER>
    </TALLYMESSAGE></DATA></BODY></ENVELOPE>
    """
    voucher = parse_vouchers_xml(xml)[0]
    assert len(voucher.inventory_lines) == 2
    line_a, line_b = voucher.inventory_lines
    assert line_a.stock_item_name == "ASUS NUX3405CA-QL1014WS"
    assert line_a.quantity == "1 Nos"
    assert line_a.batch_allocations == ["W2N0CX01W43406E"]
    assert line_b.stock_item_name == "ASUS NUX3405CA-QL1111WS"
    assert line_b.quantity == "4 Nos"
    assert line_b.batch_allocations == [
        "W1N0CX049069045",
        "W1N0CX049096048",
        "W1N0CX049097042",
        "W1N0CX04918204F",
    ]


def test_sales_invoice_expands_two_models_independently() -> None:
    from webstudio_backend.integrations.tally.xml_parser import expand_inventory_lines

    xml = """
    <ENVELOPE><BODY><DATA><TALLYMESSAGE>
      <VOUCHER REMOTEID="sale-two-models">
        <DATE>20260718</DATE>
        <ALLINVENTORYENTRIES.LIST>
          <STOCKITEMNAME>ASUS NUX3405CA-QL1014WS</STOCKITEMNAME>
          <ACTUALQTY>1 Nos</ACTUALQTY>
          <BASICUSERDESCRIPTION.LIST>
            <BASICUSERDESCRIPTION>W2N0CX01W43406E</BASICUSERDESCRIPTION>
          </BASICUSERDESCRIPTION.LIST>
        </ALLINVENTORYENTRIES.LIST>
        <ALLINVENTORYENTRIES.LIST>
          <STOCKITEMNAME>ASUS NUX3405CA-QL1111WS</STOCKITEMNAME>
          <ACTUALQTY>2 Nos</ACTUALQTY>
          <BASICUSERDESCRIPTION.LIST>
            <BASICUSERDESCRIPTION>W1N0CX049069045</BASICUSERDESCRIPTION>
            <BASICUSERDESCRIPTION>W1N0CX049096048</BASICUSERDESCRIPTION>
          </BASICUSERDESCRIPTION.LIST>
        </ALLINVENTORYENTRIES.LIST>
      </VOUCHER>
    </TALLYMESSAGE></DATA></BODY></ENVELOPE>
    """
    lines = parse_vouchers_xml(xml)[0].inventory_lines
    expanded = expand_inventory_lines(lines)
    assert len(expanded) == 3
    assert [line.stock_item_name for line in expanded] == [
        "ASUS NUX3405CA-QL1014WS",
        "ASUS NUX3405CA-QL1111WS",
        "ASUS NUX3405CA-QL1111WS",
    ]
    assert [line.serial_number for line in expanded] == [
        "W2N0CX01W43406E",
        "W1N0CX049069045",
        "W1N0CX049096048",
    ]


def test_merge_vouchers_by_guid_prefers_richer_register_copy() -> None:
    sparse_xml = """
    <ENVELOPE><BODY><DATA><TALLYMESSAGE>
      <VOUCHER REMOTEID="g-purchase">
        <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
        <DATE>20260701</DATE>
        <ALLINVENTORYENTRIES.LIST>
          <STOCKITEMNAME>ASUS F1504FA</STOCKITEMNAME>
          <ACTUALQTY>4 Nos</ACTUALQTY>
          <BASICUSERDESCRIPTION.LIST>
            <BASICUSERDESCRIPTION>SN-ONLY-ONE</BASICUSERDESCRIPTION>
          </BASICUSERDESCRIPTION.LIST>
        </ALLINVENTORYENTRIES.LIST>
      </VOUCHER>
    </TALLYMESSAGE></DATA></BODY></ENVELOPE>
    """
    rich_xml = """
    <ENVELOPE><BODY><DATA><TALLYMESSAGE>
      <VOUCHER REMOTEID="g-purchase">
        <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
        <DATE>20260701</DATE>
        <ALLINVENTORYENTRIES.LIST>
          <STOCKITEMNAME>ASUS F1504FA</STOCKITEMNAME>
          <ACTUALQTY>4 Nos</ACTUALQTY>
          <BATCHALLOCATIONS.LIST><SERIALNUMBER>SN-001</SERIALNUMBER></BATCHALLOCATIONS.LIST>
          <BATCHALLOCATIONS.LIST><SERIALNUMBER>SN-002</SERIALNUMBER></BATCHALLOCATIONS.LIST>
          <BATCHALLOCATIONS.LIST><SERIALNUMBER>SN-003</SERIALNUMBER></BATCHALLOCATIONS.LIST>
          <BATCHALLOCATIONS.LIST><SERIALNUMBER>SN-004</SERIALNUMBER></BATCHALLOCATIONS.LIST>
        </ALLINVENTORYENTRIES.LIST>
      </VOUCHER>
    </TALLYMESSAGE></DATA></BODY></ENVELOPE>
    """
    sparse = parse_vouchers_xml(sparse_xml)[0]
    rich = parse_vouchers_xml(rich_xml)[0]
    merged = merge_vouchers_by_guid([sparse, rich])
    assert len(merged) == 1
    assert merged[0].inventory_lines[0].batch_allocations == [
        "SN-001",
        "SN-002",
        "SN-003",
        "SN-004",
    ]


def _purchase_xml(serial_fields: str, *, quantity: int = 10) -> str:
    return f"""
    <ENVELOPE>
      <VOUCHER REMOTEID="purchase-split-serials">
        <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME><DATE>20260701</DATE>
        <ALLINVENTORYENTRIES.LIST>
          <STOCKITEMNAME>ASUS F1504FA</STOCKITEMNAME><ACTUALQTY>{quantity} Nos</ACTUALQTY>
          {serial_fields}
        </ALLINVENTORYENTRIES.LIST>
      </VOUCHER>
    </ENVELOPE>
    """


def test_purchase_recovers_ten_serials_across_tally_fields() -> None:
    xml = _purchase_xml("""
        <BATCHALLOCATIONS.LIST><SERIALNUMBER>ASUS0001,ASUS0002</SERIALNUMBER>
          <SERIALNUMBER.LIST><SERIALNUMBER>ASUS0003&#10;ASUS0004&#xA;ASUS0005</SERIALNUMBER>
          </SERIALNUMBER.LIST>
        </BATCHALLOCATIONS.LIST>
        <SERIALNUMBER.LIST><SERIALNUMBER>asus0005;ASUS0006</SERIALNUMBER></SERIALNUMBER.LIST>
        <BASICUSERDESCRIPTION.LIST>
          <BASICUSERDESCRIPTION>Warranty by ASUS</BASICUSERDESCRIPTION>
          <BASICUSERDESCRIPTION>ASUS0007&#13;&#10;ASUS0008
          123456789009;ASUS0010</BASICUSERDESCRIPTION>
        </BASICUSERDESCRIPTION.LIST>
        """)

    line = parse_vouchers_xml(xml, strict=True)[0].inventory_lines[0]
    assert line.batch_allocations == [
        "ASUS0001",
        "ASUS0002",
        "ASUS0003",
        "ASUS0004",
        "ASUS0005",
        "ASUS0006",
        "ASUS0007",
        "ASUS0008",
        "123456789009",
        "ASUS0010",
    ]


def test_purchase_does_not_guess_between_conflicting_description_serials() -> None:
    voucher = parse_vouchers_xml(
        _purchase_xml(
            "<SERIALNUMBER>ASUS0001</SERIALNUMBER>"
            "<BASICUSERDESCRIPTION>ASUS0002,ASUS0003</BASICUSERDESCRIPTION>",
            quantity=2,
        )
    )[0]
    assert voucher.inventory_lines[0].batch_allocations == ["ASUS0001"]


def test_purchase_retains_richer_duplicate_within_one_tally_response() -> None:
    sparse = _purchase_xml("<SERIALNUMBER>ASUS0001</SERIALNUMBER>", quantity=2)
    rich = _purchase_xml("<SERIALNUMBER>ASUS0001,ASUS0002</SERIALNUMBER>", quantity=2)

    vouchers = parse_vouchers_xml(f"<DATA>{sparse}{rich}</DATA>")

    assert len(vouchers) == 1
    assert vouchers[0].inventory_lines[0].batch_allocations == ["ASUS0001", "ASUS0002"]


def test_purchase_refresh_keeps_richer_serials_but_accepts_quantity_correction() -> None:
    service = TallySyncService(AsyncSession())
    original = parse_vouchers_xml(
        _purchase_xml("<SERIALNUMBER>ASUS0001,ASUS0002</SERIALNUMBER>", quantity=2)
    )[0]
    saved = service._purchase_lines_from_voucher(original)
    sparse = parse_vouchers_xml(_purchase_xml("<SERIALNUMBER>asus0001</SERIALNUMBER>", quantity=2))[
        0
    ]
    corrected = parse_vouchers_xml(
        _purchase_xml("<SERIALNUMBER>ASUS0001</SERIALNUMBER>", quantity=1)
    )[0]

    assert service._purchase_lines_from_voucher(sparse, previous=saved)[0].serial_numbers == [
        "ASUS0001",
        "ASUS0002",
    ]
    assert service._purchase_lines_from_voucher(corrected, previous=saved)[0].serial_numbers == [
        "ASUS0001"
    ]


@pytest.mark.asyncio
async def test_purchase_refresh_checks_day_book_when_register_has_fewer_serials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock(spec=AsyncSession)
    service = TallySyncService(session)
    voucher_date = date(2026, 7, 1)
    header = TallyPurchaseVoucher(
        id=1,
        tally_voucher_guid="purchase-split-serials",
        voucher_date=voucher_date,
        status=TallyPurchaseStatus.PENDING,
    )
    register = _purchase_xml("<SERIALNUMBER>ASUS0001</SERIALNUMBER>", quantity=2)
    day_book = _purchase_xml("<SERIALNUMBER>ASUS0001,ASUS0002</SERIALNUMBER>", quantity=2)
    client = AsyncMock()
    client.export_monitored_voucher_types.return_value = {"voucher_register": register}
    client.export_day_book.return_value = day_book
    monkeypatch.setattr(service._purchase, "get_voucher", AsyncMock(return_value=header))
    monkeypatch.setattr(
        service, "get_connection_config", AsyncMock(return_value=("localhost", "9000", "IMS", 300))
    )
    monkeypatch.setattr(service, "is_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr(TallyConnectivityService, "ensure_workstation_reachable", AsyncMock())
    monkeypatch.setattr(
        TallyConnectivityService, "build_client_for_sync", AsyncMock(return_value=client)
    )

    result = await service.refresh_purchase_voucher(1)

    client.export_day_book.assert_awaited_once_with(
        company_name="IMS", from_date=voucher_date, to_date=voucher_date
    )
    assert result["refreshed"] is True
    assert header.lines[0].serial_numbers == ["ASUS0001", "ASUS0002"]
