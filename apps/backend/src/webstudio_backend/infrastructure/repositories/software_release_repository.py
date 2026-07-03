"""Software release catalog persistence."""

from __future__ import annotations

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import ReleaseChannel
from webstudio_backend.infrastructure.database.models.software_release import SoftwareRelease
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, paginate


class SoftwareReleaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_all(self) -> int:
        result = await self._session.scalar(select(func.count()).select_from(SoftwareRelease))
        return int(result or 0)

    async def get_by_id(self, release_id: int) -> SoftwareRelease | None:
        result = await self._session.execute(
            select(SoftwareRelease).where(SoftwareRelease.id == release_id),
        )
        return result.scalar_one_or_none()

    async def get_current(self, channel: ReleaseChannel) -> SoftwareRelease | None:
        result = await self._session.execute(
            select(SoftwareRelease)
            .where(
                SoftwareRelease.release_channel == channel,
                SoftwareRelease.is_current.is_(True),
            )
            .order_by(desc(SoftwareRelease.published_at))
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def get_latest(self, channel: ReleaseChannel) -> SoftwareRelease | None:
        result = await self._session.execute(
            select(SoftwareRelease)
            .where(SoftwareRelease.release_channel == channel)
            .order_by(
                desc(SoftwareRelease.build_number),
                desc(SoftwareRelease.published_at),
            )
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def list_history(
        self,
        channel: ReleaseChannel,
        *,
        page: PageParams,
    ) -> tuple[list[SoftwareRelease], int]:
        base = select(SoftwareRelease).where(SoftwareRelease.release_channel == channel)
        base = base.order_by(
            SoftwareRelease.published_at.desc(),
            SoftwareRelease.build_number.desc(),
        )
        result = await paginate(self._session, base, page)
        return result.items, result.total_items

    async def find_existing(
        self,
        *,
        release_version: str,
        build_number: int,
        channel: ReleaseChannel,
    ) -> SoftwareRelease | None:
        result = await self._session.execute(
            select(SoftwareRelease).where(
                SoftwareRelease.release_version == release_version,
                SoftwareRelease.build_number == build_number,
                SoftwareRelease.release_channel == channel,
            ),
        )
        return result.scalar_one_or_none()

    async def upsert_release(self, release: SoftwareRelease) -> SoftwareRelease:
        existing = await self.find_existing(
            release_version=release.release_version,
            build_number=release.build_number,
            channel=release.release_channel,
        )
        if existing is not None:
            existing.git_commit = release.git_commit
            existing.git_short = release.git_short
            existing.build_timestamp = release.build_timestamp
            existing.release_notes = release.release_notes
            existing.manifest = release.manifest
            existing.checksums = release.checksums
            existing.compatibility_matrix = release.compatibility_matrix
            existing.supported_platforms = release.supported_platforms
            existing.is_current = release.is_current
            if release.published_at is not None:
                existing.published_at = release.published_at
            await self._session.flush()
            await self._session.refresh(existing)
            return existing

        self._session.add(release)
        await self._session.flush()
        await self._session.refresh(release)
        return release

    async def clear_current_flags(self, channel: ReleaseChannel) -> None:
        await self._session.execute(
            update(SoftwareRelease)
            .where(SoftwareRelease.release_channel == channel)
            .values(is_current=False),
        )
