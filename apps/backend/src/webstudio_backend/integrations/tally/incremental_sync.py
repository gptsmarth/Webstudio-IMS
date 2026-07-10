"""Incremental Tally synchronization helpers — date windows and duplicate fingerprints."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from webstudio_backend.infrastructure.database.models.tally_company_sync import TallyCompanySync
from webstudio_backend.integrations.tally.types import TallyVoucher

SYNC_INTERVAL_DEFAULT_SECONDS = 300
SYNC_INTERVAL_MIN_SECONDS = 60
SYNC_INTERVAL_MAX_SECONDS = 3600
REPEATED_FAILURE_NOTIFICATION_THRESHOLD = 3
INITIAL_SYNC_LOOKBACK_DAYS = 30
STALE_SYNC_IN_PROGRESS_SECONDS = 600


def clamp_sync_interval_seconds(raw: int) -> int:
    return max(SYNC_INTERVAL_MIN_SECONDS, min(SYNC_INTERVAL_MAX_SECONDS, raw))


def tally_sync_had_meaningful_progress(
    *,
    invoices_imported: int,
    sales_created: int,
) -> bool:
    """Return True when a sync run imported at least one bill or applied at least one sale."""
    return invoices_imported > 0 or sales_created > 0


def resolve_incremental_from_date(
    company_sync: TallyCompanySync, *, today: date | None = None
) -> date:
    """
    Restart-safe incremental window start.

    After power failure / Windows restart / scheduler restart:
      From = last_imported_voucher_date (preferred)
      To   = current date (caller)
    Duplicate GUIDs are filtered later — overnight invoices are never skipped.
    """
    reference = today or datetime.now(UTC).date()
    lookback_start = reference - timedelta(days=INITIAL_SYNC_LOOKBACK_DAYS)

    if company_sync.last_imported_voucher_date is not None:
        return company_sync.last_imported_voucher_date

    if company_sync.last_successful_sync_at is not None:
        sync_date = company_sync.last_successful_sync_at.date()
        # Sync ran but never imported — widen the window instead of same-day-only exports.
        return min(sync_date, lookback_start)

    return lookback_start


@dataclass(frozen=True, slots=True)
class GuidWatermarkPartition:
    """Result of partitioning a chronological voucher list by GUID watermark.

    Does not reduce XML downloaded from Tally. It only avoids full matching /
    inventory work for vouchers at or before the last successfully processed GUID.

    GUID remains the sole synchronization identity — this is an efficiency cursor.
    """

    to_process: tuple[TallyVoucher, ...]
    historical_skipped: int
    watermark_found: bool
    watermark_guid: str | None


def partition_by_guid_watermark(
    vouchers: Sequence[TallyVoucher],
    last_processed_guid: str | None,
) -> GuidWatermarkPartition:
    """
    Fast-skip vouchers at/before the stored GUID watermark.

    Preconditions:
      - ``vouchers`` are already sorted chronologically (date, then GUID).
      - Watermark GUID was persisted only after successful processing.

    Behaviour:
      - No watermark → process all (safe; GUID idempotency still applies).
      - Watermark found at index i → skip 0..i inclusive; process i+1..
      - Watermark missing from batch → process all (safe fallback).
    """
    watermark = (last_processed_guid or "").strip()
    if not watermark:
        return GuidWatermarkPartition(
            to_process=tuple(vouchers),
            historical_skipped=0,
            watermark_found=False,
            watermark_guid=None,
        )

    for index, voucher in enumerate(vouchers):
        if (voucher.guid or "").strip() == watermark:
            return GuidWatermarkPartition(
                to_process=tuple(vouchers[index + 1 :]),
                historical_skipped=index + 1,
                watermark_found=True,
                watermark_guid=watermark,
            )

    return GuidWatermarkPartition(
        to_process=tuple(vouchers),
        historical_skipped=0,
        watermark_found=False,
        watermark_guid=watermark,
    )


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
