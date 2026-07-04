"""WEBSTUDIO IMS FastAPI application factory."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from webstudio_backend.api.middleware.correlation_id import CorrelationIdMiddleware
from webstudio_backend.api.middleware.request_logging import RequestLoggingMiddleware
from webstudio_backend.api.middleware.security_headers import SecurityHeadersMiddleware
from webstudio_backend.api.routers import (
    access_roles,
    audit_logs,
    auth,
    brands,
    client_deployment,
    client_updates,
    dashboard,
    deployment,
    deployment_center,
    discovery,
    health,
    integration_keys,
    inventory,
    locations,
    metadata,
    network,
    notifications,
    platform,
    product_images,
    product_models,
    releases,
    reports,
    sales,
    search,
    security,
    setup,
    sync,
    tally,
    users,
)
from webstudio_backend.api.routers import (
    settings as settings_router,
)
from webstudio_backend.core.config import Settings, get_settings
from webstudio_backend.core.exceptions import register_exception_handlers
from webstudio_backend.core.logging import configure_logging
from webstudio_backend.core.startup_validation import validate_startup_settings
from webstudio_backend.infrastructure.database.session import (
    close_db,
    get_session_factory,
    init_db,
    session_scope,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import (
    TallyCompanySyncRepository,
)
from webstudio_backend.services.audit_retention_scheduler import (
    audit_retention_loop,
    maybe_purge_audit_logs,
)
from webstudio_backend.services.backup_scheduler import backup_scheduler_loop
from webstudio_backend.services.maintenance_scheduler import maintenance_scheduler_loop
from webstudio_backend.services.mdns_advertisement_service import MdnsAdvertisementService
from webstudio_backend.services.notification_scheduler import notification_scheduler_loop
from webstudio_backend.services.release_sync_scheduler import release_sync_loop
from webstudio_backend.services.scheduler_runtime_service import (
    SchedulerRuntimeService,
    is_shutdown_requested,
    reset_shutdown_flag,
    sleep_until_next_run,
)
from webstudio_backend.services.shutdown_orchestrator import run_graceful_shutdown
from webstudio_backend.services.startup_orchestrator import run_startup_orchestration
from webstudio_backend.services.tally_connectivity_scheduler import tally_connectivity_probe_loop
from webstudio_backend.services.tally_sync_service import TallySyncService

_tally_scheduler_task: asyncio.Task | None = None
_backup_scheduler_task: asyncio.Task | None = None
_audit_retention_task: asyncio.Task | None = None
_notification_scheduler_task: asyncio.Task | None = None
_maintenance_scheduler_task: asyncio.Task | None = None
_tally_connectivity_probe_task: asyncio.Task | None = None
_release_sync_task: asyncio.Task | None = None
_scheduler_persist_task: asyncio.Task | None = None
_mdns_service: MdnsAdvertisementService | None = None


async def _persist_scheduler_state_loop(settings: Settings) -> None:
    interval = max(settings.scheduler_state_persist_seconds, 15)
    while not is_shutdown_requested():
        try:
            async with session_scope() as session:
                await SchedulerRuntimeService(session).snapshot_for_shutdown()
                await session.commit()
        except Exception:
            pass
        try:
            await asyncio.wait_for(asyncio.sleep(interval), timeout=interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass


async def _tally_scheduler_loop() -> None:
    while not is_shutdown_requested():
        async with session_scope() as session:
            sync_service = TallySyncService(session)
            if not await sync_service.is_enabled():
                runtime = SchedulerRuntimeService(session)
                await runtime.record_run("tally_sync", status="disabled", interval_seconds=60)
                await session.commit()
                if not await sleep_until_next_run("tally_sync", interval_seconds=60):
                    break
                continue
            _, _, _, interval = await sync_service.get_connection_config()
            await session.commit()

        if not await sleep_until_next_run("tally_sync", interval_seconds=interval):
            break
        if is_shutdown_requested():
            break
        status = "completed"
        try:
            async with session_scope() as session:
                sync_service = TallySyncService(session)
                if not await sync_service.is_enabled():
                    await session.commit()
                    continue
                _, _, _, interval = await sync_service.get_connection_config()
                await sync_service.run_sync(correlation_id=str(uuid.uuid4()))
                runtime = SchedulerRuntimeService(session)
                await runtime.record_run("tally_sync", status=status, interval_seconds=interval)
                await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            status = "failed"
            try:
                async with session_scope() as session:
                    runtime = SchedulerRuntimeService(session)
                    await runtime.record_run("tally_sync", status=status, interval_seconds=300)
                    await session.commit()
            except Exception:
                pass


async def _cancel_task(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _tally_scheduler_task, _backup_scheduler_task, _audit_retention_task
    global _notification_scheduler_task, _maintenance_scheduler_task, _scheduler_persist_task
    global _tally_connectivity_probe_task
    global _release_sync_task
    global _mdns_service

    settings: Settings = app.state.settings
    reset_shutdown_flag()
    await init_db(settings)

    if settings.is_test:
        from webstudio_backend.services.startup_orchestrator import StartupReport

        startup_report = StartupReport(ready=True)
    else:
        startup_report = await run_startup_orchestration(settings)
    app.state.startup_report = startup_report
    if not startup_report.ready and settings.is_production:
        logger.error("Startup orchestration failed — service may not accept traffic safely")

    company_name = ""
    if not settings.is_test:
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                company_name = (
                    await SystemSettingRepository(session).get_string("company_name") or ""
                ).strip()
        except Exception:
            company_name = ""
        _mdns_service = MdnsAdvertisementService(settings)
        app.state.mdns_service = _mdns_service
        _mdns_service.start(company_name=company_name)

    scheduler_enabled = not settings.is_test and settings.webstudio_tally_scheduler
    backup_scheduler_enabled = not settings.is_test and settings.webstudio_backup_scheduler
    audit_retention_enabled = (
        not settings.is_test and settings.webstudio_audit_retention_scheduler
    )
    notification_scheduler_enabled = (
        not settings.is_test and settings.webstudio_notification_scheduler
    )
    maintenance_scheduler_enabled = (
        not settings.is_test and settings.webstudio_maintenance_scheduler
    )
    tally_probe_enabled = not settings.is_test and settings.webstudio_tally_connectivity_probe
    release_sync_enabled = not settings.is_test and settings.webstudio_release_sync_scheduler

    if scheduler_enabled:
        try:
            async with session_scope() as session:
                await TallyCompanySyncRepository(session).clear_all_sync_in_progress()
                await session.commit()
        except Exception:
            pass
        _tally_scheduler_task = asyncio.create_task(_tally_scheduler_loop())
    if backup_scheduler_enabled:
        _backup_scheduler_task = asyncio.create_task(backup_scheduler_loop())
    if audit_retention_enabled:
        try:
            await maybe_purge_audit_logs()
        except Exception:
            pass
        _audit_retention_task = asyncio.create_task(audit_retention_loop())
    if notification_scheduler_enabled:
        _notification_scheduler_task = asyncio.create_task(notification_scheduler_loop())
    if maintenance_scheduler_enabled:
        _maintenance_scheduler_task = asyncio.create_task(maintenance_scheduler_loop())
    if tally_probe_enabled:
        _tally_connectivity_probe_task = asyncio.create_task(tally_connectivity_probe_loop())
    if release_sync_enabled:
        _release_sync_task = asyncio.create_task(release_sync_loop())
    if not settings.is_test:
        _scheduler_persist_task = asyncio.create_task(_persist_scheduler_state_loop(settings))

    yield

    if settings.is_production:
        await run_graceful_shutdown(wait_for_sync_seconds=float(settings.graceful_shutdown_seconds))
    else:
        reset_shutdown_flag()

    if _mdns_service is not None:
        _mdns_service.stop()
        _mdns_service = None
    await _cancel_task(_scheduler_persist_task)
    _scheduler_persist_task = None
    await _cancel_task(_maintenance_scheduler_task)
    _maintenance_scheduler_task = None
    await _cancel_task(_tally_connectivity_probe_task)
    _tally_connectivity_probe_task = None
    await _cancel_task(_release_sync_task)
    _release_sync_task = None
    await _cancel_task(_notification_scheduler_task)
    _notification_scheduler_task = None
    await _cancel_task(_audit_retention_task)
    _audit_retention_task = None
    await _cancel_task(_backup_scheduler_task)
    _backup_scheduler_task = None
    await _cancel_task(_tally_scheduler_task)
    _tally_scheduler_task = None
    # Test suite keeps a session-scoped engine via tests/conftest.py; closing here
    # would break later tests that share the same process-global session factory.
    if not settings.is_test:
        await close_db()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    validate_startup_settings(settings)
    configure_logging(settings)

    app = FastAPI(
        title="WEBSTUDIO IMS API",
        version=settings.app_version,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID", "API-Version"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(metadata.router)
    app.include_router(platform.router)
    app.include_router(releases.router)
    app.include_router(client_updates.router)
    app.include_router(discovery.router)
    app.include_router(deployment.router)
    app.include_router(client_deployment.router)
    app.include_router(deployment_center.router)
    app.include_router(network.router)
    app.include_router(sync.router)
    app.include_router(search.router)
    app.include_router(setup.router)
    app.include_router(auth.router)
    app.include_router(security.router)
    app.include_router(users.router)
    app.include_router(access_roles.router)
    app.include_router(integration_keys.router)
    app.include_router(brands.router)
    app.include_router(locations.router)
    app.include_router(product_models.router)
    app.include_router(product_images.router)
    app.include_router(inventory.router)
    app.include_router(sales.router)
    app.include_router(dashboard.router)
    app.include_router(notifications.router)
    app.include_router(reports.router)
    app.include_router(audit_logs.router)
    app.include_router(settings_router.router)
    app.include_router(tally.router)

    return app
