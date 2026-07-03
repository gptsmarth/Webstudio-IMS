"""Release download queue persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from webstudio_backend.infrastructure.database.enums import ReleaseChannel, ReleaseDownloadStatus
from webstudio_backend.infrastructure.database.models.release_download_job import (
    ReleaseDownloadArtifact,
    ReleaseDownloadJob,
)
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, paginate


class ReleaseDownloadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_job_by_id(self, job_id: int) -> ReleaseDownloadJob | None:
        result = await self._session.execute(
            select(ReleaseDownloadJob)
            .options(selectinload(ReleaseDownloadJob.artifacts))
            .where(ReleaseDownloadJob.id == job_id),
        )
        return result.scalar_one_or_none()

    async def find_job_by_github_release(
        self,
        *,
        github_release_id: int,
        channel: ReleaseChannel,
    ) -> ReleaseDownloadJob | None:
        result = await self._session.execute(
            select(ReleaseDownloadJob).where(
                ReleaseDownloadJob.github_release_id == github_release_id,
                ReleaseDownloadJob.release_channel == channel,
            ),
        )
        return result.scalar_one_or_none()

    async def create_job(self, job: ReleaseDownloadJob) -> ReleaseDownloadJob:
        self._session.add(job)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def save_job(self, job: ReleaseDownloadJob) -> ReleaseDownloadJob:
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def save_artifact(self, artifact: ReleaseDownloadArtifact) -> ReleaseDownloadArtifact:
        await self._session.flush()
        await self._session.refresh(artifact)
        return artifact

    async def list_retryable_jobs(self, *, limit: int = 5) -> list[ReleaseDownloadJob]:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(ReleaseDownloadJob)
            .options(selectinload(ReleaseDownloadJob.artifacts))
            .where(
                ReleaseDownloadJob.status.in_(
                    [
                        ReleaseDownloadStatus.PENDING,
                        ReleaseDownloadStatus.QUEUED,
                        ReleaseDownloadStatus.FAILED,
                    ],
                ),
                or_(
                    ReleaseDownloadJob.next_retry_at.is_(None),
                    ReleaseDownloadJob.next_retry_at <= now,
                ),
                ReleaseDownloadJob.attempt_count < ReleaseDownloadJob.max_attempts,
            )
            .order_by(ReleaseDownloadJob.created_at.asc())
            .limit(limit),
        )
        return list(result.scalars().all())

    async def list_history(
        self,
        *,
        page: PageParams,
        statuses: list[ReleaseDownloadStatus] | None = None,
    ) -> tuple[list[ReleaseDownloadJob], int]:
        base = select(ReleaseDownloadJob).options(selectinload(ReleaseDownloadJob.artifacts))
        if statuses:
            base = base.where(ReleaseDownloadJob.status.in_(statuses))
        base = base.order_by(
            ReleaseDownloadJob.completed_at.desc().nullslast(),
            ReleaseDownloadJob.created_at.desc(),
        )
        result = await paginate(self._session, base, page)
        return result.items, result.total_items

    async def count_by_status(self) -> dict[str, int]:
        result = await self._session.execute(
            select(ReleaseDownloadJob.status, func.count()).group_by(ReleaseDownloadJob.status),
        )
        return {row[0].value: int(row[1]) for row in result.all()}

    async def latest_completed_job(self) -> ReleaseDownloadJob | None:
        result = await self._session.execute(
            select(ReleaseDownloadJob)
            .where(ReleaseDownloadJob.status == ReleaseDownloadStatus.COMPLETED)
            .order_by(desc(ReleaseDownloadJob.completed_at))
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def mark_stale_downloading_failed(self) -> int:
        result = await self._session.execute(
            update(ReleaseDownloadJob)
            .where(ReleaseDownloadJob.status == ReleaseDownloadStatus.DOWNLOADING)
            .values(
                status=ReleaseDownloadStatus.FAILED,
                error_message="Interrupted download reset for retry",
            ),
        )
        return int(result.rowcount or 0)
