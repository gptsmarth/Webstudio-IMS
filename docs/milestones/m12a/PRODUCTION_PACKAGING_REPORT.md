---
Title: Production Packaging Report
Version: 1.0.0
Status: Final — Awaiting Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12A
---

# Production Packaging Report — Milestone 12A

**Audit date:** 2026-07-02  
**Method:** Read-only codebase review, manifest inspection, cross-reference with M11Y signoff and M12 global rules.  
**Code changes:** None.

---

## Executive summary

WEBSTUDIO IMS is **functionally ready for packaging work** (M11Y engineering signoff: proceed to M12). It is **not ready to ship installers** today because:

1. **No desktop installer pipeline** — `electron-builder`, NSIS, DMG, code signing absent  
2. **No mobile release pipeline** — Android release signing uses debug keys; iOS distribution not configured  
3. **No CI release workflow** — `.github/workflows/release.yml` is a placeholder  
4. **No backend release artifact** — server deployed as source + venv (documented), no Windows service installer in repo  
5. **Production hardening gaps** — ungated Preview/demo mode (desktop), no renderer CSP, incomplete `.env.example` vs runtime Settings  
6. **Branding assets exist but are not bound** to OS shell (window icon, launcher mipmaps, native splash)

**Recommendation:** Approve M12A reports → implement M12B packaging in dependency order: version bump script → electron-builder → Flutter icon/splash generation → signing → CI artifacts → staging acceptance.

---

## Layer-by-layer assessment

### Backend — ⚠️ Deployable, not packaged

| Area | Status | Notes |
|------|--------|-------|
| API & business logic | ✅ | 293+ tests; incremental Tally sync implemented |
| Configuration | ⚠️ | Pydantic Settings; `.env.example` incomplete vs `config.py` |
| Production gate | ✅ Partial | `JWT_SECRET` ≥32 bytes when `APP_ENV=production` |
| Entry point | ✅ | `webstudio-api` / uvicorn factory + optional TLS |
| Container | ❌ | `compose.yaml` = Postgres only; no backend image |
| Windows service | 📄 | Documented in SYSTEM_ARCHITECTURE; no repo script |
| Migrations | ✅ | Alembic head **`0034_tally_incremental_sync`** (34 revisions) |
| Lockfile | ❌ | `pyproject.toml` min pins only; no reproducible lock |

### Electron (Desktop) — ⚠️ Builds, does not ship

| Area | Status | Notes |
|------|--------|-------|
| Dev/build | ✅ | `pnpm build` → `dist/` + `dist-electron/` |
| electron-builder | ❌ | Not installed or configured |
| Security baseline | ✅ | contextIsolation, sandbox, no nodeIntegration |
| CSP | ❌ | No renderer Content-Security-Policy |
| Demo / Preview mode | ❌ | Always available — **11Y-H01 blocker** |
| Version metadata | ⚠️ | `0.1.0-mvp` hardcoded in `electron/main.ts` |
| Branding on disk | ✅ | `public/assets/webstudio/*` complete |
| Branding in shell | ❌ | No BrowserWindow icon; installer graphics absent |

### Flutter (Mobile) — ⚠️ Runnable, not release-ready

| Area | Status | Notes |
|------|--------|-------|
| App identity | ⚠️ | `0.1.0+1`; display names inconsistent |
| Android signing | ❌ | Release buildType uses **debug** keystore |
| iOS signing | ❌ | No DEVELOPMENT_TEAM / distribution profile in repo |
| Bundle IDs | ⚠️ | Android `com.webstudio.webstudio_ims` ≠ iOS `com.webstudio.webstudioIms` |
| Icons / splash | ❌ | Flutter template defaults |
| API URL | ✅ By design | Runtime discovery + saved URL (LAN model) |
| Mandatory update gate | ✅ | Compares to `/api/v1/version` |
| Release scripts | ❌ | Debug APK only; no `build apk --release` script |

### Database — ✅ Schema stable

| Area | Status | Notes |
|------|--------|-------|
| Schema | ✅ | PostgreSQL, schema `webstudio` |
| Migrations | ✅ | Linear chain, head `0034` |
| Seeds | ℹ️ | Reference seeds optional; setup wizard initializes system |
| Backup/restore | ✅ | Application backup module + documented pg_dump procedure |

### Configuration — ⚠️ Gaps for ops

| Area | Status | Notes |
|------|--------|-------|
| Template | ⚠️ | `config/env/.env.example` — 46 lines, missing many Settings fields |
| Scheduler flags | ⚠️ | `WEBSTUDIO_*_SCHEDULER` env vars undocumented in example |
| Desktop env | ❌ | No `VITE_*` production template |
| CORS / TLS | ⏳ | Per-deployment; documented in DEPLOY-001 |

### Assets — ⚠️ Registry complete, binding incomplete

| Area | Status | Notes |
|------|--------|-------|
| Canonical registry | ✅ | `apps/desktop/public/assets/webstudio/` |
| In-app usage | ✅ | Logos via AssetManifest |
| Installer / OS | ❌ | ICO/ICNS not wired to electron-builder |
| Mobile | ❌ | Not generated from registry |

### Logging — ⚠️ stdout-only

| Area | Status | Notes |
|------|--------|-------|
| Backend | ✅ JSON to stdout in production | No file rotation in code |
| Desktop | ✅ | `userData/webstudio-client.log` (Electron main) |
| Mobile | ⚠️ | Standard Flutter/debug; no centralized ship strategy |
| Architecture doc | ⚠️ | File paths under `D:\WEBSTUDIO-IMS\logs\` not implemented |

### Runtime dependencies — See [RUNTIME_DEPENDENCIES.md](./RUNTIME_DEPENDENCIES.md)

### Versioning — See [VERSION_STRATEGY.md](./VERSION_STRATEGY.md)

### Release folders — See [FOLDER_STRUCTURE.md](./FOLDER_STRUCTURE.md)

---

## Critical blockers before first installer

| ID | Blocker | Layer | M12 action |
|----|---------|-------|------------|
| P-01 | No `electron-builder` / Setup.exe / DMG | Desktop | Add config + scripts |
| P-02 | Android release signed with debug key | Flutter | Keystore + Gradle config |
| P-03 | iOS distribution signing not configured | Flutter | Xcode team + profiles |
| P-04 | Preview/demo mode ungated in production builds | Desktop | Build-time or env gate |
| P-05 | CI `release.yml` placeholder | DevOps | Tag-triggered artifact build |
| P-06 | No unified version/build injection | All | M12 C3/C4 |
| P-07 | Flutter/iOS launcher icons are templates | Flutter | Generate from webstudio registry |
| P-08 | No Python dependency lockfile | Backend | pip-tools or uv lock for server installs |
| P-09 | `pnpm audit` — 23 advisories (mostly dev) | Node | Upgrade Vite/Electron in M12 |
| P-10 | Bundle ID mismatch Android vs iOS | Flutter | Align in M12 D11 |

---

## Non-blockers (acceptable for MVP packaging)

- Runtime API URL on mobile (LAN discovery model)
- No backend Docker image (on-prem Windows server model)
- Advisory-only min client version on server (Flutter enforces; desktop does not)
- Legacy `apps/mobile` React Native stub in monorepo (exclude from release builds)

---

## Test status reference (M11Y)

| Suite | Result |
|-------|--------|
| Desktop vitest | 95/95 pass |
| Flutter tests | 121/121 pass |
| Backend pytest | Partial — CI placeholder; local runs vary |
| Tally incremental | 22/22 pass (post-M12 engine) |

---

## Alignment with M12 global rules

| Rule | Audit finding |
|------|---------------|
| No UI redesign | ✅ This audit proposes packaging/config only |
| Extend only | ✅ Recommended work is scripts, assets, CI |
| Four release artifacts | ❌ None produced yet |
| WEBSTUDIO branding | ⚠️ Assets ready; platform binding pending |
| Alembic for schema | ✅ Head at 0034; no packaging-related migration needed now |

---

## Verdict

| Question | Answer |
|----------|--------|
| Safe to start packaging **implementation**? | **Yes**, after M12A review approval |
| Safe to ship to customers **today**? | **No** |
| Estimated packaging work | M12B–M12E (installer, mobile signing, CI, staging drills) per [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md) |

---

## References

- [M11Y Final Engineering Signoff](../m11y/FINAL_ENGINEERING_SIGNOFF.md)
- [M12 Global Rules](../m12/M12_GLOBAL_RULES.md)
- [Deployment Guide](../../deployment/DEPLOYMENT_GUIDE.md)
- [Branding Matrix](../m12/BRANDING_PACKAGING_MATRIX.md)
