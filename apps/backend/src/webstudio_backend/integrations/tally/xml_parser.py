"""Tally voucher XML parser."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from webstudio_backend.integrations.tally.types import TallyInventoryLine, TallyVoucher


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


def _extract_serials_from_line(line: ET.Element) -> list[str]:
    serials: list[str] = []
    for batch in line.iter():
        if _local_name(batch.tag).upper() == "SERIALNUMBER":
            text = (batch.text or "").strip()
            if text:
                serials.append(text)
    direct = _child_text(line, "SERIALNUMBER")
    if direct:
        serials.append(direct)
    for desc_list in _children_by_name(line, "BASICUSERDESCRIPTION.LIST"):
        for item in _children_by_name(desc_list, "BASICUSERDESCRIPTION"):
            text = (item.text or "").strip()
            if text and re.match(r"^[A-Z0-9]{8,}$", text, re.I):
                serials.append(text.upper())
    return list(dict.fromkeys(serials))


def _parse_inventory_line(line: ET.Element, index: int) -> TallyInventoryLine:
    stock_item = _child_text(line, "STOCKITEMNAME") or ""
    quantity = _child_text(line, "ACTUALQTY") or _child_text(line, "BILLEDQTY") or "1"
    serials = _extract_serials_from_line(line)
    return TallyInventoryLine(
        line_index=index,
        stock_item_name=stock_item,
        quantity=quantity,
        serial_number=serials[0] if serials else None,
        batch_allocations=serials,
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


def parse_voucher_element(voucher: ET.Element) -> TallyVoucher | None:
    guid = _child_text(voucher, "GUID")
    voucher_number = _child_text(voucher, "VOUCHERNUMBER")
    voucher_type = _child_text(voucher, "VOUCHERTYPENAME")
    if not guid or not voucher_number or not voucher_type:
        return None

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
        amount=_voucher_amount(voucher),
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
        parsed = parse_voucher_element(element)
        if parsed is None or parsed.guid in seen_guids:
            continue
        seen_guids.add(parsed.guid)
        vouchers.append(parsed)
    return vouchers


def normalize_model_name(value: str) -> str:
    text = re.sub(r"[^\w\s-]", " ", value.upper())
    text = re.sub(r"\s+", " ", text).strip()
    for prefix in ("VIVOBOOK", "INSPIRON", "PAVILION", "IDEAPAD", "THINKPAD", "NOTEBOOK", "LAPTOP"):
        text = re.sub(rf"\b{prefix}\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_model_tokens(value: str) -> set[str]:
    normalized = normalize_model_name(value)
    tokens = {token for token in normalized.split() if len(token) >= 4}
    compact = re.sub(r"[^A-Z0-9]", "", normalized)
    if len(compact) >= 6:
        tokens.add(compact)
    return tokens


def models_equivalent(inventory_model: str, invoice_model: str) -> bool:
    inv_tokens = extract_model_tokens(inventory_model)
    inv_tokens.update(extract_model_tokens(invoice_model))
    left = extract_model_tokens(inventory_model)
    right = extract_model_tokens(invoice_model)
    if not left or not right:
        return normalize_model_name(inventory_model) == normalize_model_name(invoice_model)
    return bool(left & right)
