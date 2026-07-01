"""Background loop that purges audit logs past the retention window."""

from __future__ import annotations

import asyncio

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.database.session import session_scope
from webstudio_backend.services.audit_retention_service import AuditRetentionService, audit_retention_days


async def maybe_purge_audit_logs() -> None:
    settings = get_settings()
    if settings.is_test:
        return
    async with session_scope() as session:
        deleted = await AuditRetentionService(session).purge_expired()
        if deleted:
            await session.commit()


async def audit_retention_loop() -> None:
    while True:
        try:
            await maybe_purge_audit_logs()
        except Exception:
            pass
        await asyncio.sleep(86_400)
