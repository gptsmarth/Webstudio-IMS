"""Backup encryption — extension points only (not enabled by default)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BackupEncryptionProvider(ABC):
    """Optional archive encryption. Implement and register when encryption is required."""

    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def algorithm(self) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def encrypt_archive(self, archive_path: Path) -> Path:
        raise NotImplementedError

    @abstractmethod
    def decrypt_archive(self, archive_path: Path) -> Path:
        raise NotImplementedError


class NoOpBackupEncryption(BackupEncryptionProvider):
    """Default provider — archives remain unencrypted."""

    def is_enabled(self) -> bool:
        return False

    def algorithm(self) -> str | None:
        return None

    def encrypt_archive(self, archive_path: Path) -> Path:
        return archive_path

    def decrypt_archive(self, archive_path: Path) -> Path:
        return archive_path


def get_backup_encryption_provider() -> BackupEncryptionProvider:
    """Factory for future encrypted backup support."""
    return NoOpBackupEncryption()
