"""Server startup orchestration for business-hours Windows deployments."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.session import get_engine
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.ai.config import resolve_ai_config
from webstudio_backend.services.scheduler_runtime_service import (
    SchedulerRuntimeService,
    reset_shutdown_flag,
)


@dataclass(slots=True)
class StartupCheckResult:
    name: str
    status: str
    detail: str = ""


@dataclass(slots=True)
class StartupReport:
    checks: list[StartupCheckResult] = field(default_factory=list)
    scheduler_state: dict[str, dict[str, Any]] = field(default_factory=dict)
    ready: bool = False

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append(StartupCheckResult(name=name, status=status, detail=detail))


async def verify_postgresql(settings: Settings) -> StartupCheckResult:
    try:
        engine = get_engine()
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return StartupCheckResult(name="postgresql", status="ok")
    except Exception as exc:
        return StartupCheckResult(name="postgresql", status="failed", detail=str(exc))


def _storage_path(settings: Settings) -> Path:
    if settings.webstudio_data_root.strip():
        return Path(settings.webstudio_data_root)
    return Path("C:/") if settings.is_production else Path("/")


async def verify_storage(settings: Settings) -> StartupCheckResult:
    try:
        path = _storage_path(settings)
        usage = shutil.disk_usage(str(path))
        free_ratio = usage.free / usage.total if usage.total else 0
        if free_ratio < 0.05:
            return StartupCheckResult(
                name="storage",
                status="failed",
                detail=f"Low disk space on {path} ({free_ratio:.1%} free)",
            )
        return StartupCheckResult(name="storage", status="ok", detail=str(path))
    except Exception as exc:
        return StartupCheckResult(name="storage", status="failed", detail=str(exc))


async def verify_configuration(session: AsyncSession, settings: Settings) -> StartupCheckResult:
    repo = SystemSettingRepository(session)
    if settings.is_production and len(settings.jwt_secret.encode("utf-8")) < 32:
        return StartupCheckResult(
            name="configuration", status="failed", detail="JWT_SECRET too short"
        )
    initialized = await repo.is_system_initialized()
    if not initialized and settings.is_production:
        return StartupCheckResult(
            name="configuration",
            status="warning",
            detail="System not initialized — setup wizard required",
        )
    return StartupCheckResult(name="configuration", status="ok")


async def verify_ai_configuration(session: AsyncSession, settings: Settings) -> StartupCheckResult:
    try:
        config = await resolve_ai_config(session, settings)
        if config.enrichment_enabled and not any(
            [config.gemini.api_key, config.openai.api_key, config.groq.api_key, config.openrouter.api_key],
        ):
            return StartupCheckResult(
                name="ai_configuration",
                status="warning",
                detail="AI enrichment enabled but no provider API key configured",
            )
        return StartupCheckResult(
            name="ai_configuration",
            status="ok",
            detail=config.primary_provider,
        )
    except Exception as exc:
        return StartupCheckResult(name="ai_configuration", status="failed", detail=str(exc))


async def verify_tally_configuration(session: AsyncSession) -> StartupCheckResult:
    repo = SystemSettingRepository(session)
    enabled = await repo.get_bool("tally_enabled", default=False)
    if not enabled:
        return StartupCheckResult(name="tally_configuration", status="ok", detail="disabled")
    host = (await repo.get_string("tally_host") or "").strip()
    company = (await repo.get_string("tally_company_name") or "").strip()
    if not host or not company:
        return StartupCheckResult(
            name="tally_configuration",
            status="warning",
            detail="Tally enabled but host or company name missing",
        )
    return StartupCheckResult(name="tally_configuration", status="ok", detail=company)


async def restore_scheduler_state(session: AsyncSession) -> dict[str, dict[str, Any]]:
    from webstudio_backend.integrations.tally.constants import DEFAULT_SYNC_INTERVAL_SECONDS
    from webstudio_backend.integrations.tally.incremental_sync import clamp_sync_interval_seconds

    service = SchedulerRuntimeService(session)
    restored = await service.restore_all()
    settings_repo = SystemSettingRepository(session)
    tally_enabled = await settings_repo.get_bool("tally_enabled", default=False)
    if tally_enabled:
        raw_interval = await settings_repo.get_int(
            "tally_sync_interval_seconds",
            default=DEFAULT_SYNC_INTERVAL_SECONDS,
        )
        interval = clamp_sync_interval_seconds(raw_interval)
        await service.sync_interval("tally_sync", interval)
    await session.commit()
    return restored


async def run_startup_orchestration(settings: Settings) -> StartupReport:
    reset_shutdown_flag()
    report = StartupReport()

    pg = await verify_postgresql(settings)
    report.add(pg.name, pg.status, pg.detail)
    if pg.status == "failed":
        logger.error("Startup blocked: PostgreSQL unavailable ({detail})", detail=pg.detail)
        return report

    storage = await verify_storage(settings)
    report.add(storage.name, storage.status, storage.detail)

    from webstudio_backend.infrastructure.database.session import session_scope

    async with session_scope() as session:
        for check_fn in (
            lambda s: verify_configuration(s, settings),
            lambda s: verify_ai_configuration(s, settings),
            verify_tally_configuration,
        ):
            result = await check_fn(session)
            report.add(result.name, result.status, result.detail)

        report.scheduler_state = await restore_scheduler_state(session)

    critical_failed = any(
        check.status == "failed" and check.name in {"postgresql", "configuration", "storage"}
        for check in report.checks
    )
    report.ready = not critical_failed
    if report.ready:
        logger.info("Startup orchestration complete — accepting requests")
    else:
        logger.error("Startup orchestration failed critical checks")
    return report
