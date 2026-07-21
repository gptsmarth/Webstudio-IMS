"""Purchase quantity parsing and multi-serial extraction from Tally XML."""

from __future__ import annotations

from webstudio_backend.integrations.tally.quantity import parse_tally_quantity
from webstudio_backend.integrations.tally.xml_parser import (
    merge_vouchers_by_guid,
    parse_vouchers_xml,
)


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
