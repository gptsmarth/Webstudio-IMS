"""Backup schedule helpers — retention and next-run calculation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def compute_next_scheduled_backup(
    schedule: str,
    *,
    last_backup_at: datetime | None,
    now: datetime | None = None,
) -> datetime | None:
    if schedule == "manual":
        return None
    reference = now or datetime.now(UTC)
    base = last_backup_at or reference
    if schedule == "daily":
        return base + timedelta(days=1)
    if schedule == "weekly":
        return base + timedelta(weeks=1)
    if schedule == "monthly":
        return base + timedelta(days=30)
    return None


def backup_health_status(
    *,
    database_health: str,
    last_verification_status: str | None,
    storage_free_bytes: int,
) -> str:
    if database_health != "ok":
        return "degraded"
    if storage_free_bytes < 512 * 1024 * 1024:
        return "warning"
    if last_verification_status in {"failed", None}:
        return "warning"
    if last_verification_status == "warning":
        return "warning"
    return "healthy"


RETENTION_POLICIES = frozenset({"last_7", "last_30", "last_90", "unlimited", "custom"})


def resolve_retention_limit(policy: str, custom_count: int) -> int | None:
    if policy == "unlimited":
        return None
    if policy == "custom":
        return max(custom_count, 1)
    mapping = {"last_7": 7, "last_30": 30, "last_90": 90}
    return mapping.get(policy, 30)


OLD_BACKUP_THRESHOLD_DAYS = 7
LOW_STORAGE_BYTES = 512 * 1024 * 1024
STORAGE_WARNING_BYTES = LOW_STORAGE_BYTES
STORAGE_CRITICAL_BYTES = 128 * 1024 * 1024


def compute_recovery_readiness(
    *,
    database_health: str,
    backup_health: str,
    has_recent_backup: bool,
    failed_backup_count: int,
    open_health_issues: int,
) -> str:
    if database_health != "ok":
        return "not_ready"
    if failed_backup_count > 0 or open_health_issues > 2:
        return "not_ready"
    if backup_health == "degraded" or not has_recent_backup:
        return "partial"
    if backup_health == "warning" or open_health_issues > 0:
        return "partial"
    return "ready"


def compute_system_health(
    *,
    database_health: str,
    backup_health: str,
    open_critical_issues: int,
    open_warning_issues: int,
) -> str:
    if database_health != "ok" or open_critical_issues > 0:
        return "critical"
    if backup_health == "degraded":
        return "degraded"
    if backup_health == "warning" or open_warning_issues > 0:
        return "warning"
    return "healthy"


def estimate_remaining_backups(
    *,
    storage_free_bytes: int,
    average_backup_bytes: int,
    retention_count: int | None,
) -> int | None:
    if average_backup_bytes <= 0:
        return None
    capacity = max(storage_free_bytes // average_backup_bytes, 0)
    if retention_count is None:
        return int(capacity)
    return int(min(capacity, retention_count))


def compute_readiness_score(
    *,
    database_health: str,
    backup_health: str,
    storage_status: str,
    latest_backup_age_days: float | None,
    latest_verification_status: str | None,
    recovery_readiness: str,
) -> dict[str, int | str]:
    database_score = 100 if database_health == "ok" else 0
    backup_age_score = 100
    if latest_backup_age_days is None:
        backup_age_score = 0
    elif latest_backup_age_days > OLD_BACKUP_THRESHOLD_DAYS:
        backup_age_score = 40
    elif latest_backup_age_days > 1:
        backup_age_score = 75
    verification_score = 100
    if latest_verification_status in {None, "failed"}:
        verification_score = 0
    elif latest_verification_status == "warning":
        verification_score = 60
    storage_score = 100
    if storage_status == "warning":
        storage_score = 55
    elif storage_status == "critical":
        storage_score = 15
    recovery_score = {"ready": 100, "partial": 60, "not_ready": 20}.get(recovery_readiness, 50)
    overall = int(
        (database_score * 0.25)
        + (backup_age_score * 0.2)
        + (verification_score * 0.2)
        + (storage_score * 0.15)
        + (recovery_score * 0.2),
    )
    return {
        "overall_score": overall,
        "database_health_score": database_score,
        "latest_backup_age_score": backup_age_score,
        "backup_verification_score": verification_score,
        "storage_health_score": storage_score,
        "recovery_status_score": recovery_score,
        "overall_readiness": recovery_readiness,
    }
