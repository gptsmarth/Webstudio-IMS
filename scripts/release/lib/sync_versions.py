#!/usr/bin/env python3
"""Propagate VERSION.json to all packaging manifests (M13H)."""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_catalog(root: Path) -> dict[str, object]:
    path = root / "VERSION.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing canonical version source: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_version_file(root: Path, version: str) -> None:
    (root / "VERSION").write_text(f"{version}\n", encoding="utf-8")


def sync_package_json(path: Path, version: str, catalog: dict[str, object]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = version
    payload["webstudio"] = {
        "buildNumber": int(catalog.get("build_number", 1)),
        "releaseChannel": str(catalog.get("release_channel", "development")),
        "releaseDate": str(catalog.get("release_date", "")),
        "gitCommit": str(catalog.get("git_commit", "")),
        "gitShort": str(catalog.get("git_short", "")),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sync_pubspec(path: Path, version: str, build_number: int) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^version: .*$", f"version: {version}+{build_number}", text, flags=re.M)
    path.write_text(text, encoding="utf-8")


def sync_inno_setup(path: Path, version: str, build_number: int) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'#define MyAppVersion ".*"', f'#define MyAppVersion "{version}"', text)
    if "#define MyAppBuild" in text:
        text = re.sub(r"#define MyAppBuild \d+", f"#define MyAppBuild {build_number}", text)
    else:
        text = text.replace(
            f'#define MyAppVersion "{version}"',
            f'#define MyAppVersion "{version}"\n#define MyAppBuild {build_number}',
            1,
        )
    path.write_text(text, encoding="utf-8")


def sync_catalog(root: Path, *, version: str | None = None, build_number: int | None = None) -> dict[str, object]:
    catalog_path = root / "VERSION.json"
    catalog = load_catalog(root)
    if version is not None:
        catalog["version"] = version
    if build_number is not None:
        catalog["build_number"] = build_number
    if not str(catalog.get("release_date", "")).strip():
        catalog["release_date"] = date.today().isoformat()
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

    resolved_version = str(catalog["version"])
    resolved_build = int(catalog.get("build_number", 1))

    write_version_file(root, resolved_version)
    sync_package_json(root / "package.json", resolved_version, catalog)
    sync_package_json(root / "apps/desktop/package.json", resolved_version, catalog)
    sync_pubspec(root / "apps/mobile_flutter/pubspec.yaml", resolved_version, resolved_build)
    sync_inno_setup(
        root / "infra/windows/server-installer/WEBSTUDIO-Server-Setup.iss",
        resolved_version,
        resolved_build,
    )
    return catalog


def main(argv: list[str]) -> int:
    root = _repo_root()
    version = argv[1] if len(argv) > 1 else None
    build_number = int(argv[2]) if len(argv) > 2 else None
    catalog = sync_catalog(root, version=version, build_number=build_number)
    print(
        f"[sync-versions] {catalog['version']}+{catalog.get('build_number', 1)} "
        f"({catalog.get('release_channel', 'development')}) @ {datetime.now(UTC).isoformat()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
