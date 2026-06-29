"""Extensible backup format detection, validation, and archive loading."""

from __future__ import annotations

import io
import json
import re
import tarfile
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from webstudio_backend.infrastructure.repositories.exceptions import RepositoryError
from webstudio_backend.services.backup_manifest import validate_manifest_structure

GZIP_MAGIC = b"\x1f\x8b"
WSB_MAGIC = b"WEBSTUDIO-BACKUP\x00"
WSB_HEADER_LENGTH = len(WSB_MAGIC)

BACKUP_ARCHIVE_PATTERN = re.compile(r"^webstudio-backup-.+\.tar\.gz$")
IMPORTED_ARCHIVE_PATTERN = re.compile(r"^webstudio-import-.+\.tar\.gz$")
BACKUP_WSB_PATTERN = re.compile(r"^webstudio-backup-.+\.wsb$")
IMPORTED_WSB_PATTERN = re.compile(r"^webstudio-import-.+\.wsb$")
LEGACY_SQL_PATTERN = re.compile(r"^webstudio-.+\.sql$")

FORMAT_TAR_GZ = "tar_gz"
FORMAT_WSB = "wsb"
FORMAT_LEGACY_SQL = "legacy_sql"


@dataclass(frozen=True, slots=True)
class BackupArchiveInspection:
    format_id: str
    format_label: str
    integrity_valid: bool
    corruption_detected: bool
    manifest: dict[str, Any]
    members: tuple[str, ...] = ()
    manifest_valid: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class BackupFormatLoader(ABC):
    """Extension point for WEBSTUDIO backup archive formats."""

    format_id: str
    format_label: str
    preferred_extension: str

    @abstractmethod
    def can_load(self, path: Path) -> bool:
        """Return True when this loader can handle the file contents."""

    @abstractmethod
    def inspect(self, path: Path) -> BackupArchiveInspection:
        """Validate archive integrity and read manifest without full extraction."""

    @abstractmethod
    def extract(self, path: Path, workspace: Path) -> BackupArchiveInspection:
        """Extract archive members into workspace and return inspection metadata."""

    def read_manifest(self, path: Path) -> dict[str, Any]:
        return self.inspect(path).manifest


def is_supported_backup_filename(filename: str) -> bool:
    return bool(
        BACKUP_ARCHIVE_PATTERN.match(filename)
        or IMPORTED_ARCHIVE_PATTERN.match(filename)
        or BACKUP_WSB_PATTERN.match(filename)
        or IMPORTED_WSB_PATTERN.match(filename)
        or LEGACY_SQL_PATTERN.match(filename)
    )


def is_supported_backup_path(path: Path) -> bool:
    if not path.is_file():
        return False
    if is_supported_backup_filename(path.name):
        return True
    try:
        detect_backup_format(path)
    except RepositoryError:
        return False
    return True


def detect_backup_format(path: Path) -> BackupFormatLoader:
    if not path.is_file():
        raise RepositoryError(f"Backup not found: {path.name}")
    for loader in _REGISTERED_LOADERS:
        if loader.can_load(path):
            return loader
    raise RepositoryError(f"Unsupported or unrecognized backup format: {path.name}")


def detect_import_extension(content: bytes, original_name: str = "") -> str:
    hinted = Path(original_name).suffix.lower() if original_name else ""
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    try:
        loader = detect_backup_format(temp_path)
        if hinted == ".wsb":
            return ".wsb"
        return loader.preferred_extension
    finally:
        temp_path.unlink(missing_ok=True)


def _payload_offset(path: Path) -> int:
    header = path.read_bytes()[:WSB_HEADER_LENGTH]
    if header.startswith(WSB_MAGIC):
        return WSB_HEADER_LENGTH
    return 0


def _gzip_payload_bytes(path: Path) -> bytes:
    offset = _payload_offset(path)
    return path.read_bytes()[offset:]


def _open_tar_archive(path: Path) -> tarfile.TarFile:
    payload = _gzip_payload_bytes(path)
    if not payload.startswith(GZIP_MAGIC):
        raise tarfile.TarError("Missing gzip payload")
    return tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz")


def _inspect_tar_archive(
    path: Path,
    *,
    format_id: str,
    format_label: str,
) -> BackupArchiveInspection:
    warnings: list[str] = []
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    try:
        with _open_tar_archive(path) as archive:
            names = tuple(archive.getnames())
            if "manifest.json" not in names or "database.sql" not in names:
                errors.append("Archive is missing required members (manifest.json, database.sql).")
                return BackupArchiveInspection(
                    format_id=format_id,
                    format_label=format_label,
                    integrity_valid=False,
                    corruption_detected=False,
                    manifest=manifest,
                    members=names,
                    warnings=warnings,
                    errors=errors,
                )
            extracted = archive.extractfile("manifest.json")
            if extracted is None:
                return BackupArchiveInspection(
                    format_id=format_id,
                    format_label=format_label,
                    integrity_valid=False,
                    corruption_detected=True,
                    manifest=manifest,
                    members=names,
                    warnings=warnings,
                    errors=["manifest.json could not be read."],
                )
            manifest = json.loads(extracted.read().decode("utf-8"))
    except (tarfile.TarError, json.JSONDecodeError, OSError) as exc:
        return BackupArchiveInspection(
            format_id=format_id,
            format_label=format_label,
            integrity_valid=False,
            corruption_detected=True,
            manifest=manifest,
            warnings=warnings,
            errors=[f"Archive integrity check failed: {exc}"],
        )

    manifest_warnings, manifest_errors = validate_manifest_structure(manifest)
    warnings.extend(manifest_warnings)
    errors.extend(manifest_errors)
    integrity_valid = not errors
    return BackupArchiveInspection(
        format_id=format_id,
        format_label=format_label,
        integrity_valid=integrity_valid,
        corruption_detected=False,
        manifest=manifest,
        members=names,
        manifest_valid=not manifest_errors,
        warnings=warnings,
        errors=errors,
    )


def _extract_tar_archive(
    path: Path,
    workspace: Path,
    *,
    format_id: str,
    format_label: str,
) -> BackupArchiveInspection:
    inspection = _inspect_tar_archive(path, format_id=format_id, format_label=format_label)
    if inspection.corruption_detected or not inspection.integrity_valid:
        return inspection
    with _open_tar_archive(path) as archive:
        archive.extractall(workspace, filter="data")
    return inspection


class TarGzBackupLoader(BackupFormatLoader):
    format_id = FORMAT_TAR_GZ
    format_label = "Gzip Tar Archive (.tar.gz)"
    preferred_extension = ".tar.gz"

    def can_load(self, path: Path) -> bool:
        if path.suffixes[-2:] == [".tar", ".gz"] or path.suffix == ".gz":
            payload = path.read_bytes()[:2]
            return payload == GZIP_MAGIC
        if path.name.endswith(".tar.gz"):
            return path.read_bytes()[:2] == GZIP_MAGIC
        return path.read_bytes()[:2] == GZIP_MAGIC and _payload_offset(path) == 0

    def inspect(self, path: Path) -> BackupArchiveInspection:
        return _inspect_tar_archive(path, format_id=self.format_id, format_label=self.format_label)

    def extract(self, path: Path, workspace: Path) -> BackupArchiveInspection:
        return _extract_tar_archive(
            path,
            workspace,
            format_id=self.format_id,
            format_label=self.format_label,
        )


class WsbBackupLoader(BackupFormatLoader):
    """WEBSTUDIO Backup format — gzip tar payload with optional branded header."""

    format_id = FORMAT_WSB
    format_label = "WEBSTUDIO Backup (.wsb)"
    preferred_extension = ".wsb"

    def can_load(self, path: Path) -> bool:
        header = path.read_bytes()[:WSB_HEADER_LENGTH]
        if header.startswith(WSB_MAGIC):
            return True
        return path.suffix.lower() == ".wsb" and path.read_bytes()[:2] == GZIP_MAGIC

    def inspect(self, path: Path) -> BackupArchiveInspection:
        return _inspect_tar_archive(path, format_id=self.format_id, format_label=self.format_label)

    def extract(self, path: Path, workspace: Path) -> BackupArchiveInspection:
        return _extract_tar_archive(
            path,
            workspace,
            format_id=self.format_id,
            format_label=self.format_label,
        )


class LegacySqlBackupLoader(BackupFormatLoader):
    format_id = FORMAT_LEGACY_SQL
    format_label = "Legacy SQL Dump (.sql)"
    preferred_extension = ".sql"

    def can_load(self, path: Path) -> bool:
        if not path.name.endswith(".sql"):
            return False
        sample = path.read_bytes()[:4096].decode("utf-8", errors="ignore").strip().lower()
        return sample.startswith(("--", "create", "copy", "set", "select", "pg_"))

    def inspect(self, path: Path) -> BackupArchiveInspection:
        return BackupArchiveInspection(
            format_id=self.format_id,
            format_label=self.format_label,
            integrity_valid=path.stat().st_size > 0,
            corruption_detected=False,
            manifest={},
            warnings=["Legacy SQL backup has no manifest or checksum metadata."],
        )

    def extract(self, path: Path, workspace: Path) -> BackupArchiveInspection:
        target = workspace / "database.sql"
        target.write_bytes(path.read_bytes())
        return self.inspect(path)


_REGISTERED_LOADERS: tuple[BackupFormatLoader, ...] = (
    LegacySqlBackupLoader(),
    WsbBackupLoader(),
    TarGzBackupLoader(),
)
