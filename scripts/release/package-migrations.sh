#!/usr/bin/env bash
# Package Alembic migration scripts into a release bundle.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="${1:-$ROOT/release/migrations}"

SRC="$ROOT/database/migrations"
mkdir -p "$OUT_DIR/versions"

cp "$SRC/alembic.ini" "$OUT_DIR/"
cp "$SRC/env.py" "$OUT_DIR/"
cp "$SRC/script.py.mako" "$OUT_DIR/"
cp "$SRC/versions/"*.py "$OUT_DIR/versions/"

cat > "$OUT_DIR/README.md" <<'EOF'
# WEBSTUDIO IMS — Database Migrations

Apply on the server before starting the new API version:

```bash
cd apps/backend
alembic -c ../../database/migrations/alembic.ini upgrade head
```

Verify head revision matches `version-manifest.json` → `database.alembic_head`.
EOF

echo "Migrations packaged to $OUT_DIR"
