---
Title: Release Folder Structure
Version: 1.0.0
Status: Final — Awaiting Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12A
---

# Folder Structure — Production Packaging Context

**Purpose:** Map repository layout to release-relevant paths. Defines **current state** and **target M12 release layout**.

---

## Repository root (release-relevant)

```
WEBSTUDIO IMS/
├── apps/
│   ├── backend/              # FastAPI server (Python 3.12+)
│   ├── desktop/              # Electron + Vite (Windows/macOS client)
│   ├── mobile_flutter/       # Flutter mobile (Android/iOS)
│   ├── mobile/               # Legacy React Native — EXCLUDE from release
│   └── server/               # Placeholder / future server packaging
├── packages/                 # Shared TS: api-client, auth, ui-components, shared-kernel
├── database/
│   ├── migrations/versions/  # Alembic (head: 0034_tally_incremental_sync)
│   ├── schemas/
│   └── seeds/
├── config/
│   └── env/.env.example      # Server env template (incomplete)
├── assets/brand/             # Supplementary brand assets
├── infra/
│   ├── docker/               # No backend image today
│   └── scripts/
├── scripts/                  # Dev orchestration (fresh-dev, build_android_debug)
├── docs/
│   ├── deployment/           # DEPLOY-001 operator manual
│   └── milestones/m12a/      # This audit
├── compose.yaml              # PostgreSQL only
├── package.json              # pnpm workspace root (v0.1.0)
└── pnpm-workspace.yaml
```

---

## Backend (`apps/backend/`)

```
apps/backend/
├── pyproject.toml            # Runtime deps + webstudio-api entry
├── alembic.ini
├── src/webstudio_backend/
│   ├── app.py                # create_app factory, scheduler startup
│   ├── core/config.py        # Settings (env-driven)
│   ├── api/routers/
│   ├── services/
│   └── integrations/tally/
└── tests/
```

**Production deploy (today):** Copy tree → venv → `pip install -e .` → systemd/NSSM → `alembic upgrade head` → `webstudio-api`.

**Missing for packaging:** `requirements.lock`, Windows service installer script, optional wheel/sdist publish.

---

## Desktop (`apps/desktop/`)

```
apps/desktop/
├── package.json              # @webstudio/desktop v0.1.0
├── electron/
│   ├── main.ts               # buildVersion: '0.1.0-mvp' (hardcoded)
│   └── preload.ts
├── public/
│   └── assets/webstudio/     # CANONICAL branding registry
│       ├── icon.ico
│       ├── icon.icns
│       ├── logo-dark.svg
│       ├── logo-light.svg
│       └── splash.svg
├── src/                      # React renderer
├── dist/                     # Vite build (gitignored)
└── dist-electron/            # Compiled main/preload (gitignored)
```

**Build outputs (dev):**

| Path | Contents |
|------|----------|
| `dist/` | Static renderer (HTML/JS/CSS) |
| `dist-electron/` | `main.js`, `preload.js` |

**Target M12 release outputs (not yet created):**

```
release/
└── desktop/
    └── v0.1.0/
        ├── WEBSTUDIO-IMS-Setup-0.1.0.exe    # Windows NSIS
        ├── WEBSTUDIO-IMS-0.1.0.dmg            # macOS
        └── SHA256SUMS.txt
```

Recommended: gitignore `release/` or publish from CI artifacts only.

---

## Flutter (`apps/mobile_flutter/`)

```
apps/mobile_flutter/
├── pubspec.yaml              # webstudio_ims 0.1.0+1
├── lib/
│   ├── app_config.dart       # Runtime API URL
│   └── features/
├── android/
│   └── app/build.gradle.kts  # release → debug signing (BLOCKER)
├── ios/
│   └── Runner.xcodeproj/
├── assets/images/            # In-app logos (webstudio)
└── scripts/build_android_debug.sh
```

**Target M12 release outputs:**

```
release/
└── mobile/
    └── v0.1.0+1/
        ├── webstudio-ims-0.1.0+1.apk
        ├── webstudio-ims-0.1.0+1.aab          # Optional sideload vs store-prep
        └── ios/
            └── WEBSTUDIO-IMS.ipa              # Ad-hoc or enterprise distribution
```

---

## Database

```
database/migrations/versions/
├── 0001_*.py … 0033_*.py
└── 0034_tally_incremental_sync.py   # HEAD
```

**Operator data paths (documented, not in repo):**

| Platform | Typical path |
|----------|--------------|
| Windows server | `D:\WEBSTUDIO-IMS\` (logs, backups per DEPLOY-001) |
| macOS dev | `~/Library/Application Support/webstudio-ims/` (desktop logs) |
| Android | App sandbox + shared preferences for API URL |

---

## Configuration & secrets (never commit)

```
config/env/.env.example       # Template only
config/env/.env               # Local dev (gitignored)
```

Production secrets: `JWT_SECRET`, `DATABASE_URL`, `WEBSTUDIO_SECRET_ENCRYPTION_KEY`, TLS cert paths, Android keystore, Apple signing certs.

---

## CI / release (current vs target)

**Current:**

```
.github/workflows/
├── ci-backend.yml            # Placeholder / partial
├── ci-desktop.yml
├── ci-flutter.yml
└── release.yml               # PLACEHOLDER — no artifact upload
```

**Target M12:**

```
.github/workflows/release.yml
  on: push tag v*
  jobs:
    backend-sdist (optional)
    desktop-win + desktop-mac
    flutter-apk + flutter-ios (signed via secrets)
  artifacts → GitHub Releases / internal artifact store
```

---

## Branding asset flow (target)

```
apps/desktop/public/assets/webstudio/   (source of truth)
        │
        ├──► electron-builder (icon.ico / icon.icns)
        ├──► flutter_launcher_icons (Android mipmaps, iOS AppIcon)
        └──► flutter_native_splash (white + logo-dark)
```

---

## Directories to exclude from release artifacts

| Path | Reason |
|------|--------|
| `apps/mobile/` | Legacy RN stub |
| `apps/mobile-native-temp/` | Temp |
| `.venv`, `node_modules`, `build/` | Build caches |
| `backups/` | Local dev dumps |
| `docs/`, `adr/`, `.cursor/` | Not shipped to end users |

---

## Related documents

- [PRODUCTION_PACKAGING_REPORT.md](./PRODUCTION_PACKAGING_REPORT.md)
- [BRANDING_PACKAGING_MATRIX.md](../m12/BRANDING_PACKAGING_MATRIX.md)
