#!/usr/bin/env bash
# Extract release notes for the current VERSION from CHANGELOG.md.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="$(cat "$ROOT/VERSION")"
RELEASE_DIR="${1:-$ROOT/release/v${VERSION}}"
OUT="$RELEASE_DIR/RELEASE_NOTES.md"

mkdir -p "$RELEASE_DIR"

python3 - "$ROOT" "$VERSION" "$OUT" <<'PY'
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

root, version, out_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
pattern = rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
match = re.search(pattern, changelog, re.S)
body = match.group(1).strip() if match else "_No changelog section for this version — see git history._"

manifest_hint = ""
manifest = root / "release" / f"v{version}" / "version-manifest.json"
if manifest.is_file():
    manifest_hint = f"\n\nSee `version-manifest.json` for component versions and migration head.\n"

content = f"""---
Title: Release Notes — WEBSTUDIO IMS {version}
Generated: {datetime.now(UTC).strftime('%Y-%m-%d')}
---

# WEBSTUDIO IMS {version}

{body}
{manifest_hint}
## Upgrade

1. Back up PostgreSQL and `WEBSTUDIO_DATA_ROOT`.
2. Apply migrations: `alembic upgrade head`.
3. Replace server application files or run installer.
4. Upgrade desktop and mobile clients to **{version}** or newer.
5. Verify checksums: `shasum -a 256 -c checksums.sha256`.

## Support

- Deployment: `docs/deployment/DEPLOYMENT_GUIDE.md`
- Release engineering: `docs/milestones/m12g/RELEASE_ENGINEERING_REPORT.md`
"""
out_path.write_text(content, encoding="utf-8")
print(f"Wrote {out_path}")
PY
