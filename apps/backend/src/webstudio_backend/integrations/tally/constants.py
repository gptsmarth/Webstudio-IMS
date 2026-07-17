"""Tally ERP 9 integration constants."""

from __future__ import annotations

MONITORED_VOUCHER_TYPES: tuple[str, ...] = ("Sales", "NEW SALE")

VOUCHER_TYPE_STORE_MAP: dict[str, str] = {
    "Sales": "WEBSTUDIO",
    "NEW SALE": "AES",
}

# Purchase Import Module (additive). These vouchers are projected into the
# Purchase Import Queue for manual review — they NEVER auto-create inventory and
# are NOT part of the Sales sync watermark / MONITORED_VOUCHER_TYPES pipeline.
# "NEW PURCHASE" is included for forward-compatibility as requested.
PURCHASE_VOUCHER_TYPES: tuple[str, ...] = ("Purchase", "NEW PURCHASE")

DEFAULT_SYNC_INTERVAL_SECONDS = 300
