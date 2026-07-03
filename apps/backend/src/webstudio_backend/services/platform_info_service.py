"""Platform version and capabilities discovery."""

from __future__ import annotations

import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.ai.config import resolve_ai_config
from webstudio_backend.services.tally_sync_service import TallySyncService


async def resolve_schema_version(session: AsyncSession) -> str:
    try:
        result = await session.execute(text("SELECT version_num FROM webstudio.alembic_version"))
        value = result.scalar_one_or_none()
        return str(value or "unknown")
    except Exception:
        return "unknown"


def resolve_build_version(settings: Settings) -> str:
    return (
        os.getenv("WEBSTUDIO_BUILD_VERSION", "").strip()
        or os.getenv("WEBSTUDIO_GIT_COMMIT", "").strip()
        or settings.build_version.strip()
        or settings.app_version
    )


async def build_version_payload(session: AsyncSession, settings: Settings) -> dict[str, object]:
    from webstudio_backend.services.enterprise_version_service import EnterpriseVersionService

    version_identity = await EnterpriseVersionService(session, settings).build_version_identity()
    schema_version = str(version_identity["database_revision"])
    repo = SystemSettingRepository(session)
    latest_mobile = (
        await repo.get_string("mobile_latest_version") or settings.app_version
    ).strip()
    release_date = (await repo.get_string("mobile_release_date") or "").strip()
    release_notes = (await repo.get_string("mobile_release_notes") or "").strip()
    apk_url = (await repo.get_string("mobile_apk_download_url") or "").strip()
    channel_raw = (await repo.get_string("mobile_release_channel") or "stable").strip().lower()
    release_channel = channel_raw if channel_raw in {"stable", "beta"} else "stable"
    min_mobile = (settings.min_mobile_version or settings.min_client_version).strip()

    return {
        "version": version_identity["version"],
        "build_number": version_identity["build_number"],
        "git_commit": version_identity["git_commit"],
        "git_short": version_identity["git_short"],
        "release_date": version_identity["release_date"],
        "release_channel": version_identity["release_channel"],
        "database_revision": version_identity["database_revision"],
        "version_identity": version_identity,
        "backend_version": version_identity["version"],
        "schema_version": schema_version,
        "api_version": settings.api_version,
        "build_version": resolve_build_version(settings),
        "environment": settings.app_env,
        "min_desktop_version": settings.min_desktop_version or settings.min_client_version,
        "min_mobile_version": min_mobile,
        "min_client_version": settings.min_client_version,
        "mobile": {
            "latest_version": latest_mobile,
            "min_supported_version": min_mobile,
            "release_date": release_date or version_identity["release_date"],
            "release_notes": release_notes or None,
            "apk_download_url": apk_url or None,
            "release_channel": release_channel or version_identity["release_channel"],
        },
    }


async def build_capabilities_payload(
    session: AsyncSession,
    settings: Settings,
) -> dict[str, object]:
    repo = SystemSettingRepository(session)
    ai_config = await resolve_ai_config(session, settings)
    tally_enabled = await TallySyncService(session).is_enabled()

    backup_schedule = (await repo.get_string("backup_schedule") or "manual").strip().lower()
    backup_enabled = backup_schedule != "disabled"
    excel_enabled_raw = await repo.get_string("excel_export_enabled")
    excel_enabled = excel_enabled_raw.strip().lower() != "false" if excel_enabled_raw else True
    backup_alerts_raw = await repo.get_string("backup_alerts_enabled")
    security_alerts_raw = await repo.get_string("security_alerts_enabled")

    return {
        "installed_version": settings.app_version,
        "api_version": settings.api_version,
        "schema_version": await resolve_schema_version(session),
        "modules": {
            "auth": True,
            "users": True,
            "inventory": True,
            "sales": True,
            "catalogue": True,
            "reports": True,
            "audit": True,
            "notifications": True,
            "settings": True,
            "dashboard": True,
            "setup": True,
            "security": True,
            "tally": tally_enabled,
            "backup": backup_enabled,
            "ai_enrichment": ai_config.enrichment_enabled,
            "excel_export": excel_enabled,
        },
        "ai": {
            "enrichment_enabled": ai_config.enrichment_enabled,
            "primary_provider": ai_config.primary_provider,
            "fallback_chain": list(ai_config.fallback_chain),
            "configured_providers": {
                "gemini": bool(ai_config.gemini.api_key),
                "groq": bool(ai_config.groq.api_key),
                "openrouter": bool(ai_config.openrouter.api_key),
            },
        },
        "tally_enabled": tally_enabled,
        "backup_enabled": backup_enabled,
        "reports_enabled": True,
        "feature_flags": {
            "rate_limit_enabled": settings.rate_limit_enabled,
            "ai_enrichment_enabled": ai_config.enrichment_enabled,
            "backup_alerts_enabled": (backup_alerts_raw or "true").lower() == "true",
            "security_alerts_enabled": (security_alerts_raw or "true").lower() == "true",
        },
    }
