"""FastAPI dependency injection foundation."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings, get_settings
from webstudio_backend.infrastructure.database.session import get_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


SettingsDep = Depends(get_settings)
DbSessionDep = Depends(get_db_session)
AppSettingsDep = Depends(get_app_settings)
