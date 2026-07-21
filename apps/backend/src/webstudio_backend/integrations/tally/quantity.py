"""Parse Tally quantity strings such as ``4 Nos`` or ``1.00 Nos``."""

from __future__ import annotations


def parse_tally_quantity(raw: str | None, *, default: int = 0) -> int:
    """Leading integer quantity from a Tally qty string (e.g. ``'5 Nos'`` → 5)."""
    if not raw:
        return default
    digits = ""
    for char in raw.strip():
        if char.isdigit():
            digits += char
        elif char in {".", ","} and digits:
            break
        elif digits:
            break
    if not digits:
        return default
    try:
        value = int(digits)
    except ValueError:
        return default
    return value if value > 0 else default
