"""Shared database test fixtures."""

from __future__ import annotations

import os
import subprocess
from collections.abc import AsyncGenerator
from pathlib import Path
from urllib.parse import urlparse, urlunparse

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
TEST_DATABASE_NAME = "webstudio_test"


def _test_database_url(dev_url: str) -> str:
    parsed = urlparse(dev_url)
    db_name = parsed.path.lstrip("/") or "webstudio_dev"
    if db_name == TEST_DATABASE_NAME:
        return dev_url
    if db_name.endswith("_test"):
        return dev_url
    test_path = f"/{TEST_DATABASE_NAME}"
    return urlunparse(parsed._replace(path=test_path))


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    base = get_settings()
    test_db_url = _test_database_url(base.database_url)
    if TEST_DATABASE_NAME not in test_db_url:
        raise RuntimeError(
            f"Refusing to run tests: expected database name '{TEST_DATABASE_NAME}' in DATABASE_URL",
        )
    return base.model_copy(
        update={
            "app_env": "test",
            "database_url": test_db_url,
            "jwt_secret": "test-jwt-secret-for-unit-tests-32bytes!",
        },
    )


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(test_settings: Settings) -> None:
    subprocess.run(
        ["bash", str(REPO_ROOT / "tools/scripts/ensure-test-db.sh")],
        check=True,
        cwd=REPO_ROOT,
    )
    env = os.environ.copy()
    env["DATABASE_URL"] = test_settings.database_url
    subprocess.run(
        ["bash", str(REPO_ROOT / "tools/scripts/alembic.sh"), "upgrade", "head"],
        check=True,
        cwd=REPO_ROOT,
        env=env,
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
