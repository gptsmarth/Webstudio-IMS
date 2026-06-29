"""Backup storage backends — local implemented; cloud/NAS/external future-ready."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BackupStorageBackend(ABC):
    backend_type: str

    @abstractmethod
    def resolve_path(self, filename: str) -> Path:
        raise NotImplementedError

    @abstractmethod
    def ensure_ready(self) -> None:
        raise NotImplementedError

    def upload(self, archive_path: Path) -> str:
        """Future: upload archive to remote provider. Returns remote reference."""
        raise NotImplementedError(f"{self.backend_type} upload is not implemented")

    def download(self, remote_ref: str, target_path: Path) -> Path:
        """Future: download archive from remote provider."""
        raise NotImplementedError(f"{self.backend_type} download is not implemented")


class LocalBackupStorage(BackupStorageBackend):
    backend_type = "local"

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def resolve_path(self, filename: str) -> Path:
        return self._root / filename

    def ensure_ready(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)


class CloudBackupStorage(BackupStorageBackend):
    """Future: S3/Azure/GCS upload. Not implemented."""

    backend_type = "cloud"

    def __init__(self, root: Path) -> None:
        self._root = root

    def resolve_path(self, filename: str) -> Path:
        return self._root / filename

    def ensure_ready(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)


class GoogleDriveBackupStorage(CloudBackupStorage):
    backend_type = "google_drive"


class OneDriveBackupStorage(CloudBackupStorage):
    backend_type = "onedrive"


class DropboxBackupStorage(CloudBackupStorage):
    backend_type = "dropbox"


class NasBackupStorage(LocalBackupStorage):
    backend_type = "nas"


class NetworkShareBackupStorage(LocalBackupStorage):
    backend_type = "network_share"


class ExternalDriveBackupStorage(LocalBackupStorage):
    backend_type = "external_drive"


def create_storage_backend(backend_type: str, root: Path) -> BackupStorageBackend:
    mapping: dict[str, type[BackupStorageBackend]] = {
        "cloud": CloudBackupStorage,
        "google_drive": GoogleDriveBackupStorage,
        "onedrive": OneDriveBackupStorage,
        "dropbox": DropboxBackupStorage,
        "nas": NasBackupStorage,
        "network_share": NetworkShareBackupStorage,
        "external_drive": ExternalDriveBackupStorage,
    }
    backend_cls = mapping.get(backend_type, LocalBackupStorage)
    return backend_cls(root)
