"""Tally voucher XML parser — deterministic serial extraction (no fuzzy matching)."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from webstudio_backend.integrations.tally.types import (
    TallyInventoryLine,
    TallyVoucher,
    TallyVoucherTotals,
)

SERIAL_SOURCE_BASICUSERDESCRIPTION = "basicuserdescription"
SERIAL_SOURCE_SERIALNUMBER = "serialnumber"
SERIAL_SOURCE_BATCH_ALLOCATION = "batch_allocations.serialnumber"


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _child_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if _local_name(child.tag).upper() == name.upper():
            text = (child.text or "").strip()
            return text or None
    return None


def _children_by_name(element: ET.Element, name: str) -> list[ET.Element]:
    target = name.upper()
    return [child for child in element if _local_name(child.tag).upper() == target]


def _parse_tally_date(value: str | None) -> date:
    if not value:
        return datetime.now().date()
    cleaned = value.strip()
    if len(cleaned) == 8 and cleaned.isdigit():
        return datetime.strptime(cleaned, "%Y%m%d").date()
    try:
        return datetime.fromisoformat(cleaned).date()
    except ValueError:
        return datetime.now().date()


def _sanitize_xml_text(xml_text: str) -> str:
    cleaned = xml_text.strip()
    cleaned = re.sub(r"&#(\d+);", lambda m: "" if int(m.group(1)) < 32 else m.group(0), cleaned)
    return "".join(
        ch
        for ch in cleaned
        if ord(ch) in (0x9, 0xA, 0xD) or 0x20 <= ord(ch) <= 0xD7FF or 0xE000 <= ord(ch) <= 0xFFFD
    )


def normalize_serial(value: str | None) -> str | None:
    """Trim + uppercase for comparison. Original value is kept separately."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned.upper()


def _looks_like_inventory_serial(text: str) -> bool:
    """Filter BASICUSERDESCRIPTION noise (e.g. 'Warranty by ASUS') from serial lines."""
    cleaned = text.strip()
    if len(cleaned) < 8:
        return False
    if " " in cleaned:
        return False
    lower = cleaned.lower()
    if "warranty" in lower:
        return False
    return any(char.isalpha() for char in cleaned) and any(char.isdigit() for char in cleaned)


def _expand_serial_text(text: str) -> list[str]:
    """Split one Tally field that may list serials comma- or semicolon-separated."""
    if not text:
        return []
    serials: list[str] = []
    for part in re.split(r"[,;]+", text):
        token = part.strip()
        if token and _looks_like_inventory_serial(token) and token not in serials:
            serials.append(token)
    return serials


def _expand_batch_serial_text(text: str) -> list[str]:
    """Batch allocation serials — trust Tally (accessories may be shorter than 8 chars)."""
    if not text:
        return []
    serials: list[str] = []
    for part in re.split(r"[,;]+", text):
        token = part.strip()
        if not token:
            continue
        if "warranty" in token.lower():
            continue
        if token not in serials:
            serials.append(token)
    return serials


def _collect_basic_serials(line: ET.Element) -> list[str]:
    serials: list[str] = []
    for desc_list in _children_by_name(line, "BASICUSERDESCRIPTION.LIST"):
        for description in _children_by_name(desc_list, "BASICUSERDESCRIPTION"):
            text = (description.text or "").strip()
            if not text:
                continue
            for serial in _expand_serial_text(text):
                if serial not in serials:
                    serials.append(serial)
    return serials


def _collect_batch_serials(line: ET.Element) -> list[str]:
    batch_serials: list[str] = []

    def _append_serial(raw: str) -> None:
        for serial in _expand_batch_serial_text(raw):
            if serial not in batch_serials:
                batch_serials.append(serial)

    for batch in _children_by_name(line, "BATCHALLOCATIONS.LIST"):
        serial = _child_text(batch, "SERIALNUMBER")
        if serial:
            _append_serial(serial)
        for nested in batch.iter():
            if nested is batch:
                continue
            if _local_name(nested.tag).upper() == "SERIALNUMBER":
                text = (nested.text or "").strip()
                if text:
                    _append_serial(text)
    return batch_serials


def _extract_serial_from_line(line: ET.Element) -> tuple[str | None, str | None, list[str]]:
    """
    Production serial priority (WEBSTUDIO):
      1. All BATCHALLOCATIONS.LIST serials when more than one
      2. All serial-like BASICUSERDESCRIPTION entries when more than one
         (Tally lists qty>1 laptops as one model row with a serial per line,
         or comma-separated serials in one description field)
      3. Single batch serial, then single basic description, then SERIALNUMBER

    Warranty / remark lines in BASICUSERDESCRIPTION are ignored.
    """
    try:
        batch_serials = _collect_batch_serials(line)
        basic_serials = _collect_basic_serials(line)

        if len(batch_serials) > 1:
            return batch_serials[0], SERIAL_SOURCE_BATCH_ALLOCATION, batch_serials
        if len(basic_serials) > 1:
            return basic_serials[0], SERIAL_SOURCE_BASICUSERDESCRIPTION, basic_serials
        if len(batch_serials) == 1:
            return batch_serials[0], SERIAL_SOURCE_BATCH_ALLOCATION, batch_serials
        if len(basic_serials) == 1:
            return basic_serials[0], SERIAL_SOURCE_BASICUSERDESCRIPTION, basic_serials

        direct = _child_text(line, "SERIALNUMBER")
        if direct:
            direct_serials = _expand_batch_serial_text(direct)
            if not direct_serials:
                direct_serials = _expand_serial_text(direct)
            if direct_serials:
                return direct_serials[0], SERIAL_SOURCE_SERIALNUMBER, direct_serials
            if _looks_like_inventory_serial(direct):
                return direct, SERIAL_SOURCE_SERIALNUMBER, [direct]
    except Exception:  # noqa: BLE001 — never fail voucher parse on serial extraction
        return None, None, []

    return None, None, []


def format_serial_source_label(serial_source: str | None) -> str | None:
    """Operator-facing serial source label for Main Admin audit."""
    if not serial_source:
        return None
    labels = {
        SERIAL_SOURCE_BASICUSERDESCRIPTION: "BASICUSERDESCRIPTION[0]",
        SERIAL_SOURCE_SERIALNUMBER: "SERIALNUMBER",
        SERIAL_SOURCE_BATCH_ALLOCATION: "BATCHALLOCATIONS.SERIALNUMBER",
    }
    return labels.get(serial_source, serial_source)


def _parse_tally_money(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().replace(",", "")
    if "/" in cleaned:
        cleaned = cleaned.split("/", 1)[0].strip()
    try:
        amount = abs(Decimal(cleaned))
    except InvalidOperation:
        return None
    return str(amount.quantize(Decimal("0.01")))


def _money_decimal(value: str | None) -> Decimal | None:
    parsed = _parse_tally_money(value)
    if parsed is None:
        return None
    return Decimal(parsed)


def _line_amount(line: ET.Element) -> str | None:
    """Sale value for one inventory line (AMOUNT preferred; RATE fallback)."""
    direct = _parse_tally_money(_child_text(line, "AMOUNT"))
    if direct:
        return direct
    rate = _parse_tally_money(_child_text(line, "RATE"))
    if rate:
        return rate
    amounts: list[Decimal] = []
    for child in line.iter():
        if _local_name(child.tag).upper() != "AMOUNT":
            continue
        # Prefer inventory-line amounts; skip deep ledger noise when possible.
        if child is not line and _local_name(child.tag).upper() == "AMOUNT":
            # ElementTree has no parent pointer; collect all and take max as last resort.
            parsed = _parse_tally_money(child.text)
            if parsed:
                amounts.append(Decimal(parsed))
    if not amounts:
        return None
    return str(max(amounts).quantize(Decimal("0.01")))


def resolve_inventory_line_sale_amount(
    line: TallyInventoryLine,
    voucher: TallyVoucher,
) -> float | None:
    """Line total from XML only — never estimate GST."""
    if line.line_total:
        return float(line.line_total)
    if line.amount:
        return float(line.amount)
    if len(voucher.inventory_lines) == 1 and voucher.amount:
        return float(voucher.amount)
    return None


def expand_inventory_lines(lines: list[TallyInventoryLine]) -> list[TallyInventoryLine]:
    """Split Tally lines that carry multiple serials into one sync row per serial."""
    expanded: list[TallyInventoryLine] = []
    for line in lines:
        serials = list(line.batch_allocations)
        if not serials and line.serial_number:
            serials = [line.serial_number]
        if len(serials) <= 1:
            expanded.append(
                TallyInventoryLine(
                    line_index=len(expanded),
                    stock_item_name=line.stock_item_name,
                    quantity=line.quantity,
                    serial_number=serials[0] if serials else line.serial_number,
                    batch_allocations=serials,
                    amount=line.amount,
                    rate=line.rate,
                    taxable_amount=line.taxable_amount,
                    cgst_amount=line.cgst_amount,
                    sgst_amount=line.sgst_amount,
                    igst_amount=line.igst_amount,
                    cess_amount=line.cess_amount,
                    line_total=line.line_total,
                    serial_source=line.serial_source,
                    normalized_serial=normalize_serial(
                        serials[0] if serials else line.serial_number
                    ),
                )
            )
            continue

        unit_amount: str | None = line.amount
        if line.amount:
            try:
                total = Decimal(line.amount)
                unit_amount = str((total / len(serials)).quantize(Decimal("0.01")))
            except (InvalidOperation, ZeroDivisionError):
                unit_amount = line.amount

        for serial in serials:
            expanded.append(
                TallyInventoryLine(
                    line_index=len(expanded),
                    stock_item_name=line.stock_item_name,
                    quantity="1",
                    serial_number=serial,
                    batch_allocations=[serial],
                    amount=unit_amount,
                    rate=line.rate,
                    taxable_amount=None,
                    cgst_amount=None,
                    sgst_amount=None,
                    igst_amount=None,
                    cess_amount=None,
                    line_total=unit_amount,
                    serial_source=line.serial_source,
                    normalized_serial=normalize_serial(serial),
                )
            )
    return expanded


def _parse_inventory_line(line: ET.Element, index: int) -> TallyInventoryLine:
    stock_item = _child_text(line, "STOCKITEMNAME") or ""
    quantity = _child_text(line, "ACTUALQTY") or _child_text(line, "BILLEDQTY") or "1"
    serial, serial_source, serials = _extract_serial_from_line(line)
    amount = _line_amount(line)
    rate = _parse_tally_money(_child_text(line, "RATE"))
    return TallyInventoryLine(
        line_index=index,
        stock_item_name=stock_item,
        quantity=quantity,
        serial_number=serial,
        batch_allocations=serials,
        amount=amount,
        rate=rate,
        taxable_amount=_parse_tally_money(_child_text(line, "TAXABLEAMOUNT")),
        cgst_amount=_parse_tally_money(_child_text(line, "CGSTAMOUNT")),
        sgst_amount=_parse_tally_money(_child_text(line, "SGSTAMOUNT")),
        igst_amount=_parse_tally_money(_child_text(line, "IGSTAMOUNT")),
        cess_amount=_parse_tally_money(_child_text(line, "CESSAMOUNT")),
        line_total=amount,
        serial_source=serial_source,
        normalized_serial=normalize_serial(serial),
    )


def _voucher_amount(voucher: ET.Element) -> str | None:
    amounts: list[Decimal] = []
    for child in voucher.iter():
        if _local_name(child.tag).upper() != "AMOUNT":
            continue
        text = (child.text or "").strip().replace(",", "")
        if not text:
            continue
        try:
            amounts.append(abs(Decimal(text)))
        except InvalidOperation:
            continue
    if not amounts:
        return None
    return str(max(amounts).quantize(Decimal("0.01")))


def _parse_voucher_totals(voucher: ET.Element, voucher_amount: str | None) -> TallyVoucherTotals:
    """Read tax/total fields from XML when present — never invent GST."""
    cgst = Decimal("0")
    sgst = Decimal("0")
    igst = Decimal("0")
    cess = Decimal("0")
    discount = Decimal("0")
    round_off = Decimal("0")
    found_tax = False

    for ledger in voucher.iter():
        tag = _local_name(ledger.tag).upper()
        if tag not in {"LEDGERENTRIES.LIST", "ALLLEDGERENTRIES.LIST"}:
            continue
        name = (_child_text(ledger, "LEDGERNAME") or "").upper()
        amount = _money_decimal(_child_text(ledger, "AMOUNT"))
        if amount is None:
            continue
        if "CGST" in name:
            cgst += amount
            found_tax = True
        elif "SGST" in name:
            sgst += amount
            found_tax = True
        elif "IGST" in name:
            igst += amount
            found_tax = True
        elif "CESS" in name:
            cess += amount
            found_tax = True
        elif "ROUND" in name:
            round_off += amount
        elif "DISCOUNT" in name:
            discount += amount

    grand = _money_decimal(voucher_amount)
    return TallyVoucherTotals(
        subtotal=None,
        discount_amount=discount if discount else None,
        round_off=round_off if round_off else None,
        cgst_amount=cgst if found_tax and cgst else None,
        sgst_amount=sgst if found_tax and sgst else None,
        igst_amount=igst if found_tax and igst else None,
        cess_amount=cess if found_tax and cess else None,
        grand_total=grand,
    )


def _printed_invoice_number(voucher: ET.Element, voucher_number: str) -> str:
    for candidate in (
        "REFERENCE",
        "REFERENCENUMBER",
        "BASICBUYERIDENTITY",
        "VOUCHERNUMBER",
    ):
        value = _child_text(voucher, candidate)
        if value:
            if candidate == "VOUCHERNUMBER" and _child_text(voucher, "REFERENCE"):
                continue
            return value
    return voucher_number


def _voucher_field(voucher: ET.Element, *names: str) -> str | None:
    """Read a voucher field from child elements or XML attributes (e.g. REMOTEID)."""
    for name in names:
        value = _child_text(voucher, name)
        if value:
            return value
        for attr in (name, name.upper(), name.lower()):
            raw = voucher.get(attr)
            if raw and str(raw).strip():
                return str(raw).strip()
    return None


def parse_voucher_element(
    voucher: ET.Element, *, raw_xml: str | None = None
) -> TallyVoucher | None:
    guid = _voucher_field(voucher, "GUID", "REMOTEID")
    voucher_number = _voucher_field(voucher, "VOUCHERNUMBER")
    voucher_type = _voucher_field(voucher, "VOUCHERTYPENAME", "VCHTYPE")
    if not guid or not voucher_type:
        return None
    if not voucher_number:
        voucher_number = guid

    inventory_lines: list[TallyInventoryLine] = []
    line_index = 0
    for child in voucher:
        tag = _local_name(child.tag).upper()
        if tag == "ALLINVENTORYENTRIES.LIST" or tag == "INVENTORYENTRIES.LIST":
            inventory_lines.append(_parse_inventory_line(child, line_index))
            line_index += 1

    if not inventory_lines:
        for child in voucher.iter():
            tag = _local_name(child.tag).upper()
            if (
                tag in {"ALLINVENTORYENTRIES.LIST", "INVENTORYENTRIES.LIST"}
                and child is not voucher
            ):
                inventory_lines.append(_parse_inventory_line(child, line_index))
                line_index += 1

    amount = _voucher_amount(voucher)
    return TallyVoucher(
        guid=guid,
        master_id=_child_text(voucher, "MASTERID"),
        voucher_type=voucher_type.strip(),
        voucher_number=voucher_number.strip(),
        printed_invoice_number=_printed_invoice_number(voucher, voucher_number.strip()),
        voucher_date=_parse_tally_date(_child_text(voucher, "DATE")),
        party_name=_child_text(voucher, "PARTYLEDGERNAME"),
        narration=_child_text(voucher, "NARRATION"),
        inventory_lines=inventory_lines,
        payment_mode=_child_text(voucher, "BASICPAYMENTTYPE")
        or _child_text(voucher, "PAYMENTMODE"),
        amount=amount,
        totals=_parse_voucher_totals(voucher, amount),
        raw_xml=raw_xml,
    )


def parse_vouchers_xml(xml_text: str) -> list[TallyVoucher]:
    cleaned = _sanitize_xml_text(xml_text)
    if not cleaned:
        return []
    try:
        root = ET.fromstring(cleaned)
    except ET.ParseError:
        return []

    vouchers: list[TallyVoucher] = []
    seen_guids: set[str] = set()
    for element in root.iter():
        if _local_name(element.tag).upper() != "VOUCHER":
            continue
        # Preserve per-voucher XML fragment for archive when possible.
        try:
            fragment = ET.tostring(element, encoding="unicode")
        except Exception:  # noqa: BLE001
            fragment = cleaned
        parsed = parse_voucher_element(element, raw_xml=fragment)
        if parsed is None or parsed.guid in seen_guids:
            continue
        seen_guids.add(parsed.guid)
        vouchers.append(parsed)
    return vouchers


def _voucher_detail_richness(voucher: TallyVoucher) -> tuple[int, int, int]:
    """Prefer vouchers with more batch serials, then more lines, then raw XML."""
    batch_serials = sum(len(line.batch_allocations) for line in voucher.inventory_lines)
    return (batch_serials, len(voucher.inventory_lines), 1 if voucher.raw_xml else 0)


def merge_vouchers_by_guid(vouchers: list[TallyVoucher]) -> list[TallyVoucher]:
    """Collapse duplicate GUIDs from multiple export sources (Day Book + Register)."""
    merged: dict[str, TallyVoucher] = {}
    for voucher in vouchers:
        current = merged.get(voucher.guid)
        if current is None or _voucher_detail_richness(voucher) > _voucher_detail_richness(current):
            merged[voucher.guid] = voucher
    return list(merged.values())


def catalog_model_matches_invoice(ims_catalog_label: str, invoice_stock_item: str) -> bool:
    """
    Strict verification helper for Case A/B — NOT used to select inventory.

    Match when normalized strings are equal, or IMS model number token appears
    as a contiguous substring in the invoice stock item name.
    """
    left = re.sub(r"\s+", " ", (ims_catalog_label or "").strip().upper())
    right = re.sub(r"\s+", " ", (invoice_stock_item or "").strip().upper())
    if not left or not right:
        return False
    if left == right:
        return True
    # Prefer model-number style tokens (contain digits).
    for token in left.replace("(", " ").replace(")", " ").split():
        if any(ch.isdigit() for ch in token) and len(token) >= 5 and token in right:
            return True
    return False
