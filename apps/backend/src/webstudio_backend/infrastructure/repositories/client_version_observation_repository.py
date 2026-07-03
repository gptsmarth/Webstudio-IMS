"""Client version observation persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.client_version_observation import (
    ClientVersionObservation,
)


class ClientVersionObservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_observation(
        self,
        *,
        platform: str,
        client_version: str,
        release_channel: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        stmt = (
            insert(ClientVersionObservation)
            .values(
                platform=platform,
                client_version=client_version,
                release_channel=release_channel,
                observation_count=1,
                first_seen_at=now,
                last_seen_at=now,
            )
            .on_conflict_do_update(
                index_elements=["platform", "client_version"],
                set_={
                    "observation_count": ClientVersionObservation.observation_count + 1,
                    "last_seen_at": now,
                    "release_channel": release_channel,
                },
            )
        )
        await self._session.execute(stmt)

    async def distribution_by_platform(self, platform_prefix: str) -> list[ClientVersionObservation]:
        result = await self._session.execute(
            select(ClientVersionObservation)
            .where(ClientVersionObservation.platform.like(f"{platform_prefix}%"))
            .order_by(
                desc(ClientVersionObservation.observation_count),
                desc(ClientVersionObservation.last_seen_at),
            )
            .limit(25),
        )
        return list(result.scalars().all())
