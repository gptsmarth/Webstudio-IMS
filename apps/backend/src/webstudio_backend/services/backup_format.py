"""Extensible backup format detection, validation, and archive loading."""

from __future__ import annotations

import hashlib
import io
import json
import re
import tarfile
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from webstudio_backend.infrastructure.repositories.exceptions import RepositoryError
from webstudio_backend.services.backup_completeness import BACKUP_MANAGED_ASSET_DIRS
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

CHECKSUM_MEMBERS = (
    "config/asset-manifest.json",
    "config/settings-registry.json",
    "database.sql",
)
_WINDOWS_DEVICE = re.compile(r"^(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\.|$)", re.I)


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
    checksum_valid: bool = False


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


def _read_header(path: Path) -> bytes:
    with path.open("rb") as raw:
        return raw.read(WSB_HEADER_LENGTH)


@contextmanager
def _open_tar_archive(path: Path) -> Iterator[tarfile.TarFile]:
    with path.open("rb") as raw:
        header = raw.read(WSB_HEADER_LENGTH)
        if header.startswith(WSB_MAGIC):
            source = io.BytesIO(raw.read())
        else:
            raw.seek(0)
            source = raw
        with tarfile.open(fileobj=source, mode="r:gz") as archive:
            yield archive


def _validate_members(members: list[tarfile.TarInfo]) -> None:
    seen: set[str] = set()
    files: set[str] = set()
    spellings: dict[str, str] = {}
    for member in members:
        parts = member.name.split("/")
        if not (member.isfile() or member.isdir()) or any(
            not part
            or part in {".", ".."}
            or part.endswith((" ", "."))
            or _WINDOWS_DEVICE.match(part)
            or any(ord(char) < 32 or char in '\\:<>|?*"' for char in part)
            for part in parts
        ):
            raise ValueError("Archive contains an unsafe path or an unsupported file type.")
        for length in range(1, len(parts) + 1):
            prefix = "/".join(parts[:length])
            if spellings.setdefault(prefix.casefold(), prefix) != prefix:
                raise ValueError("Archive contains conflicting paths on Windows.")
        name = member.name
        if name in seen:
            raise ValueError("Archive contains duplicate paths.")
        seen.add(name)
        if member.isfile():
            files.add(name)
    for name in seen:
        parts = name.split("/")
        if any("/".join(parts[:length]) in files for length in range(1, len(parts))):
            raise ValueError("Archive contains a file where a directory is required.")


def _verify_content_checksum(archive: tarfile.TarFile, manifest: dict[str, Any]) -> bool:
    expected = manifest.get("checksum")
    if manifest.get("checksum_algorithm") != "sha256" or not expected:
        if str(manifest.get("backup_version")) == "2.1":
            raise ValueError("Backup format 2.1 requires a SHA-256 content checksum.")
        return False
    if not all(name in archive.getnames() for name in CHECKSUM_MEMBERS):
        if str(manifest.get("backup_version")) == "2.1":
            raise ValueError("Archive is missing files required for its content checksum.")
        return False
    digest = hashlib.sha256()
    for name in CHECKSUM_MEMBERS:
        stream = archive.extractfile(name)
        if stream is None:
            raise ValueError("Archive checksum member is not a file.")
        with stream:
            digest.update(name.encode("utf-8"))
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError("Archive content checksum does not match.")
    return True


def _verify_archived_assets(
    archive: tarfile.TarFile, members: list[tarfile.TarInfo], manifest: dict[str, Any]
) -> None:
    prefixes = tuple(f"assets/{folder}/" for folder in BACKUP_MANAGED_ASSET_DIRS)
    paths = {
        member.name
        for member in members
        if member.isfile()
        and member.name.startswith(prefixes)
        and not member.name.endswith("/.gitkeep")
    }
    expected = manifest.get("managed_asset_file_count")
    if expected is not None and (type(expected) is not int or expected != len(paths)):
        raise ValueError("The archive asset count does not match its manifest.")
    if "config/asset-manifest.json" not in archive.getnames():
        return
    stream = archive.extractfile("config/asset-manifest.json")
    if stream is None:
        raise ValueError("Asset manifest is not a file.")
    with stream:
        asset_manifest = json.load(stream)
    if not isinstance(asset_manifest, dict):
        raise ValueError("Asset manifest must contain a JSON object.")
    names = asset_manifest.get("directories")
    if names is not None:
        if not isinstance(names, dict) or any(
            not isinstance(group, list) or not all(isinstance(item, str) for item in group)
            for group in names.values()
        ):
            raise ValueError("Asset manifest contains an invalid file list.")
        listed = {f"assets/{folder}/{item}" for folder, group in names.items() for item in group}
        if listed != paths:
            raise ValueError("Asset manifest file list does not match the archive.")
    checksums = asset_manifest.get("sha256")
    if checksums is None:
        return
    if not isinstance(checksums, dict) or checksums.keys() != paths:
        raise ValueError("Asset checksums do not cover the archived files.")
    for name in sorted(paths, key=lambda item: archive.getmember(item).offset_data):
        stream = archive.extractfile(name)
        if stream is None:
            raise ValueError("A managed asset is not a file.")
        with stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != checksums[name]:
                raise ValueError("A managed asset does not match its archive checksum.")


def _inspect_tar_archive(
    path: Path,
    *,
    format_id: str,
    format_label: str,
    workspace: Path | None = None,
) -> BackupArchiveInspection:
    warnings: list[str] = []
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    try:
        with _open_tar_archive(path) as archive:
            members = archive.getmembers()
            _validate_members(members)
            names = tuple(archive.getnames())
            if any(
                name not in names or not archive.getmember(name).isfile()
                for name in ("manifest.json", "database.sql")
            ):
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
            payload = json.loads(extracted.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Archive manifest must contain a JSON object.")
            manifest = payload
            checksum_valid = _verify_content_checksum(archive, manifest)
            _verify_archived_assets(archive, members, manifest)
            # Read through the gzip trailer, beyond tar's end marker.
            while archive.fileobj.read(1024 * 1024):
                pass
            manifest_warnings, manifest_errors = validate_manifest_structure(manifest)
            if workspace is not None and not manifest_errors:
                archive.extractall(workspace, members=members, filter="data")
    except (tarfile.TarError, EOFError, ValueError, OSError) as exc:
        return BackupArchiveInspection(
            format_id=format_id,
            format_label=format_label,
            integrity_valid=False,
            corruption_detected=True,
            manifest=manifest,
            warnings=warnings,
            errors=[f"Archive integrity check failed: {exc}"],
        )

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
        checksum_valid=checksum_valid,
    )


def _extract_tar_archive(
    path: Path,
    workspace: Path,
    *,
    format_id: str,
    format_label: str,
) -> BackupArchiveInspection:
    return _inspect_tar_archive(
        path, format_id=format_id, format_label=format_label, workspace=workspace
    )


class TarGzBackupLoader(BackupFormatLoader):
    format_id = FORMAT_TAR_GZ
    format_label = "Gzip Tar Archive (.tar.gz)"
    preferred_extension = ".tar.gz"

    def can_load(self, path: Path) -> bool:
        return _read_header(path).startswith(GZIP_MAGIC)

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
        header = _read_header(path)
        if header.startswith(WSB_MAGIC):
            return True
        return path.suffix.lower() == ".wsb" and header.startswith(GZIP_MAGIC)

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
