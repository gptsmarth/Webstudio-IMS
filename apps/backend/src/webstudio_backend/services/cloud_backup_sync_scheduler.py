"""Google Drive cloud backup sync — independent background scheduler.

Reads `backup_runs` history and uploads whatever's pending. Deliberately
decoupled from `BackupEngine.create_backup()` (see docs/architecture/future/
cloud-backup-sync.md §0): this module never touches the local backup path,
so a bug here can only ever stall cloud sync, never a local backup.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings, get_settings
from webstudio_backend.infrastructure.database.session import session_scope
from webstudio_backend.infrastructure.repositories.backup_run_repository import BackupRunRepository
from webstudio_backend.infrastructure.repositories.cloud_backup_connection_repository import (
    GOOGLE_DRIVE_PROVIDER,
    CloudBackupConnectionRepository,
)
from webstudio_backend.infrastructure.security.secret_encryption import decrypt_secret
from webstudio_backend.services.google_drive_client import (
    GoogleDriveAuthError,
    GoogleDriveClient,
    GoogleDriveError,
    GoogleDriveQuotaError,
)
from webstudio_backend.services.scheduler_runtime_service import (
    SchedulerRuntimeService,
    is_shutdown_requested,
    sleep_until_next_run,
)

CLOUD_SYNC_POLL_INTERVAL_SECONDS = 900
CLOUD_SYNC_BATCH_SIZE = 5
ERROR_BACKOFF_SECONDS = 3600


def _apply_drive_retention(
    client: GoogleDriveClient, *, folder_id: str, retention_count: int
) -> None:
    files = client.list_files_oldest_first(folder_id=folder_id)
    if len(files) <= retention_count:
        return
    for stale in files[: len(files) - retention_count]:
        client.delete_file(file_id=stale["id"])


async def maybe_run_cloud_backup_sync() -> None:
    settings = get_settings()
    if settings.is_test:
        return
    async with session_scope() as session:
        await run_cloud_backup_sync(session, settings)


async def run_cloud_backup_sync(session: AsyncSession, settings: Settings) -> None:
    """Core sync logic, factored out of `maybe_run_cloud_backup_sync` so tests can
    call it directly against a test session/settings without the `is_test` guard."""
    connections = CloudBackupConnectionRepository(session)
    connection = await connections.get_by_provider(GOOGLE_DRIVE_PROVIDER)
    runtime = SchedulerRuntimeService(session)

    if connection is None or connection.status == "disconnected":
        await runtime.record_run(
            "cloud_backup_sync",
            status="not_connected",
            interval_seconds=CLOUD_SYNC_POLL_INTERVAL_SECONDS,
        )
        await session.commit()
        return

    if connection.status == "error" and connection.last_sync_at is not None:
        elapsed = (datetime.now(UTC) - connection.last_sync_at).total_seconds()
        if elapsed < ERROR_BACKOFF_SECONDS:
            await runtime.record_run(
                "cloud_backup_sync",
                status="backoff",
                interval_seconds=CLOUD_SYNC_POLL_INTERVAL_SECONDS,
            )
            await session.commit()
            return

    from webstudio_backend.services.backup_alert_service import BackupAlertService

    alerts = BackupAlertService(session)
    runs_repo = BackupRunRepository(session)

    try:
        refresh_token = decrypt_secret(
            connection.encrypted_refresh_token,
            secret=settings.jwt_secret,
        )
        client = GoogleDriveClient(
            refresh_token=refresh_token,
            client_id=settings.google_drive_client_id,
            client_secret=settings.google_drive_client_secret,
        )

        folder_id = connection.drive_folder_id or await asyncio.to_thread(
            client.ensure_backup_folder
        )
        if folder_id != connection.drive_folder_id:
            connection.drive_folder_id = folder_id

        pending = await runs_repo.list_pending_cloud_uploads(limit=CLOUD_SYNC_BATCH_SIZE)
        uploaded_count = 0
        for run in pending:
            try:
                file_id = await asyncio.to_thread(
                    client.upload_file,
                    local_path=Path(run.archive_path),
                    folder_id=folder_id,
                    filename=run.filename,
                )
                run.cloud_uploaded_at = datetime.now(UTC)
                run.cloud_upload_status = "uploaded"
                run.cloud_file_id = file_id
                uploaded_count += 1
            except (GoogleDriveAuthError, GoogleDriveQuotaError):
                raise
            except GoogleDriveError as exc:
                run.cloud_upload_status = "failed"
                logger.warning(f"Cloud upload failed for {run.filename}: {exc}")
        await session.flush()

        await asyncio.to_thread(
            _apply_drive_retention,
            client,
            folder_id=folder_id,
            retention_count=connection.retention_count,
        )

        await connections.record_sync_result(connection, status="success", error=None)
        if connection.status != "connected":
            await connections.set_status(connection, status="connected")
        if uploaded_count:
            await alerts.notify_cloud_sync_completed(uploaded_count=uploaded_count)
        await runtime.record_run(
            "cloud_backup_sync",
            status="completed",
            interval_seconds=CLOUD_SYNC_POLL_INTERVAL_SECONDS,
        )
    except GoogleDriveAuthError as exc:
        detail = "Google Drive access was revoked or expired. Reconnect in Settings → Backup."
        await connections.set_status(connection, status="error", error=detail)
        await connections.record_sync_result(connection, status="error", error=str(exc))
        await alerts.notify_cloud_reconnect_needed(detail=detail)
        await runtime.record_run(
            "cloud_backup_sync",
            status="auth_error",
            interval_seconds=CLOUD_SYNC_POLL_INTERVAL_SECONDS,
        )
    except GoogleDriveQuotaError as exc:
        detail = "Google Drive storage quota exceeded. Free up space or upgrade storage."
        await connections.set_status(connection, status="error", error=detail)
        await connections.record_sync_result(connection, status="error", error=str(exc))
        await alerts.notify_cloud_sync_failed(detail=detail)
        await runtime.record_run(
            "cloud_backup_sync",
            status="quota_exceeded",
            interval_seconds=CLOUD_SYNC_POLL_INTERVAL_SECONDS,
        )
    except GoogleDriveError as exc:
        await connections.record_sync_result(connection, status="failed", error=str(exc))
        await alerts.notify_cloud_sync_failed(detail=str(exc))
        await runtime.record_run(
            "cloud_backup_sync",
            status="failed",
            interval_seconds=CLOUD_SYNC_POLL_INTERVAL_SECONDS,
        )
    await session.commit()


async def cloud_backup_sync_scheduler_loop() -> None:
    while not is_shutdown_requested():
        if not await sleep_until_next_run(
            "cloud_backup_sync", interval_seconds=CLOUD_SYNC_POLL_INTERVAL_SECONDS
        ):
            break
        try:
            await maybe_run_cloud_backup_sync()
        except Exception as exc:
            from webstudio_backend.services.backup_alert_service import BackupAlertService

            async with session_scope() as session:
                await BackupAlertService(session).notify_cloud_sync_failed(detail=str(exc))
                runtime = SchedulerRuntimeService(session)
                await runtime.record_run(
                    "cloud_backup_sync",
                    status="failed",
                    interval_seconds=CLOUD_SYNC_POLL_INTERVAL_SECONDS,
                )
                await session.commit()
