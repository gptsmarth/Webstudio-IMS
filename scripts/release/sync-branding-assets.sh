#!/usr/bin/env bash
# Sync canonical WEBSTUDIO branding assets from desktop registry to Flutter.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/apps/desktop/public/assets/webstudio"
DST="$ROOT/apps/mobile_flutter/assets/images"

mkdir -p "$DST"

cp "$SRC/icon.png" "$DST/icon.png"
cp "$SRC/logo-dark.svg" "$DST/logo-dark.svg"
cp "$SRC/splash.svg" "$DST/splash.svg"

echo "Branding assets synced to $DST"
