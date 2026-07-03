#!/usr/bin/env bash
# Build WEBSTUDIO Desktop.dmg (macOS).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
bash "$ROOT/scripts/release/validate-branding-icons.sh"
bash "$ROOT/scripts/release/package-desktop-mac.sh"
