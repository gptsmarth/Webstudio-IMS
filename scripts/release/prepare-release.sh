#!/usr/bin/env bash
# Assemble a production release bundle: manifest, migrations, env profiles, logging, notes, checksums.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(cat "$ROOT/VERSION")"
RELEASE_DIR="$ROOT/release/v${VERSION}"

echo "[release] Preparing WEBSTUDIO IMS v${VERSION} → ${RELEASE_DIR}"

mkdir -p "$RELEASE_DIR/artifacts" "$RELEASE_DIR/env" "$RELEASE_DIR/logging" "$RELEASE_DIR/migrations"

# Version manifest
python3 "$ROOT/scripts/release/lib/generate_manifest.py" "$ROOT" "$RELEASE_DIR"

# Database migrations
bash "$ROOT/scripts/release/package-migrations.sh" "$RELEASE_DIR/migrations"

# Environment profiles
for profile in development testing staging production; do
  src="$ROOT/config/env/.env.${profile}"
  if [[ -f "$src" ]]; then
    cp "$src" "$RELEASE_DIR/env/${profile}.env"
  fi
done
cp "$ROOT/config/env/.env.example" "$RELEASE_DIR/env/.env.example"

# Logging guides
cp "$ROOT/config/logging/production-logging.md" "$RELEASE_DIR/logging/" 2>/dev/null || true
cp "$ROOT/config/logging/crash-logging.md" "$RELEASE_DIR/logging/" 2>/dev/null || true
cp "$ROOT/config/logging/logrotate-webstudio.conf.example" "$RELEASE_DIR/logging/" 2>/dev/null || true

# Release notes
bash "$ROOT/scripts/release/generate-release-notes.sh" "$RELEASE_DIR"

# Copy built artifacts when present (optional — CI or local packaging)
copy_if_exists() {
  local src="$1"
  local dest="$2"
  if [[ -f "$src" ]]; then
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
    echo "[release] Included artifact: $(basename "$dest")"
  fi
}

copy_if_exists "$ROOT/apps/desktop/release/desktop/WEBSTUDIO Desktop Setup.exe" "$RELEASE_DIR/artifacts/WEBSTUDIO-Desktop-Setup.exe"
copy_if_exists "$ROOT/apps/desktop/release/desktop/WEBSTUDIO Desktop.dmg" "$RELEASE_DIR/artifacts/WEBSTUDIO-Desktop.dmg"
copy_if_exists "$ROOT/release/mobile/WEBSTUDIO IMS.apk" "$RELEASE_DIR/artifacts/WEBSTUDIO-IMS.apk"
copy_if_exists "$ROOT/release/server/WEBSTUDIO Server Setup.exe" "$RELEASE_DIR/artifacts/WEBSTUDIO-Server-Setup.exe"
copy_if_exists "$ROOT/release/backend/webstudio-backend-${VERSION}.tar.gz" "$RELEASE_DIR/artifacts/webstudio-backend-${VERSION}.tar.gz"
copy_if_exists "$ROOT/release/mobile/ios/WEBSTUDIO-IMS.xcarchive.zip" "$RELEASE_DIR/artifacts/WEBSTUDIO-IMS.xcarchive.zip"

# Manifest-aligned artifact names at bundle root (M13 enterprise sync)
copy_if_exists "$ROOT/apps/desktop/release/desktop/WEBSTUDIO Desktop Setup.exe" "$RELEASE_DIR/WEBSTUDIO Desktop Setup.exe"
copy_if_exists "$ROOT/apps/desktop/release/desktop/WEBSTUDIO Desktop.dmg" "$RELEASE_DIR/WEBSTUDIO Desktop.dmg"
copy_if_exists "$ROOT/release/mobile/WEBSTUDIO IMS.apk" "$RELEASE_DIR/WEBSTUDIO IMS.apk"
copy_if_exists "$ROOT/release/server/WEBSTUDIO Server Setup.exe" "$RELEASE_DIR/WEBSTUDIO Server Setup.exe"
copy_if_exists "$ROOT/release/backend/webstudio-backend-${VERSION}.tar.gz" "$RELEASE_DIR/webstudio-backend-${VERSION}.tar.gz"
copy_if_exists "$ROOT/release/mobile/ios/WEBSTUDIO-IMS.xcarchive.zip" "$RELEASE_DIR/WEBSTUDIO-IMS.xcarchive.zip"

# Folder structure doc
cp "$ROOT/release/STRUCTURE.md" "$RELEASE_DIR/STRUCTURE.md" 2>/dev/null || true

# Checksums (entire bundle)
bash "$ROOT/scripts/release/generate-checksums.sh" "$RELEASE_DIR"

echo "[release] Bundle ready: ${RELEASE_DIR}"
echo "[release]   version-manifest.json"
echo "[release]   checksums.sha256"
echo "[release]   RELEASE_NOTES.md"
echo "[release]   migrations/"
echo "[release]   env/"
echo "[release]   logging/"
