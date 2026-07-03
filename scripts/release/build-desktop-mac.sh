#!/usr/bin/env bash
# Build WEBSTUDIO Desktop.dmg (macOS).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/apps/desktop"

echo "[release] Building desktop renderer + electron..."
pnpm build

echo "[release] Packaging DMG..."
pnpm exec electron-builder --mac --config electron-builder.yml

echo "[release] Output: apps/desktop/release/desktop/"
