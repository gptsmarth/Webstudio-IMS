#!/usr/bin/env bash
# Stage downloaded GitHub Actions artifacts for prepare-release.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ARTIFACTS_ROOT="${1:-$ROOT/artifacts}"

mkdir -p \
  "$ROOT/apps/desktop/release/desktop" \
  "$ROOT/release/mobile" \
  "$ROOT/release/server" \
  "$ROOT/release/backend"

copy_first() {
  local pattern="$1"
  local dest="$2"
  local found=""
  found="$(find "$ARTIFACTS_ROOT" -path "$pattern" -type f 2>/dev/null | head -n 1 || true)"
  if [[ -n "$found" && -f "$found" ]]; then
    cp "$found" "$dest"
    echo "[stage] $found → $dest"
  fi
}

copy_first "*/WEBSTUDIO Desktop Setup.exe" "$ROOT/apps/desktop/release/desktop/WEBSTUDIO Desktop Setup.exe"
copy_first "*/WEBSTUDIO Desktop.dmg" "$ROOT/apps/desktop/release/desktop/WEBSTUDIO Desktop.dmg"
copy_first "*/WEBSTUDIO IMS.apk" "$ROOT/release/mobile/WEBSTUDIO IMS.apk"
copy_first "*/WEBSTUDIO Server Setup.exe" "$ROOT/release/server/WEBSTUDIO Server Setup.exe"
copy_first "*/webstudio-backend-*.tar.gz" "$ROOT/release/backend/"

echo "[stage] Artifact staging complete"
