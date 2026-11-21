"""Tally voucher XML parser — deterministic serial extraction (no fuzzy matching)."""

from __future__ import annotations

import gzip
import re
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from webstudio_backend.integrations.tally.constants import (
    MONITORED_VOUCHER_TYPES,
    PURCHASE_VOUCHER_TYPES,
)
from webstudio_backend.integrations.tally.gst import reconcile_invoice_lines, split_inventory_line
from webstudio_backend.integrations.tally.quantity import parse_tally_quantity
from webstudio_backend.integrations.tally.types import (
    TallyInventoryLine,
    TallyVoucher,
    TallyVoucherTotals,
)

SERIAL_SOURCE_BASICUSERDESCRIPTION = "basicuserdescription"
SERIAL_SOURCE_SERIALNUMBER = "serialnumber"
SERIAL_SOURCE_BATCH_ALLOCATION = "batch_allocations.serialnumber"
_INVALID_XML_CONTROLS = set(range(32)) - {9, 10, 13}


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
    cleaned = re.sub(
        r"&#(?:(\d+)|x([0-9a-fA-F]+));",
        lambda match: (
            ""
            if int(match[1] or match[2], 10 if match[1] else 16) in _INVALID_XML_CONTROLS
            else match[0]
        ),
        cleaned,
    )
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


def _purchase_serials(fields: list[ET.Element], *, free_text: bool = False) -> list[str]:
    serials: dict[str, str] = {}
    for field in fields:
        for part in re.split(r"[,;\r\n\t]+", field.text or ""):
            serial = part.strip()
            if not serial or "warranty" in serial.lower():
                continue
            if free_text and not (
                re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{6,}[A-Za-z0-9]", serial)
                and any(char.isdigit() for char in serial)
            ):
                continue
            serials.setdefault(serial.upper(), serial)
    return list(serials.values())


def _extract_purchase_serials(
    line: ET.Element, quantity: int
) -> tuple[str | None, str | None, list[str]]:
    batches = [
        field
        for batch in _children_by_name(line, "BATCHALLOCATIONS.LIST")
        for field in batch.iter()
        if _local_name(field.tag).upper() == "SERIALNUMBER"
    ]
    direct = _children_by_name(line, "SERIALNUMBER") + [
        field
        for serial_list in _children_by_name(line, "SERIALNUMBER.LIST")
        for field in _children_by_name(serial_list, "SERIALNUMBER")
    ]
    descriptions = _children_by_name(line, "BASICUSERDESCRIPTION") + [
        field
        for desc_list in _children_by_name(line, "BASICUSERDESCRIPTION.LIST")
        for field in _children_by_name(desc_list, "BASICUSERDESCRIPTION")
    ]
    sources = (
        (SERIAL_SOURCE_BATCH_ALLOCATION, _purchase_serials(batches)),
        (SERIAL_SOURCE_SERIALNUMBER, _purchase_serials(direct)),
        (SERIAL_SOURCE_BASICUSERDESCRIPTION, _purchase_serials(descriptions, free_text=True)),
    )
    source, serials = next((entry for entry in sources if entry[1]), (None, []))
    if not serials:
        return None, None, []

    # Preserve explicit serials and fill gaps only when the combined candidates
    # fit the billed quantity. A full explicit list takes priority over remarks.
    for _, candidates in sources:
        if len(serials) >= quantity:
            break
        seen = {serial.upper() for serial in serials}
        extra = [serial for serial in candidates if serial.upper() not in seen]
        if len(serials) + len(extra) <= quantity:
            serials.extend(extra)
    return serials[0], source, serials


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


def _parse_tally_money(value: str | None, *, signed: bool = False) -> str | None:
    if not value:
        return None
    cleaned = value.strip().replace(",", "")
    if "/" in cleaned:
        cleaned = cleaned.split("/", 1)[0].strip()
    try:
        amount = Decimal(cleaned)
        if not amount.is_finite():
            return None
        return str((amount if signed else abs(amount)).quantize(Decimal("0.01")))
    except InvalidOperation:
        return None


def _money_decimal(value: str | None) -> Decimal | None:
    parsed = _parse_tally_money(value)
    if parsed is None:
        return None
    return Decimal(parsed)


def _line_amount(line: ET.Element, *, rate_quantity: int = 1) -> str | None:
    """Sale value for one inventory line (AMOUNT preferred; RATE fallback)."""
    direct = _parse_tally_money(_child_text(line, "AMOUNT"))
    if direct:
        return direct
    rate = _parse_tally_money(_child_text(line, "RATE"))
    if rate:
        return str(Decimal(rate) * rate_quantity)
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
        unit_lines = [line]
        if len(serials) > 1:
            count = max(len(serials), parse_tally_quantity(line.quantity))
            unit_lines = split_inventory_line(line, count, limit=len(serials))
        for unit, serial in zip(unit_lines, serials or [line.serial_number], strict=True):
            expanded.append(
                replace(
                    unit,
                    line_index=len(expanded),
                    serial_number=serial,
                    batch_allocations=[serial] if serial else [],
                    normalized_serial=normalize_serial(serial),
                )
            )
    return expanded


def _parse_inventory_line(
    line: ET.Element, index: int, *, purchase: bool = False, sale: bool = False
) -> TallyInventoryLine:
    stock_item = _child_text(line, "STOCKITEMNAME") or ""
    quantity = _child_text(line, "ACTUALQTY") or _child_text(line, "BILLEDQTY") or "1"
    serial, serial_source, serials = (
        _extract_purchase_serials(line, parse_tally_quantity(quantity, default=1))
        if purchase
        else _extract_serial_from_line(line)
    )
    rate_quantity = parse_tally_quantity(quantity, default=1) if sale else 1
    amount = _line_amount(line, rate_quantity=rate_quantity)
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
        gst_rates=_line_gst_rates(line) if sale else {},
    )


_GST_DUTY_FIELDS = {
    "CGST": "cgst_amount",
    "SGST": "sgst_amount",
    "SGST/UTGST": "sgst_amount",
    "UTGST": "sgst_amount",
    "IGST": "igst_amount",
    "CESS": "cess_amount",
}


def _line_gst_rates(line: ET.Element) -> dict[str, Decimal]:
    rates: dict[str, Decimal] = {}
    for entry in _children_by_name(line, "RATEDETAILS.LIST"):
        field = _GST_DUTY_FIELDS.get((_child_text(entry, "GSTRATEDUTYHEAD") or "").upper())
        valuation = (_child_text(entry, "GSTRATEVALUATIONTYPE") or "").casefold()
        if field and valuation in {"", "based on value"}:
            rate = _money_decimal(_child_text(entry, "GSTRATE"))
            if rate is not None:
                rates[field] = rate
    return rates


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


_LEDGER_TAGS = {"LEDGERENTRIES.LIST", "ALLLEDGERENTRIES.LIST"}


def _sale_party_amount(voucher: ET.Element, ledgers: list[ET.Element]) -> Decimal | None:
    party = (_child_text(voucher, "PARTYLEDGERNAME") or "").casefold()
    amounts: set[Decimal] = set()
    unnamed: list[Decimal] = []
    for ledger in ledgers:
        raw = _parse_tally_money(_child_text(ledger, "AMOUNT"), signed=True)
        if raw is None:
            continue
        name = (_child_text(ledger, "LEDGERNAME") or "").casefold()
        marked_party = (_child_text(ledger, "ISPARTYLEDGER") or "").casefold() == "yes"
        if marked_party or (party and name == party):
            amounts.add(Decimal(raw))
        elif not name:
            unnamed.append(Decimal(raw))
    if len(amounts) == 1:
        return next(iter(amounts))
    direct = _parse_tally_money(_child_text(voucher, "AMOUNT"), signed=True)
    if direct is not None:
        return Decimal(direct)
    # Some exports omit the party ledger's name and marker.
    return unnamed[0] if len(unnamed) == 1 and not amounts else None


def _parse_voucher_totals(
    voucher: ET.Element, voucher_amount: str | None, *, sale: bool = False
) -> TallyVoucherTotals:
    """Read tax/total fields from XML when present — never invent GST."""
    cgst = Decimal("0")
    sgst = Decimal("0")
    igst = Decimal("0")
    cess = Decimal("0")
    discount = Decimal("0")
    round_off = Decimal("0")
    found_tax = False

    ledgers = [
        entry
        for entry in (voucher if sale else voucher.iter())
        if _local_name(entry.tag).upper() in _LEDGER_TAGS
    ]
    party_amount = _sale_party_amount(voucher, ledgers) if sale else None
    for ledger in ledgers:
        if sale and (
            (_child_text(ledger, "ISPARTYLEDGER") or "").casefold() == "yes"
            or (_child_text(ledger, "LEDGERNAME") or "").casefold()
            == (_child_text(voucher, "PARTYLEDGERNAME") or "").casefold()
        ):
            continue
        name = (_child_text(ledger, "LEDGERNAME") or "").upper()
        amount = _money_decimal(_child_text(ledger, "AMOUNT"))
        if amount is None:
            continue
        if "CGST" in name:
            cgst += amount
            found_tax = True
        elif "SGST" in name or (sale and "UTGST" in name):
            sgst += amount
            found_tax = True
        elif "IGST" in name:
            igst += amount
            found_tax = True
        elif "CESS" in name:
            cess += amount
            found_tax = True
        elif "ROUND" in name:
            if sale:
                raw_round = _parse_tally_money(_child_text(ledger, "AMOUNT"), signed=True)
                if raw_round is not None:
                    round_off += Decimal(raw_round) * (
                        -1 if party_amount and party_amount > 0 else 1
                    )
            else:
                round_off += amount
        elif "DISCOUNT" in name:
            discount += amount

    grand = (
        (abs(party_amount) if party_amount is not None else None)
        if sale
        else _money_decimal(voucher_amount)
    )
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
    voucher_type = _voucher_field(voucher, "VOUCHERTYPENAME", "VCHTYPE") or ""
    purchase = voucher_type.strip() in PURCHASE_VOUCHER_TYPES
    sale = voucher_type.strip() in MONITORED_VOUCHER_TYPES
    if not guid:
        return None
    if not voucher_number:
        voucher_number = guid

    inventory_lines: list[TallyInventoryLine] = []
    line_index = 0
    for child in voucher:
        tag = _local_name(child.tag).upper()
        if tag == "ALLINVENTORYENTRIES.LIST" or tag == "INVENTORYENTRIES.LIST":
            inventory_lines.append(
                _parse_inventory_line(child, line_index, purchase=purchase, sale=sale)
            )
            line_index += 1

    if not inventory_lines:
        for child in voucher.iter():
            tag = _local_name(child.tag).upper()
            if (
                tag in {"ALLINVENTORYENTRIES.LIST", "INVENTORYENTRIES.LIST"}
                and child is not voucher
            ):
                inventory_lines.append(
                    _parse_inventory_line(child, line_index, purchase=purchase, sale=sale)
                )
                line_index += 1

    amount = _voucher_amount(voucher)
    parsed = TallyVoucher(
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
        totals=_parse_voucher_totals(voucher, amount, sale=sale),
        raw_xml=raw_xml,
    )
    if not sale:
        return parsed
    priced_lines, priced_totals = reconcile_invoice_lines(inventory_lines, parsed.totals)
    return replace(
        parsed,
        inventory_lines=priced_lines,
        totals=priced_totals,
        amount=str(priced_totals.grand_total) if priced_totals.grand_total is not None else amount,
    )


class TallyXmlTruncatedError(Exception):
    """Raised (strict mode only) when a Tally export response is malformed —
    almost always a response cut off mid-stream on a large historical export.

    A genuinely empty result is well-formed XML with zero VOUCHER elements and
    never raises this; only a parse failure does.
    """


def parse_vouchers_xml(xml_text: str, *, strict: bool = False) -> list[TallyVoucher]:
    cleaned = _sanitize_xml_text(xml_text)
    if not cleaned:
        return []
    try:
        root = ET.fromstring(cleaned)
    except ET.ParseError as exc:
        if strict:
            raise TallyXmlTruncatedError(
                "Tally export response could not be parsed — likely truncated"
            ) from exc
        return []

    vouchers: dict[str, TallyVoucher] = {}
    for element in root.iter():
        if _local_name(element.tag).upper() != "VOUCHER":
            continue
        # Preserve per-voucher XML fragment for archive when possible.
        try:
            fragment = ET.tostring(element, encoding="unicode")
        except Exception:  # noqa: BLE001
            fragment = cleaned
        parsed = parse_voucher_element(element, raw_xml=fragment)
        if parsed is None:
            continue
        current = vouchers.get(parsed.guid)
        if current is None or (
            parsed.voucher_type in PURCHASE_VOUCHER_TYPES
            and _voucher_detail_richness(parsed) > _voucher_detail_richness(current)
        ):
            vouchers[parsed.guid] = parsed
    return list(vouchers.values())


def read_archived_voucher(compressed: bytes | None, guid: str) -> TallyVoucher | None:
    if compressed:
        try:
            vouchers = parse_vouchers_xml(gzip.decompress(compressed).decode("utf-8"))
        except (OSError, EOFError, UnicodeError, ValueError):
            return None
        return next((voucher for voucher in vouchers if voucher.guid == guid), None)
    return None


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
