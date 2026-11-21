#!/usr/bin/env python3
"""Check the release checkout without logging credential values or file contents."""

from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
ENV_DIR = Path("config/env")
PROFILES = ("example", "development", "testing", "staging", "production", "production.template")
ALLOWED_ENV_FILES = {ENV_DIR / f".env.{profile}" for profile in PROFILES}
LOCAL_DIRS = (
    Path("tools/uat"),
    Path("apps/backend/updates"),
    Path("apps/backend/webstudio-data"),
    Path("apps/desktop/public/assets/product-images"),
)
PRODUCT_IMAGE_DOCS = {LOCAL_DIRS[-1] / name for name in (".gitkeep", "README.md")}
KEY_EXTENSIONS = {".jks", ".key", ".keystore", ".mobileprovision", ".p12", ".p8", ".pem", ".pfx"}
LEGACY_DEBUG_KEYSTORE = Path("apps/mobile/android/app/debug.keystore")


def private_path(path: Path) -> bool:
    return (
        (any(parent in path.parents for parent in LOCAL_DIRS) and path not in PRODUCT_IMAGE_DOCS)
        or (
            (path.name.startswith(".env.") or path.name == ".env") and path not in ALLOWED_ENV_FILES
        )
        or (path.suffix.lower() in KEY_EXTENSIONS and path != LEGACY_DEBUG_KEYSTORE)
        or "backups" in path.parts
        or path.name == "key.properties"
    )


def profile_errors(path: Path) -> list[str]:
    errors = []
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        key, separator, value = line.strip().partition("=")
        if not separator or key.startswith("#"):
            continue
        value = value.strip().strip("\"'")
        if key == "DATABASE_URL":
            parsed = urlsplit(value)
            if parsed.hostname in {None, "localhost", "127.0.0.1"} and parsed.password in {
                None,
                "webstudio_app",
                "CHANGE_ME",
                "REPLACE_ME",
                "changeme",
            }:
                continue
        elif key == "JWT_SECRET":
            if path.name in {".env.development", ".env.testing"}:
                continue
            if value == "GENERATED_BY_INSTALLER" and path.name == ".env.production.template":
                continue
        elif not key.endswith(("_API_KEY", "_PASSWORD", "_SECRET", "_TOKEN", "_KEY_PATH")):
            continue
        elif key == "POSTGRES_PASSWORD" and value == "webstudio_app":
            continue
        if value:
            errors.append(f"{path}: {key} must be a release placeholder")
    return errors


def main() -> int:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    paths = (Path(name.decode()) for name in tracked.split(b"\0") if name)
    errors = [f"{path}: local-only file is tracked by Git" for path in paths if private_path(path)]
    embedded_keys = subprocess.run(
        ["git", "grep", "--cached", "-Il", "-e", "^-----BEGIN .*PRIVATE KEY-----"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if embedded_keys.returncode not in (0, 1):
        raise RuntimeError("Unable to check the Git index for private keys.")
    errors.extend(
        f"{name}: private key marker detected" for name in embedded_keys.stdout.splitlines()
    )
    for path in sorted(ALLOWED_ENV_FILES):
        errors.extend(profile_errors(path))
    if errors:
        print("\n".join(errors))
        return 1
    print("Release privacy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
