#!/usr/bin/env bash
# Sync canonical WEBSTUDIO branding assets from desktop registry to Flutter.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WEBSTUDIO_SRC="$ROOT/apps/desktop/public/assets/webstudio"
BRAND_SRC="$ROOT/apps/desktop/public/assets/brand-logos"
DST="$ROOT/apps/mobile_flutter/assets/images"
BRAND_DST="$ROOT/apps/mobile_flutter/assets/brand-logos"

mkdir -p "$DST" "$BRAND_DST"

cp "$WEBSTUDIO_SRC/icon.png" "$DST/icon.png"
cp "$WEBSTUDIO_SRC/logo-dark.svg" "$DST/logo-dark.svg"
cp "$WEBSTUDIO_SRC/splash.svg" "$DST/splash.svg"

if ! file -b "$DST/icon.png" | grep -q "PNG image"; then
  echo "Synced icon.png is not a valid PNG — regenerate apps/desktop/public/assets/webstudio/icon.png" >&2
  exit 1
fi

rsync -a --delete \
  --exclude README.md \
  --exclude .gitkeep \
  "$BRAND_SRC/" "$BRAND_DST/"

echo "Branding assets synced to $DST"
echo "Brand logos synced to $BRAND_DST"
