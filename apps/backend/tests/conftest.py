"""Shared database test fixtures."""

from __future__ import annotations

import subprocess
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings, get_settings
from webstudio_backend.infrastructure.database.session import (
    close_db,
    get_session_factory,
    init_db,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    subprocess.run(
        ["bash", str(REPO_ROOT / "tools/scripts/alembic.sh"), "upgrade", "head"],
        check=True,
        cwd=REPO_ROOT,
    )


@pytest_asyncio.fixture(scope="session", autouse=True)
async def database_engine(
    test_settings: Settings,
    apply_migrations: None,
) -> AsyncGenerator[None, None]:
    await init_db(test_settings)
    yield
    await close_db()


@pytest_asyncio.fixture
async def db_session(database_engine: None) -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        yield session
        await session.rollback()
