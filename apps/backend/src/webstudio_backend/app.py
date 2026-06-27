"""WEBSTUDIO IMS FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from webstudio_backend.api.middleware.correlation_id import CorrelationIdMiddleware
from webstudio_backend.api.middleware.request_logging import RequestLoggingMiddleware
from webstudio_backend.api.middleware.security_headers import SecurityHeadersMiddleware
from webstudio_backend.api.routers import audit_logs, auth, dashboard, health, inventory, metadata, notifications, setup, users
from webstudio_backend.core.config import Settings, get_settings
from webstudio_backend.core.exceptions import register_exception_handlers
from webstudio_backend.core.logging import configure_logging
from webstudio_backend.infrastructure.database.session import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    await init_db(settings)
    yield
    await close_db()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
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
    app.include_router(setup.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(inventory.router)
    app.include_router(dashboard.router)
    app.include_router(notifications.router)
    app.include_router(audit_logs.router)

    return app
