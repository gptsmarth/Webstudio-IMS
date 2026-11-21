#!/usr/bin/env bash
# Package backend application tree for enterprise release distribution.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(cat "$ROOT/VERSION")"
OUT_DIR="${1:-$ROOT/release/backend}"
ARCHIVE_NAME="webstudio-backend-${VERSION}.tar.gz"
mkdir -p "$OUT_DIR"

STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

PKG_ROOT="$STAGING/webstudio-backend-${VERSION}"
mkdir -p "$PKG_ROOT"

mkdir -p "$PKG_ROOT/apps-backend"
cp "$ROOT/apps/backend/pyproject.toml" "$ROOT/apps/backend/README.md" "$PKG_ROOT/apps-backend/"
excludes=(--exclude='__pycache__' --exclude='*.pyc' --exclude='.env*' --exclude='*.key' --exclude='*.pem')
tar "${excludes[@]}" -cf - -C "$ROOT/apps/backend" src |
  tar -xf - -C "$PKG_ROOT/apps-backend"
tar "${excludes[@]}" -cf - -C "$ROOT/database" migrations |
  tar -xf - -C "$PKG_ROOT"
cp "$ROOT/VERSION" "$PKG_ROOT/VERSION"
if [[ -f "$ROOT/config/env/.env.example" ]]; then
  mkdir -p "$PKG_ROOT/config/env"
  cp "$ROOT/config/env/.env.example" "$PKG_ROOT/config/env/.env.example"
fi

cat > "$PKG_ROOT/README.md" <<EOF
# WEBSTUDIO IMS Backend Package v${VERSION}

Extract and install on the WEBSTUDIO Server host. Apply migrations before starting the API.

\`\`\`bash
pip install -e apps-backend
alembic -c migrations/alembic.ini upgrade head
\`\`\`

See version-manifest.json in the release bundle for alembic_head.
EOF

tar -czf "$OUT_DIR/$ARCHIVE_NAME" -C "$STAGING" "webstudio-backend-${VERSION}"
echo "[release] Backend package: $OUT_DIR/$ARCHIVE_NAME"
