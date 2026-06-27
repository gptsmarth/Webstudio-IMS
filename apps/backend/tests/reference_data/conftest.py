"""Reference data test isolation."""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def clean_reference_tables(db_session: AsyncSession) -> None:
    await db_session.execute(
        text("TRUNCATE TABLE webstudio.brands, webstudio.locations RESTART IDENTITY CASCADE"),
    )
