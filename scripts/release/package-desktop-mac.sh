#!/usr/bin/env bash
# Build one macOS DMG for both Apple silicon and Intel.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DESKTOP="$ROOT/apps/desktop"
OUT="$DESKTOP/release/desktop"

cd "$DESKTOP"

artifact="WEBSTUDIO Desktop-dev.dmg"
signing=()
if [[ -n "${CSC_LINK:-}${APPLE_ID:-}${APPLE_APP_SPECIFIC_PASSWORD:-}${APPLE_TEAM_ID:-}" ]]; then
  : "${CSC_LINK:?Developer ID Application certificate required}"
  : "${APPLE_ID:?Apple notarization account required}"
  : "${APPLE_APP_SPECIFIC_PASSWORD:?Apple notarization password required}"
  : "${APPLE_TEAM_ID:?Apple notarization team required}"
  artifact="WEBSTUDIO Desktop.dmg"
  signing+=("-c.forceCodeSigning=true")
else
  # GitHub Actions exports missing secrets as empty strings. Electron Builder
  # treats an empty CSC_LINK as a certificate path relative to the app.
  unset CSC_LINK CSC_KEY_PASSWORD
  export CSC_IDENTITY_AUTO_DISCOVERY=false
  signing+=("-c.mac.notarize=false")
  echo "[release] macOS signing is unavailable. Building a development DMG."
fi

pnpm build
pnpm exec electron-builder --mac dmg --universal --publish never --config electron-builder.yml \
  "-c.mac.artifactName=$artifact" "${signing[@]}"

app="$OUT/mac-universal/WEBSTUDIO Desktop.app"
architectures="$(lipo "$app/Contents/MacOS/WEBSTUDIO Desktop" -archs)"
if [[ " $architectures " != *" arm64 "* || " $architectures " != *" x86_64 "* ]]; then
  echo "[release] Expected arm64 and x86_64 in the Mac app, found: $architectures" >&2
  exit 1
fi
if [[ "$artifact" == "WEBSTUDIO Desktop.dmg" ]]; then
  codesign --verify --deep --strict "$app"
  xcrun stapler validate "$app"
  spctl --assess --type execute "$app"
fi
test -f "$OUT/$artifact"
echo "[release] Installer: $OUT/$artifact"
