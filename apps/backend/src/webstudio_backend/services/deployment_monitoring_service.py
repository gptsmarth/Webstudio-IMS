"""Enterprise deployment monitoring analytics (M13I)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.client_version_observation_repository import (
    ClientVersionObservationRepository,
)
from webstudio_backend.infrastructure.repositories.release_deployment_repository import (
    ReleaseDeploymentRepository,
)
from webstudio_backend.infrastructure.repositories.release_deployment_run_repository import (
    ReleaseDeploymentRunRepository,
)
from webstudio_backend.infrastructure.repositories.release_download_repository import (
    ReleaseDownloadRepository,
)
from webstudio_backend.services.enterprise_deployment_engine import EnterpriseDeploymentEngine
from webstudio_backend.services.enterprise_rollback_engine import EnterpriseRollbackEngine
from webstudio_backend.services.github_release_sync_service import GitHubReleaseSyncService
from webstudio_backend.services.scheduler_runtime_service import SchedulerRuntimeService

SCHEDULER_RECOVERY_KEYS = ("backup", "tally_sync", "github_release_sync")


class DeploymentMonitoringService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._downloads = ReleaseDownloadRepository(session)
        self._deployment_events = ReleaseDeploymentRepository(session)
        self._deployment_runs = ReleaseDeploymentRunRepository(session)
        self._client_versions = ClientVersionObservationRepository(session)
        self._sync = GitHubReleaseSyncService(session, settings)
        self._scheduler = SchedulerRuntimeService(session)

    async def get_analytics(self) -> dict[str, Any]:
        sync_status = await self._sync.get_sync_status()
        download_history = await self._sync.get_download_history(page=1, page_size=15)
        failed_downloads = await self._sync.get_failed_history(page=1, page_size=15)
        retry_queue = await self._downloads.list_retryable_jobs(limit=25)
        deployment_events, _ = await self._deployment_events.list_events(
            page=PageParams(page=1, page_size=20),
        )
        deployment_runs = await self._deployment_runs.list_recent(limit=20)
        rollback_history = await EnterpriseRollbackEngine(
            self._session, self._settings
        ).list_history(
            page=1,
            page_size=15,
        )
        scheduler_snapshot = await self._scheduler.export_snapshot()

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": await self._build_summary(sync_status, deployment_runs, rollback_history),
            "release_downloads": {
                "queue_counts": sync_status.get("queue_counts", {}),
                "recent_completed": download_history.get("items", []),
                "recent_failures": failed_downloads.get("items", []),
            },
            "deployment_history": self._serialize_deployment_events(deployment_events),
            "deployment_runs": [self._serialize_deployment_run(run) for run in deployment_runs],
            "rollback_history": rollback_history.get("items", []),
            "deployment_durations": self._deployment_durations(deployment_runs),
            "health_check_history": self._health_check_history(
                deployment_runs, rollback_history.get("items", [])
            ),
            "desktop_version_distribution": self._serialize_version_distribution(
                await self._client_versions.distribution_by_platform("desktop"),
            ),
            "mobile_version_distribution": self._serialize_version_distribution(
                await self._client_versions.distribution_by_platform("mobile"),
            ),
            "deployment_failures": self._deployment_failures(
                deployment_events,
                deployment_runs,
                rollback_history.get("items", []),
                failed_downloads.get("items", []),
            ),
            "retry_queue": [self._serialize_retry_job(job) for job in retry_queue],
            "github_polling_history": self._github_polling_history(sync_status, scheduler_snapshot),
            "scheduler_recovery": self._scheduler_recovery(scheduler_snapshot),
            "tally_scheduler_recovery": self._single_scheduler_recovery(
                scheduler_snapshot,
                "tally_sync",
            ),
            "backup_scheduler_recovery": self._single_scheduler_recovery(
                scheduler_snapshot,
                "backup",
            ),
        }

    async def _build_summary(
        self,
        sync_status: dict[str, Any],
        deployment_runs: list[Any],
        rollback_history: dict[str, Any],
    ) -> dict[str, Any]:
        run_counts = await self._deployment_runs.count_by_status()
        download_counts = sync_status.get("queue_counts", {})
        failed_deployments = int(run_counts.get("failed", 0))
        failed_rollbacks = sum(
            1 for item in rollback_history.get("items", []) if item.get("status") == "failed"
        )
        return {
            "sync_enabled": sync_status.get("enabled", False),
            "last_github_sync_at": sync_status.get("last_sync_at"),
            "last_github_sync_status": sync_status.get("last_sync_status"),
            "pending_downloads": int(download_counts.get("pending", 0))
            + int(download_counts.get("queued", 0)),
            "failed_downloads": int(download_counts.get("failed", 0)),
            "deployment_run_counts": run_counts,
            "rollback_total": rollback_history.get("total_items", 0),
            "failed_rollbacks": failed_rollbacks,
            "failed_deployments": failed_deployments,
            "retry_queue_size": len(await self._downloads.list_retryable_jobs(limit=100)),
        }

    @staticmethod
    def _serialize_deployment_events(events: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "id": event.id,
                "event_type": event.event_type,
                "status": event.status,
                "release_version": event.release_version,
                "build_number": event.build_number,
                "release_channel": event.release_channel.value if event.release_channel else None,
                "administrator_approved": event.administrator_approved,
                "error_message": event.error_message,
                "created_at": event.created_at.isoformat(),
                "completed_at": event.completed_at.isoformat() if event.completed_at else None,
            }
            for event in events
        ]

    @staticmethod
    def _serialize_deployment_run(run: Any) -> dict[str, Any]:
        payload = EnterpriseDeploymentEngine.serialize_run(run)
        payload["duration_seconds"] = DeploymentMonitoringService._duration_seconds(
            run.created_at,
            run.completed_at,
        )
        return payload

    @staticmethod
    def _deployment_durations(runs: list[Any]) -> list[dict[str, Any]]:
        durations = []
        for run in runs:
            seconds = DeploymentMonitoringService._duration_seconds(
                run.created_at, run.completed_at
            )
            if seconds is None:
                continue
            durations.append(
                {
                    "run_id": run.id,
                    "release_version": run.release_version,
                    "build_number": run.build_number,
                    "status": run.status,
                    "duration_seconds": seconds,
                    "created_at": run.created_at.isoformat(),
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                },
            )
        return durations

    @staticmethod
    def _health_check_history(
        deployment_runs: list[Any],
        rollback_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for run in deployment_runs:
            for step in run.steps_json or []:
                if step.get("step") != "run_health_checks":
                    continue
                history.append(
                    {
                        "source": "deployment",
                        "run_id": run.id,
                        "release_version": run.release_version,
                        "status": step.get("status"),
                        "timestamp": step.get("timestamp"),
                        "detail": step.get("detail") or {},
                    },
                )
        for item in rollback_items:
            health = item.get("health_status") or {}
            if not health:
                continue
            history.append(
                {
                    "source": "rollback",
                    "run_id": item.get("run_id"),
                    "from_version": item.get("from_release_version"),
                    "to_version": item.get("to_release_version"),
                    "status": health.get("status") or item.get("status"),
                    "timestamp": item.get("completed_at") or item.get("created_at"),
                    "detail": health,
                },
            )
        history.sort(key=lambda row: str(row.get("timestamp") or ""), reverse=True)
        return history[:30]

    @staticmethod
    def _deployment_failures(
        events: list[Any],
        runs: list[Any],
        rollback_items: list[dict[str, Any]],
        failed_downloads: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        failures: list[dict[str, Any]] = []
        for event in events:
            if event.status != "failed":
                continue
            failures.append(
                {
                    "kind": "deployment_event",
                    "id": event.id,
                    "action": event.event_type,
                    "release_version": event.release_version,
                    "error_message": event.error_message,
                    "timestamp": (
                        event.completed_at.isoformat()
                        if event.completed_at
                        else event.created_at.isoformat()
                    ),
                },
            )
        for run in runs:
            if run.status != "failed":
                continue
            failures.append(
                {
                    "kind": "deployment_run",
                    "id": run.id,
                    "action": "deploy",
                    "release_version": run.release_version,
                    "error_message": run.error_message,
                    "timestamp": (
                        run.completed_at.isoformat()
                        if run.completed_at
                        else run.created_at.isoformat()
                    ),
                },
            )
        for item in rollback_items:
            if item.get("status") != "failed":
                continue
            failures.append(
                {
                    "kind": "rollback_run",
                    "id": item.get("run_id"),
                    "action": "rollback",
                    "release_version": item.get("to_release_version"),
                    "error_message": item.get("error_message"),
                    "timestamp": item.get("completed_at") or item.get("created_at"),
                },
            )
        for job in failed_downloads:
            failures.append(
                {
                    "kind": "release_download",
                    "id": job.get("id"),
                    "action": "download",
                    "release_version": job.get("release_version"),
                    "error_message": job.get("error_message"),
                    "timestamp": job.get("completed_at") or job.get("started_at"),
                },
            )
        failures.sort(key=lambda row: str(row.get("timestamp") or ""), reverse=True)
        return failures[:40]

    @staticmethod
    def _serialize_retry_job(job: Any) -> dict[str, Any]:
        return {
            "job_id": job.id,
            "tag_name": job.tag_name,
            "release_version": job.release_version,
            "build_number": job.build_number,
            "status": job.status.value,
            "attempt_count": job.attempt_count,
            "max_attempts": job.max_attempts,
            "next_retry_at": job.next_retry_at.isoformat() if job.next_retry_at else None,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
        }

    @staticmethod
    def _serialize_version_distribution(rows: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "platform": row.platform,
                "client_version": row.client_version,
                "observation_count": row.observation_count,
                "release_channel": row.release_channel,
                "first_seen_at": row.first_seen_at.isoformat(),
                "last_seen_at": row.last_seen_at.isoformat(),
            }
            for row in rows
        ]

    @staticmethod
    def _github_polling_history(
        sync_status: dict[str, Any],
        scheduler_snapshot: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        github = scheduler_snapshot.get("github_release_sync", {})
        state = github.get("state_json") or sync_status.get("state") or {}
        return {
            "enabled": sync_status.get("enabled", False),
            "github_repo": sync_status.get("github_repo", ""),
            "polling_interval_seconds": sync_status.get("polling_interval_seconds"),
            "last_sync_at": sync_status.get("last_sync_at"),
            "last_sync_status": sync_status.get("last_sync_status"),
            "queue_counts": sync_status.get("queue_counts", {}),
            "latest_completed": sync_status.get("latest_completed"),
            "recent_polls": list(state.get("recent_polls") or state.get("history") or [])[:15],
            "last_shutdown_at": state.get("last_shutdown_at"),
            "last_recovery_at": state.get("last_recovery_at"),
        }

    @staticmethod
    def _scheduler_recovery(scheduler_snapshot: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            DeploymentMonitoringService._single_scheduler_recovery(scheduler_snapshot, key)
            for key in SCHEDULER_RECOVERY_KEYS
        ]

    @staticmethod
    def _single_scheduler_recovery(
        scheduler_snapshot: dict[str, dict[str, Any]],
        scheduler_key: str,
    ) -> dict[str, Any]:
        row = scheduler_snapshot.get(scheduler_key, {})
        state = row.get("state_json") or {}
        return {
            "scheduler_key": scheduler_key,
            "last_run_at": row.get("last_run_at"),
            "last_run_status": row.get("last_run_status"),
            "next_run_at": row.get("next_run_at"),
            "interval_seconds": row.get("interval_seconds"),
            "last_shutdown_at": state.get("last_shutdown_at"),
            "last_recovery_at": state.get("last_recovery_at"),
            "recovered": bool(state.get("last_recovery_at") or state.get("restored_at")),
            "state": state,
        }

    @staticmethod
    def _duration_seconds(created_at: datetime, completed_at: datetime | None) -> float | None:
        if completed_at is None:
            return None
        return max(0.0, (completed_at - created_at).total_seconds())
