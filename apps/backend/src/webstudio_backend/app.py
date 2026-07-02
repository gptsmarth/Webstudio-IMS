"""WEBSTUDIO IMS FastAPI application factory."""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from webstudio_backend.api.middleware.correlation_id import CorrelationIdMiddleware
from webstudio_backend.api.middleware.request_logging import RequestLoggingMiddleware
from webstudio_backend.api.middleware.security_headers import SecurityHeadersMiddleware
from webstudio_backend.api.routers import access_roles, audit_logs, auth, brands, dashboard, discovery, health, integration_keys, inventory, locations, metadata, notifications, platform, product_images, product_models, reports, sales, search, security, settings as settings_router, setup, sync, tally, users
from webstudio_backend.core.config import Settings, get_settings
from webstudio_backend.core.exceptions import register_exception_handlers
from webstudio_backend.core.logging import configure_logging
from webstudio_backend.core.startup_validation import validate_startup_settings
from webstudio_backend.infrastructure.database.session import close_db, get_session_factory, init_db, session_scope
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import TallyCompanySyncRepository
from webstudio_backend.services.audit_retention_scheduler import audit_retention_loop, maybe_purge_audit_logs
from webstudio_backend.services.backup_scheduler import backup_scheduler_loop
from webstudio_backend.services.mdns_advertisement_service import MdnsAdvertisementService
from webstudio_backend.services.tally_sync_service import TallySyncService

_tally_scheduler_task: asyncio.Task | None = None
_backup_scheduler_task: asyncio.Task | None = None
_audit_retention_task: asyncio.Task | None = None
_mdns_service: MdnsAdvertisementService | None = None


async def _tally_scheduler_loop() -> None:
    while True:
        try:
            async with session_scope() as session:
                sync_service = TallySyncService(session)
                if not await sync_service.is_enabled():
                    await asyncio.sleep(60)
                    continue
                _, _, _, interval = await sync_service.get_connection_config()
                await sync_service.run_sync(correlation_id=str(uuid.uuid4()))
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _tally_scheduler_task, _backup_scheduler_task, _audit_retention_task, _mdns_service
    settings: Settings = app.state.settings
    await init_db(settings)
    company_name = ""
    if not settings.is_test:
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                company_name = (await SystemSettingRepository(session).get_string("company_name") or "").strip()
        except Exception:
            company_name = ""
        _mdns_service = MdnsAdvertisementService(settings)
        app.state.mdns_service = _mdns_service
        _mdns_service.start(company_name=company_name)
    scheduler_enabled = (
        not settings.is_test and os.getenv("WEBSTUDIO_TALLY_SCHEDULER", "0") == "1"
    )
    backup_scheduler_enabled = (
        not settings.is_test and os.getenv("WEBSTUDIO_BACKUP_SCHEDULER", "1") == "1"
    )
    audit_retention_enabled = (
        not settings.is_test and os.getenv("WEBSTUDIO_AUDIT_RETENTION_SCHEDULER", "1") == "1"
    )
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
    yield
    if _mdns_service is not None:
        _mdns_service.stop()
        _mdns_service = None
    if _audit_retention_task is not None:
        _audit_retention_task.cancel()
        try:
            await _audit_retention_task
        except asyncio.CancelledError:
            pass
        _audit_retention_task = None
    if _backup_scheduler_task is not None:
        _backup_scheduler_task.cancel()
        try:
            await _backup_scheduler_task
        except asyncio.CancelledError:
            pass
        _backup_scheduler_task = None
    if _tally_scheduler_task is not None:
        _tally_scheduler_task.cancel()
        try:
            await _tally_scheduler_task
        except asyncio.CancelledError:
            pass
        _tally_scheduler_task = None
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
    app.include_router(discovery.router)
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
