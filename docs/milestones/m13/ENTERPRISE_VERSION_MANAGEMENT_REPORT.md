---
Title: Enterprise Version Management Report
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: M13H
Related Documents:
  - docs/api/openapi/platform-version-v1.yaml
  - docs/api/openapi/releases-v1.yaml
  - VERSION.json
---

# Enterprise Version Management Report (M13H)

## Executive Summary

M13H delivers **centralized version management** for WEBSTUDIO IMS. A single canonical source (`VERSION.json` at the repository root) propagates version identity to backend runtime, desktop, Flutter, database manifests, Windows installer scripts, and release metadata. Public APIs expose a unified version identity block, and every client About screen displays the six required enterprise fields.

## Canonical Version Source

| Field | Source | Propagation |
|-------|--------|-------------|
| `version` | `VERSION.json` | `VERSION`, `package.json`, desktop `package.json`, `pubspec.yaml`, Inno Setup `MyAppVersion`, backend `Settings.app_version` |
| `build_number` | `VERSION.json` | Flutter `version+X`, desktop `webstudio.buildNumber`, Inno Setup `MyAppBuild`, backend `Settings.build_number` |
| `release_channel` | `VERSION.json` | Backend `Settings.release_channel`, release manifests, client About UI |
| `release_date` | `VERSION.json` | Desktop `webstudio.releaseDate`, manifest `release.release_date` |
| `git_commit` / `git_short` | `VERSION.json` (CI) or runtime git | Backend version APIs, desktop `webstudio.gitCommit`, release bundles |
| `database_revision` | Live Alembic head at runtime | `/api/v1/version`, release `version_identity`, About UI |

**Canonical file:** [`VERSION.json`](../../../VERSION.json)

**Sync tooling:**

- [`scripts/release/sync-versions.sh`](../../../scripts/release/sync-versions.sh) — propagate `VERSION.json` to all targets
- [`scripts/release/bump-version.sh`](../../../scripts/release/bump-version.sh) — update `VERSION.json` then sync
- [`scripts/release/sync-version-from-tag.sh`](../../../scripts/release/sync-version-from-tag.sh) — CI tag → `VERSION.json` → sync

## Backend Architecture

| Component | Path | Role |
|-----------|------|------|
| Version catalog loader | `apps/backend/src/webstudio_backend/core/version_catalog.py` | Loads `VERSION.json`, resolves git metadata |
| Enterprise version service | `apps/backend/src/webstudio_backend/services/enterprise_version_service.py` | Builds unified `version_identity` |
| Platform info | `apps/backend/src/webstudio_backend/services/platform_info_service.py` | Enriches `GET /api/v1/version` |
| Release service | `apps/backend/src/webstudio_backend/services/enterprise_release_service.py` | Enriches `/releases/current` and `/releases/latest` |
| Settings bootstrap | `apps/backend/src/webstudio_backend/core/config.py` | Applies catalog defaults via `get_settings()` |

### Version identity payload

```json
{
  "version": "0.1.0",
  "build_number": 1,
  "git_commit": "abc123…",
  "git_short": "abc1234",
  "release_date": "2026-06-27",
  "release_channel": "development",
  "database_revision": "0041_enterprise_rollback",
  "product": "WEBSTUDIO IMS"
}
```

## API Surface

| Endpoint | Enrichment |
|----------|------------|
| `GET /api/v1/version` | Top-level identity fields + `version_identity` + backward-compatible `backend_version`, `schema_version`, client compatibility blocks |
| `GET /api/v1/releases/current` | `release_date`, `database_revision`, `version_identity` |
| `GET /api/v1/releases/latest` | Same as current |

OpenAPI extensions:

- [`docs/api/openapi/platform-version-v1.yaml`](../../api/openapi/platform-version-v1.yaml)
- [`docs/api/openapi/releases-v1.yaml`](../../api/openapi/releases-v1.yaml) (updated)

## Client About Screens

### Desktop (`AboutPanel`)

Location: `apps/desktop/src/components/settings/SettingsPanels.tsx`

Displays:

- Version (installed desktop + server fallback)
- Build number
- Git commit
- Release date
- Release channel
- Database revision (from `GET /api/v1/version`)

Electron IPC `system:getVersionInfo` reads synced `package.json` → `webstudio` metadata block.

### Flutter (`VersionAboutSection`)

Location: `apps/mobile_flutter/lib/features/settings/presentation/version_about_section.dart`

Fetches `GET /api/v1/version` via `platformVersionProvider` and displays all six required fields alongside update-check controls.

## Synchronized Targets

| Target | Mechanism |
|--------|-----------|
| Backend | Runtime read of `VERSION.json` + Alembic head query |
| Desktop | `apps/desktop/package.json` (`version` + `webstudio` block) |
| Flutter | `apps/mobile_flutter/pubspec.yaml` (`version: X.Y.Z+N`) |
| Database | Manifest `database.alembic_head`; live revision in APIs |
| Windows Service / Installer | `infra/windows/server-installer/WEBSTUDIO-Server-Setup.iss` (`MyAppVersion`, `MyAppBuild`) |
| Release metadata | `scripts/release/lib/generate_manifest.py` reads `VERSION.json` |
| Root monorepo | `VERSION`, `package.json` |

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/test_platform.py` | Pass — `/api/v1/version` identity fields |
| `pytest tests/test_version_catalog.py` | Pass — catalog loader |
| `pytest tests/releases/test_release_api.py` | Pass — release enrichment |
| `scripts/release/sync-versions.sh` | Pass — propagates `0.1.0+1` |

## Operational Notes

1. **Bump workflow:** `bash scripts/release/bump-version.sh 0.2.0 2 stable`
2. **CI release tags:** `sync-version-from-tag.sh` writes git commit and release date into `VERSION.json` before artifact builds.
3. **Runtime override:** Environment variables (`WEBSTUDIO_GIT_COMMIT`, `WEBSTUDIO_BUILD_NUMBER`, `WEBSTUDIO_RELEASE_CHANNEL`) still override catalog values when set (deployment flexibility).
4. **Backward compatibility:** `backend_version` and `schema_version` remain on `/api/v1/version` for existing clients.

## Sign-off

Centralized version management is **complete**. One `VERSION.json` source synchronizes all packaging surfaces; APIs and About screens expose the enterprise version identity consistently.

**STOP — M13H deliverable complete.**
