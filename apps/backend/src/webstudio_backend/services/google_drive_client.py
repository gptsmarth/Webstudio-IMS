"""Thin wrapper around the Google Drive API for the cloud backup sync scheduler.

Kept separate from the scheduler so tests can mock `GoogleDriveClient` wholesale
instead of touching the real Drive API (see docs/architecture/future/cloud-backup-sync.md §6).
Uses the `drive.file` scope only — the app can only see/touch files/folders it
creates itself, never the rest of the connected account's Drive.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

DRIVE_FOLDER_NAME = "WEBSTUDIO Backups"
DRIVE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class GoogleDriveError(Exception):
    """Base error for Drive operations. Caught by the scheduler; never raised past it."""


class GoogleDriveAuthError(GoogleDriveError):
    """Refresh token is invalid/revoked — reconnect is required."""


class GoogleDriveQuotaError(GoogleDriveError):
    """Drive storage quota exceeded."""


def _credentials(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
):
    from google.oauth2.credentials import Credentials

    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )


def _classify_http_error(exc: Exception) -> GoogleDriveError:
    from google.auth.exceptions import RefreshError

    if isinstance(exc, RefreshError):
        return GoogleDriveAuthError(str(exc))

    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        return GoogleDriveError(str(exc))

    if isinstance(exc, HttpError):
        status = getattr(exc.resp, "status", None)
        reason = str(exc).lower()
        if status in (401, 403) and (
            "invalid_grant" in reason or "invalid credentials" in reason or "unauthorized" in reason
        ):
            return GoogleDriveAuthError(str(exc))
        if status == 403 and ("quota" in reason or "storage" in reason):
            return GoogleDriveQuotaError(str(exc))
        return GoogleDriveError(str(exc))

    return GoogleDriveError(str(exc))


class GoogleDriveClient:
    """Authenticated Drive API operations, scoped to files this app creates."""

    def __init__(self, *, refresh_token: str, client_id: str, client_secret: str) -> None:
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret
        self._service = None

    def _get_service(self) -> Any:
        if self._service is None:
            from googleapiclient.discovery import build

            credentials = _credentials(
                refresh_token=self._refresh_token,
                client_id=self._client_id,
                client_secret=self._client_secret,
            )
            self._service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        return self._service

    def ensure_backup_folder(self) -> str:
        """Create-or-reuse the app's dedicated Drive folder. Returns the folder id."""
        try:
            service = self._get_service()
            query = (
                f"name='{DRIVE_FOLDER_NAME}' and mimeType='{DRIVE_FOLDER_MIME_TYPE}' "
                "and trashed=false"
            )
            response = (
                service.files().list(q=query, spaces="drive", fields="files(id,name)").execute()
            )
            files = response.get("files", [])
            if files:
                return str(files[0]["id"])
            metadata = {"name": DRIVE_FOLDER_NAME, "mimeType": DRIVE_FOLDER_MIME_TYPE}
            created = service.files().create(body=metadata, fields="id").execute()
            return str(created["id"])
        except Exception as exc:
            raise _classify_http_error(exc) from exc

    def upload_file(self, *, local_path: Path, folder_id: str, filename: str) -> str:
        """Resumable-upload the archive into the app's Drive folder. Returns the Drive file id."""
        try:
            from googleapiclient.http import MediaFileUpload

            service = self._get_service()
            metadata = {"name": filename, "parents": [folder_id]}
            media = MediaFileUpload(str(local_path), resumable=True)
            request = service.files().create(body=metadata, media_body=media, fields="id")
            response = None
            while response is None:
                _status, response = request.next_chunk()
            return str(response["id"])
        except Exception as exc:
            raise _classify_http_error(exc) from exc

    def list_files_oldest_first(self, *, folder_id: str) -> list[dict[str, str]]:
        try:
            service = self._get_service()
            query = f"'{folder_id}' in parents and trashed=false"
            response = (
                service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="files(id,name,createdTime)",
                    orderBy="createdTime",
                    pageSize=1000,
                )
                .execute()
            )
            return list(response.get("files", []))
        except Exception as exc:
            raise _classify_http_error(exc) from exc

    def delete_file(self, *, file_id: str) -> None:
        try:
            service = self._get_service()
            service.files().delete(fileId=file_id).execute()
        except Exception as exc:
            raise _classify_http_error(exc) from exc
