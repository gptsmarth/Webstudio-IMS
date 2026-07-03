#!/usr/bin/env python3
"""Generate WEBSTUDIO IMS version manifest for a release bundle."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def _read_version(root: Path) -> str:
    version_json = root / "VERSION.json"
    if version_json.is_file():
        data = json.loads(version_json.read_text(encoding="utf-8"))
        return str(data.get("version", "")).strip()
    return (root / "VERSION").read_text(encoding="utf-8").strip()


def _read_catalog(root: Path) -> dict[str, object]:
    version_json = root / "VERSION.json"
    if version_json.is_file():
        return json.loads(version_json.read_text(encoding="utf-8"))
    mobile_version = _read_pubspec_version(root / "apps/mobile_flutter/pubspec.yaml")
    return {
        "version": _read_version(root),
        "build_number": _parse_build_number(mobile_version),
        "release_channel": "stable",
        "release_date": "",
        "git_commit": "",
        "git_short": "",
    }


def _read_json_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data.get("version", ""))


def _read_pubspec_version(path: Path) -> str:
    match = re.search(r"^version:\s*(.+)$", path.read_text(encoding="utf-8"), re.M)
    return match.group(1).strip() if match else ""


def _git_commit(root: Path) -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True)
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _git_short(root: Path) -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=root, text=True)
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _alembic_head(root: Path) -> dict[str, str]:
    versions_dir = root / "database/migrations/versions"
    if not versions_dir.is_dir():
        return {"revision": "unknown", "file": ""}
    latest: tuple[str, str] | None = None
    for path in sorted(versions_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r'^revision:\s*str\s*=\s*["\']([^"\']+)["\']', text, re.M)
        if match is None:
            continue
        prefix = path.name.split("_", 1)[0]
        if latest is None or prefix > latest[0]:
            latest = (prefix, match.group(1))
    if latest is None:
        return {"revision": "unknown", "file": ""}
    return {"revision": latest[1], "sequence": latest[0]}


def build_manifest(root: Path, *, channel: str = "stable", build_number: int | None = None) -> dict[str, object]:
    catalog = _read_catalog(root)
    version = str(catalog.get("version") or _read_version(root))
    head = _alembic_head(root)
    mobile_version = _read_pubspec_version(root / "apps/mobile_flutter/pubspec.yaml")
    catalog_build = catalog.get("build_number")
    if build_number is not None:
        resolved_build_number = build_number
    elif isinstance(catalog_build, int):
        resolved_build_number = catalog_build
    else:
        resolved_build_number = _parse_build_number(mobile_version)
    resolved_channel = str(catalog.get("release_channel") or channel)
    git_commit = str(catalog.get("git_commit") or "").strip() or _git_commit(root)
    git_short = str(catalog.get("git_short") or "").strip() or _git_short(root)
    backend_component = {
        "app_version": version,
        "api_version": "1.0",
        "min_client_version": version,
        "min_desktop_version": version,
        "min_mobile_version": version,
    }
    return {
        "schema_version": "2.0.0",
        "product": "WEBSTUDIO IMS",
        "release_version": version,
        "release": {
            "channel": resolved_channel,
            "build_number": resolved_build_number,
            "min_alembic_head": head.get("revision", "unknown"),
            "release_date": str(catalog.get("release_date") or ""),
        },
        "build": {
            "timestamp": datetime.now(UTC).isoformat(),
            "git_commit": git_commit,
            "git_short": git_short,
        },
        "components": {
            "monorepo": {"version": _read_json_version(root / "package.json")},
            "desktop": {"version": _read_json_version(root / "apps/desktop/package.json")},
            "mobile_flutter": {"version": mobile_version},
            "backend": backend_component,
        },
        "database": {
            "engine": "postgresql",
            "schema": "webstudio",
            "alembic_head": head.get("revision", "unknown"),
            "alembic_sequence": head.get("sequence", ""),
            "migration_count": len(list((root / "database/migrations/versions").glob("*.py"))),
        },
        "supported_platforms": [
            {"id": "desktop_windows", "os": "windows", "artifact_key": "desktop_windows"},
            {"id": "desktop_macos", "os": "macos", "artifact_key": "desktop_macos"},
            {"id": "mobile_android", "os": "android", "artifact_key": "mobile_android"},
            {"id": "mobile_ios", "os": "ios", "artifact_key": "mobile_ios"},
            {"id": "server_windows", "os": "windows", "artifact_key": "server_windows"},
            {"id": "backend_package", "os": "linux", "artifact_key": "backend_package"},
        ],
        "compatibility_matrix": {
            "desktop": {"min_version": version, "latest_version": _read_json_version(root / "apps/desktop/package.json")},
            "mobile": {"min_version": version, "latest_version": mobile_version},
            "server": {"min_version": version, "api_version": "1.0"},
            "database": {
                "alembic_head": head.get("revision", "unknown"),
                "min_alembic_head": head.get("revision", "unknown"),
            },
            "min_client_version": version,
        },
        "artifacts": {
            "desktop_windows": "WEBSTUDIO Desktop Setup.exe",
            "desktop_macos": "WEBSTUDIO Desktop.dmg",
            "mobile_android": "WEBSTUDIO IMS.apk",
            "mobile_ios": "WEBSTUDIO-IMS.xcarchive.zip",
            "server_windows": "WEBSTUDIO Server Setup.exe",
            "backend_package": f"webstudio-backend-{version}.tar.gz",
        },
        "environment_profiles": [
            "development",
            "testing",
            "staging",
            "production",
        ],
    }


def _parse_build_number(mobile_version: str) -> int:
    import re

    match = re.search(r"\+(\d+)$", mobile_version.strip())
    return int(match.group(1)) if match else 1


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "release" / f"v{_read_version(root)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(root)
    out_path = out_dir / "version-manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
