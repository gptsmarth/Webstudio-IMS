"""Canonical VERSION.json loader — single source for enterprise version identity."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class VersionCatalog:
    product: str
    version: str
    build_number: int
    release_channel: str
    release_date: str
    git_commit: str
    git_short: str
    source_path: Path | None = None


def find_repo_root(start: Path | None = None) -> Path | None:
    env_root = os.getenv("WEBSTUDIO_REPO_ROOT", "").strip()
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if candidate.is_dir():
            return candidate

    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for candidate in [current, *current.parents]:
        if (candidate / "VERSION.json").is_file():
            return candidate
        package_json = candidate / "package.json"
        if (candidate / "VERSION").is_file() and package_json.is_file():
            try:
                payload = json.loads(package_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if payload.get("name") == "webstudio-ims":
                return candidate
    return None


def _default_catalog() -> VersionCatalog:
    return VersionCatalog(
        product="WEBSTUDIO IMS",
        version="0.1.0",
        build_number=1,
        release_channel="development",
        release_date="",
        git_commit="",
        git_short="",
    )


def _parse_catalog(data: dict[str, object], *, source_path: Path) -> VersionCatalog:
    build_number = data.get("build_number", 1)
    try:
        resolved_build = int(build_number)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        resolved_build = 1

    return VersionCatalog(
        product=str(data.get("product", "WEBSTUDIO IMS")),
        version=str(data.get("version", "0.1.0")),
        build_number=resolved_build,
        release_channel=str(data.get("release_channel", "development")),
        release_date=str(data.get("release_date", "")),
        git_commit=str(data.get("git_commit", "")),
        git_short=str(data.get("git_short", "")),
        source_path=source_path,
    )


@lru_cache
def load_version_catalog() -> VersionCatalog:
    root = find_repo_root(Path(__file__).resolve())
    if root is None:
        return _default_catalog()

    version_json = root / "VERSION.json"
    if version_json.is_file():
        try:
            payload = json.loads(version_json.read_text(encoding="utf-8"))
            return _parse_catalog(payload, source_path=version_json)
        except (OSError, json.JSONDecodeError):
            pass

    version_file = root / "VERSION"
    if version_file.is_file():
        version = version_file.read_text(encoding="utf-8").strip() or "0.1.0"
        return VersionCatalog(
            product="WEBSTUDIO IMS",
            version=version,
            build_number=1,
            release_channel="development",
            release_date="",
            git_commit="",
            git_short="",
            source_path=version_file,
        )

    return _default_catalog()


def resolve_git_commit(*, catalog: VersionCatalog | None = None, fallback: str = "") -> str:
    catalog = catalog or load_version_catalog()
    for candidate in (
        catalog.git_commit.strip(),
        os.getenv("WEBSTUDIO_GIT_COMMIT", "").strip(),
        os.getenv("WEBSTUDIO_BUILD_VERSION", "").strip(),
        fallback.strip(),
    ):
        if candidate:
            return candidate

    root = find_repo_root(Path(__file__).resolve())
    if root is not None:
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass
    return "unknown"


def resolve_git_short(commit: str, *, catalog: VersionCatalog | None = None) -> str:
    catalog = catalog or load_version_catalog()
    if catalog.git_short.strip():
        return catalog.git_short.strip()
    if commit and commit != "unknown":
        return commit[:7]
    return "unknown"
