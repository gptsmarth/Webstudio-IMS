"""Discovery metadata for LAN clients — no secrets exposed."""

from __future__ import annotations

import shutil

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.platform_info_service import resolve_build_version


async def build_discovery_health_payload(
    session: AsyncSession,
    settings: Settings,
) -> dict[str, object]:
    repo = SystemSettingRepository(session)
    company_name = (await repo.get_string("company_name") or "").strip()
    database_status = "unknown"
    try:
        await session.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:
        database_status = "failed"

    disk_status = "unknown"
    try:
        usage = shutil.disk_usage("/")
        free_ratio = usage.free / usage.total if usage.total else 0
        disk_status = "ok" if free_ratio >= 0.05 else "low"
    except Exception:
        disk_status = "unknown"

    online = database_status == "ok"
    return {
        "online": online,
        "server_name": settings.mdns_server_name or None,
        "company_name": company_name or None,
        "backend_version": settings.app_version,
        "api_version": settings.api_version,
        "build_version": resolve_build_version(settings),
        "environment": settings.app_env,
        "backend_port": settings.api_port,
        "database_status": database_status,
        "disk_status": disk_status,
        "discovery_protocol": "mdns",
        "service_type": "_webstudio-ims._tcp.local.",
    }
