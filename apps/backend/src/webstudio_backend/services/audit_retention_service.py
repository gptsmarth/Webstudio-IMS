"""Automatic purge of audit logs older than the retention window."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.audit_log import AuditLog

DEFAULT_AUDIT_RETENTION_DAYS = 45


def audit_retention_days() -> int:
    raw = os.getenv("WEBSTUDIO_AUDIT_RETENTION_DAYS", str(DEFAULT_AUDIT_RETENTION_DAYS))
    try:
        days = int(raw)
    except ValueError:
        days = DEFAULT_AUDIT_RETENTION_DAYS
    return max(1, days)


class AuditRetentionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def purge_expired(self, *, retention_days: int | None = None) -> int:
        days = retention_days if retention_days is not None else audit_retention_days()
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self._session.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        return int(result.rowcount or 0)
