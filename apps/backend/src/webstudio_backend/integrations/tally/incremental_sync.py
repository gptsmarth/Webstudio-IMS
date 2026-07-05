"""Incremental Tally synchronization helpers — date windows and duplicate fingerprints."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from webstudio_backend.infrastructure.database.models.tally_company_sync import TallyCompanySync

SYNC_INTERVAL_DEFAULT_SECONDS = 300
SYNC_INTERVAL_MIN_SECONDS = 60
SYNC_INTERVAL_MAX_SECONDS = 3600
REPEATED_FAILURE_NOTIFICATION_THRESHOLD = 3
INITIAL_SYNC_LOOKBACK_DAYS = 30
STALE_SYNC_IN_PROGRESS_SECONDS = 600


def clamp_sync_interval_seconds(raw: int) -> int:
    return max(SYNC_INTERVAL_MIN_SECONDS, min(SYNC_INTERVAL_MAX_SECONDS, raw))


def resolve_incremental_from_date(
    company_sync: TallyCompanySync, *, today: date | None = None
) -> date:
    """Request Tally exports from the last imported voucher date, with lookback when none yet."""
    reference = today or datetime.now(UTC).date()
    lookback_start = reference - timedelta(days=INITIAL_SYNC_LOOKBACK_DAYS)

    if company_sync.last_imported_voucher_date is not None:
        return company_sync.last_imported_voucher_date

    if company_sync.last_successful_sync_at is not None:
        sync_date = company_sync.last_successful_sync_at.date()
        # Sync ran but never imported — widen the window instead of same-day-only exports.
        return min(sync_date, lookback_start)

    return lookback_start


def normalize_party_name(value: str | None) -> str:
    return (value or "").strip().casefold()


def normalize_voucher_amount(value: str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    try:
        if isinstance(value, Decimal):
            return value.quantize(Decimal("0.01"))
        cleaned = str(value).strip().replace(",", "")
        if not cleaned:
            return None
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def build_fallback_fingerprint(
    *,
    voucher_date: date,
    voucher_number: str,
    amount: str | Decimal | None,
    party_name: str | None,
) -> tuple[date, str, Decimal | None, str]:
    normalized_amount = normalize_voucher_amount(amount)
    return (
        voucher_date,
        voucher_number.strip(),
        normalized_amount,
        normalize_party_name(party_name),
    )
