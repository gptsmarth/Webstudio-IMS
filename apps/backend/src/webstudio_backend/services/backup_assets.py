"""Stage and verify managed backup files while a database restore is pending."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from webstudio_backend.infrastructure.repositories.exceptions import RepositoryError
from webstudio_backend.services.backup_completeness import BACKUP_MANAGED_ASSET_DIRS


def asset_file_checksum(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def managed_backup_files(source_root: Path, directories: tuple[str, ...]) -> dict[Path, Path]:
    files: dict[Path, Path] = {}
    for directory in directories:
        folder = source_root / directory
        if folder.is_symlink() or folder.is_junction():
            continue
        for parent, subdirs, names in folder.walk():
            subdirs[:] = sorted(name for name in subdirs if not (parent / name).is_junction())
            for name in sorted(names):
                item = parent / name
                if name != ".gitkeep" and not item.is_symlink() and item.is_file():
                    files[item.relative_to(source_root)] = item
    return files


def _validate_destination(root: Path, relative: Path) -> None:
    target = root
    for part in relative.parts:
        if target.is_symlink() or target.is_junction() or (target.exists() and not target.is_dir()):
            raise RepositoryError("A managed asset destination is not a regular directory.")
        target /= part
    if target.is_symlink() or target.is_junction() or (target.exists() and not target.is_file()):
        raise RepositoryError("A managed asset destination is not a regular file.")


@contextmanager
def restore_managed_files(
    source_root: Path,
    destination: Path | None,
    *,
    directories: tuple[str, ...] = BACKUP_MANAGED_ASSET_DIRS,
    expected_count: int | None = None,
) -> Iterator[int]:
    files = managed_backup_files(source_root, directories)
    if expected_count is not None and len(files) != expected_count:
        raise RepositoryError("The archive asset count does not match its manifest.")
    if not files:
        yield 0
        return
    if destination is None:
        raise RepositoryError(
            "The managed assets folder is unavailable. Check the server data directory."
        )
    for relative in files:
        _validate_destination(destination, relative)

    changed: list[tuple[Path, Path | None]] = []
    staging: Path | None = None
    keep_staging = False
    try:
        destination.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".restore-assets-", dir=destination))
        checksums: dict[Path, str] = {}
        for relative, source in files.items():
            prepared = staging / "new" / relative
            prepared.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, prepared)
            checksums[relative] = asset_file_checksum(source)
        try:
            for relative, checksum in checksums.items():
                _validate_destination(destination, relative)
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                original = None
                if target.exists():
                    original = staging / "original" / relative
                    original.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(target, original)
                changed.append((target, original))
                os.replace(staging / "new" / relative, target)
                if asset_file_checksum(target) != checksum:
                    raise RepositoryError("A managed file did not match the archive after copying.")
            yield len(files)
        except BaseException as exc:
            for target, original in reversed(changed):
                try:
                    if original is None:
                        target.unlink(missing_ok=True)
                    else:
                        os.replace(original, target)
                except OSError:
                    keep_staging = True
            if keep_staging:
                raise RepositoryError(
                    f"Could not roll back all managed files. Originals are retained in {staging.name}."
                ) from exc
            raise
    except OSError as exc:
        raise RepositoryError(
            "Could not restore managed files. Check server data folder access and disk space."
        ) from exc
    finally:
        if staging is not None and not keep_staging:
            shutil.rmtree(staging, ignore_errors=True)
