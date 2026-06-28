"""Tally ERP 9 integration constants."""

from __future__ import annotations

MONITORED_VOUCHER_TYPES: tuple[str, ...] = ("Sales", "NEW SALE")

VOUCHER_TYPE_STORE_MAP: dict[str, str] = {
    "Sales": "WEBSTUDIO",
    "NEW SALE": "AES",
}

DEFAULT_SYNC_INTERVAL_SECONDS = 1800
