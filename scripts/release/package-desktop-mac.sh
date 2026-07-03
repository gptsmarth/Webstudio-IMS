#!/usr/bin/env bash
# Build macOS DMG artifacts sequentially (avoids hdiutil volume name collisions on CI).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DESKTOP="$ROOT/apps/desktop"
OUT="$DESKTOP/release/desktop"

cd "$DESKTOP"
pnpm build

mkdir -p "$OUT"

# One architecture per electron-builder invocation — unique DMG mount titles.
pnpm exec electron-builder --mac dmg --x64 --config electron-builder.yml \
  -c.dmg.title="WEBSTUDIO Desktop x64"

detach_dmg() {
  local vol="$1"
  if [[ -d "/Volumes/$vol" ]]; then
    hdiutil detach "/Volumes/$vol" -force -quiet 2>/dev/null || \
      hdiutil detach "/Volumes/$vol" -quiet 2>/dev/null || true
    sleep 2
  fi
}

detach_dmg "WEBSTUDIO Desktop x64"

pnpm exec electron-builder --mac dmg --arm64 --config electron-builder.yml \
  -c.dmg.title="WEBSTUDIO Desktop arm64"

detach_dmg "WEBSTUDIO Desktop arm64"

ARM64_DMG="$OUT/WEBSTUDIO Desktop-arm64.dmg"
CANONICAL_DMG="$OUT/WEBSTUDIO Desktop.dmg"

if [[ -f "$ARM64_DMG" ]]; then
  cp "$ARM64_DMG" "$CANONICAL_DMG"
  echo "[release] Canonical DMG (arm64): $CANONICAL_DMG"
elif [[ -f "$OUT/WEBSTUDIO Desktop-x64.dmg" ]]; then
  cp "$OUT/WEBSTUDIO Desktop-x64.dmg" "$CANONICAL_DMG"
  echo "[release] Canonical DMG (x64 fallback): $CANONICAL_DMG"
else
  echo "No macOS DMG produced under $OUT" >&2
  exit 1
fi

ls -la "$OUT"/*.dmg
