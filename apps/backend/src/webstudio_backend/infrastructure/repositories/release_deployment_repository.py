"""Release deployment event persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.release_deployment_event import ReleaseDeploymentEvent
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, paginate


class ReleaseDeploymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_event(self, event: ReleaseDeploymentEvent) -> ReleaseDeploymentEvent:
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def list_events(
        self,
        *,
        page: PageParams,
        event_type: str | None = None,
    ) -> tuple[list[ReleaseDeploymentEvent], int]:
        base = select(ReleaseDeploymentEvent).order_by(desc(ReleaseDeploymentEvent.created_at))
        if event_type:
            base = base.where(ReleaseDeploymentEvent.event_type == event_type)
        result = await paginate(self._session, base, page)
        return result.items, result.total_items

    async def latest_deploy_event(self) -> ReleaseDeploymentEvent | None:
        result = await self._session.execute(
            select(ReleaseDeploymentEvent)
            .where(
                ReleaseDeploymentEvent.event_type == "deploy",
                ReleaseDeploymentEvent.status == "completed",
            )
            .order_by(desc(ReleaseDeploymentEvent.completed_at))
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def complete_event(
        self,
        event: ReleaseDeploymentEvent,
        *,
        status: str,
        detail_patch: dict | None = None,
        error_message: str | None = None,
    ) -> ReleaseDeploymentEvent:
        event.status = status
        event.completed_at = datetime.now(UTC)
        if detail_patch:
            event.detail_json = {**(event.detail_json or {}), **detail_patch}
        if error_message:
            event.error_message = error_message
        await self._session.flush()
        await self._session.refresh(event)
        return event
