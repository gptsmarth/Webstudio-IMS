---
Title: Version Matrix
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 11Y
---

# WEBSTUDIO IMS — Version Matrix

**Audit date:** 2026-07-02  
**Target release line:** 0.1.0 (MVP)

---

## Primary Version Alignment

| Component | Source file | Version field | Value | Match? |
|-----------|-------------|-----------------|-------|--------|
| Monorepo root | `package.json` | `version` | **0.1.0** | ✅ |
| Backend package | `apps/backend/pyproject.toml` | `project.version` | **0.1.0** | ✅ |
| Backend runtime | `core/config.py` | `app_version` | **0.1.0** | ✅ |
| Backend API contract | `core/config.py` | `api_version` | **1.0** | ✅ |
| Desktop app | `apps/desktop/package.json` | `version` | **0.1.0** | ✅ |
| Flutter mobile | `apps/mobile_flutter/pubspec.yaml` | `version` | **0.1.0+1** | ⚠️ Build +1 |
| Legacy RN mobile | `apps/mobile/package.json` | `version` | **0.1.0** | ℹ️ Deprecated |
| shared-kernel | `packages/shared-kernel/package.json` | `version` | **0.1.0** | ✅ |
| shared-kernel constants | `packages/shared-kernel/src/index.ts` | `APP_VERSION` | **0.1.0** | ✅ |
| shared-kernel constants | `packages/shared-kernel/src/index.ts` | `API_VERSION` | **1.0** | ✅ |
| api-client | `packages/api-client/package.json` | `version` | **0.1.0** | ✅ |
| ui-components | `packages/ui-components/package.json` | `version` | **0.1.0** | ✅ |

---

## Runtime / Wire Version Metadata

| Surface | Location | Reported value | Aligned? |
|---------|----------|----------------|----------|
| HTTP `API-Version` header | Backend middleware | `1.0` | ✅ |
| `GET /health/live` | `version` field | `0.1.0` | ✅ |
| `GET /api/v1/version` | `backend_version` | `0.1.0` | ✅ |
| `GET /api/v1/version` | `api_version` | `1.0` | ✅ |
| `GET /api/v1/version` | `schema_version` | From Alembic (`0033…`) | ✅ Dynamic |
| `GET /api/v1/version` | `build_version` | Env or `app_version` fallback | ⚠️ Often empty |
| `GET /api/v1/capabilities` | `installed_version` | `0.1.0` | ✅ |
| mDNS TXT `backend_version` | Zeroconf advertisement | `0.1.0` | ✅ |
| Desktop IPC `getVersionInfo` | `electron/main.ts` | `app.getVersion()` + `buildVersion: 0.1.0-mvp` | ❌ Hardcoded MVP suffix |
| Desktop HTTP client | `api-client` default header | `X-Client-Version: 0.1.0` | ✅ Fallback |
| Flutter runtime | `PackageInfo.fromPlatform()` | `0.1.0` from pubspec | ✅ |
| Flutter build number | pubspec `+1` | **1** | ℹ️ Android `versionCode` |

---

## Minimum Client Compatibility

| Setting | Default | Source |
|---------|---------|--------|
| `min_client_version` | 0.1.0 | `config.py` |
| `min_desktop_version` | 0.1.0 | `config.py` |
| `min_mobile_version` | 0.1.0 | `config.py` |
| Server enforcement | **Advisory only** | No middleware rejects old clients |
| Flutter mandatory gate | **Implemented** | Compares to `/api/v1/version` mobile block |
| Desktop boot gate | **Not implemented** | Uses local VersionService only |

---

## Database Schema Version

| Item | Value |
|------|-------|
| Alembic head revision | `0033_tally_connectivity` |
| Migration file count | 33 |
| Exposed via API | `/api/v1/version` → `schema_version` |

---

## Installer / Artifact Versions (M12 — Not Yet Defined)

| Artifact | Version source | Status |
|----------|----------------|--------|
| Windows EXE/MSI | TBD — electron-builder | ❌ Not configured |
| macOS DMG | TBD | ❌ Not configured |
| Android APK/AAB | `pubspec.yaml` 0.1.0+1 | ⚠️ Debug-signed only |
| iOS IPA | Xcode MARKETING_VERSION | ⚠️ Manual |
| Server installer | TBD | ❌ Not configured |

---

## M12 Version Coordination Requirements

1. **Single semver bump script** — update root, backend, desktop, pubspec, shared-kernel in one command.
2. **Build metadata injection** — `WEBSTUDIO_BUILD_VERSION`, `WEBSTUDIO_GIT_COMMIT` for backend and Electron IPC.
3. **Remove hardcoded** `0.1.0-mvp` from `electron/main.ts`.
4. **Align Flutter build number** with CI increment (`0.1.0+<build>`).
5. **Document** installer file naming convention: `WEBSTUDIO-IMS-{platform}-{semver}-{build}`.

---

## Verdict

| Check | Result |
|-------|--------|
| Semantic versions aligned at 0.1.0 | ✅ |
| API version aligned at 1.0 | ✅ |
| Build/installer version pipeline | ❌ M12 required |
| Runtime metadata consistency | ⚠️ Fix hardcoded Electron build string in M12 |
