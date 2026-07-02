---
Title: Production Pre-Packaging Audit
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 11Y — Production Pre-Packaging Audit
Related Documents: docs/milestones/m11/RELEASE_READINESS_REPORT.md, docs/milestones/m11x/MILESTONE_11X_IMPLEMENTATION_REPORT.md
---

# Production Pre-Packaging Audit

**Purpose:** Final engineering verification before Milestone 12 (Release Engineering). No installers or release artifacts were built in this pass.

**Audit date:** 2026-07-02  
**Scope:** Backend, Desktop, Flutter Mobile, Database, Shared Packages, CI, Documentation

---

## Executive Summary

| Area | Verdict | Notes |
|------|---------|-------|
| Backend application code | ✅ Pass | No critical defects; env-gated production validation |
| Desktop application code | ✅ Pass | Electron hardened; 95/95 unit tests |
| Flutter mobile code | ✅ Pass | 121/121 tests; version gate on mobile |
| Database schema | ✅ Pass | 33 migrations; head `0033_tally_connectivity` |
| Shared packages | ⚠️ Conditional | Minimal surface; no dedicated tests |
| CI/CD | ❌ Fail | All workflows are placeholders |
| Release infrastructure | ❌ Not present | Expected — Milestone 12 deliverable |
| Security (LAN production) | ⚠️ Conditional | Strong baseline; demo mode and upload caps open |
| Documentation | ⚠️ Partial | M11/M11X current; legacy RN references stale |

---

## 1. Project-Wide Audit

### Backend (`apps/backend`)

| Check | Result |
|-------|--------|
| Development-only endpoints | OpenAPI `/docs` gated to `development` only ✅ |
| Debug-only logic | Test env skips mDNS, uses mock AI chain only in `is_test` ✅ |
| TODO/FIXME in `src/` | **None found** ✅ |
| Placeholder implementations | `/health/ready` migrations check hardcoded `"ok"` ⚠️ |
| Mock services in production | Enrichment uses Gemini only; mock not in production path ✅ |
| Rate limiting | Flag exists; **middleware not implemented** ⚠️ |

### Desktop (`apps/desktop`)

| Check | Result |
|-------|--------|
| Placeholder pages | `PlaceholderPage.tsx` exists but not in production nav ✅ |
| Demo/offline mode | **Preview mode exposed on ConnectionPage** ⚠️ |
| UpdateService | Stub only (M12) ℹ️ |
| Orphan components | `TallyPage`, `BulkOperationsDialog`, `ChangeRoleDialog` ℹ️ |

### Flutter Mobile (`apps/mobile_flutter`)

| Check | Result |
|-------|--------|
| Primary mobile client | Active; feature-complete for M11 scope ✅ |
| Unimplemented scan modes | QR/NFC/BT throw `UnimplementedError` (documented) ℹ️ |
| Mandatory update gate | Implemented on mobile ✅ |

### Legacy React Native (`apps/mobile`)

| Check | Result |
|-------|--------|
| Status | **Superseded by Flutter** — still in pnpm workspace ⚠️ |
| Production path | Not used for release; creates tooling confusion |

### Shared Packages

| Package | Role | Tests |
|---------|------|-------|
| `@webstudio/shared-kernel` | Types, network discovery helpers | 0 (via desktop) |
| `@webstudio/api-client` | HTTP client, headers | 0 |
| `@webstudio/ui-components` | Shared UI | 0 |

---

## 2. Environment Audit

| Check | Result | Details |
|-------|--------|---------|
| `.env` in git | ✅ Ignored | `.gitignore` covers `.env`, `.env.*` |
| Test credentials in repo | ✅ None committed | Only in `config/env/.env.example` and test fixtures |
| Default JWT secret | ⚠️ Dev default | `change-me-in-production`; **startup fails in production** if &lt; 32 bytes ✅ |
| Default DB URL | ⚠️ Dev default | Overridden via `DATABASE_URL` in deployment |
| Hardcoded localhost (prod code) | ⚠️ Acceptable | Connection discovery fallbacks, Tally localhost default, config defaults — all overridable via env or user URL |
| Absolute filesystem paths | ✅ Clean | Uses `app.getPath('userData')`, `path_provider`, configurable backup paths |
| API keys in source | ✅ None | Loaded from settings/env only |

**Production env minimum:** `APP_ENV=production`, `JWT_SECRET` (≥32 bytes), `DATABASE_URL`, `CORS_ORIGINS`, `LOG_LEVEL=INFO`.

---

## 3. Version Audit

See [VERSION_MATRIX.md](./VERSION_MATRIX.md). Summary: all components at **0.1.0** / API **1.0**; build metadata fragmented across hardcoded strings.

---

## 4. Security Audit

| Control | Backend | Desktop | Flutter |
|---------|---------|---------|---------|
| JWT / refresh rotation | ✅ | N/A (stores tokens via IPC) | ✅ Secure storage |
| Secret encryption at rest | ✅ Fernet for integration keys | N/A | N/A |
| CORS | ⚠️ Default localhost | N/A | N/A |
| Security headers | ✅ CSP, X-Frame-Options, etc. | ⚠️ No renderer CSP | N/A |
| Electron hardening | N/A | ✅ contextIsolation, sandbox, no nodeIntegration | N/A |
| IPC surface | N/A | ⚠️ Unvalidated keys; DNS resolve on user host | N/A |
| Android permissions | N/A | N/A | ✅ Manifest reviewed M11 |
| iOS local network | N/A | N/A | ✅ Usage string present (M11X) |
| Demo mode bypass | N/A | ⚠️ **Preview mode always visible** | N/A |
| Discovery SSRF probe | ⚠️ Public `validate-host` | N/A | N/A |

---

## 5. Performance Audit

| Item | Finding |
|------|---------|
| Background timers | Tally scheduler (5-min floor), backup poll 15 min, audit retention 24h — acceptable |
| mDNS | Continuous while backend running — expected for LAN discovery |
| Memory leaks | No systematic leak detected in audit; no unbounded listener patterns in connection flow |
| Slow request threshold | 750 ms logged on backend |
| Large lists | Desktop/mobile use pagination patterns in inventory/sales |
| Image cache | Desktop `ProductImageService` localStorage cache with quota fallback |

---

## 6. Database Audit

| Item | Status |
|------|--------|
| Migration count | **33** files (`0001` → `0033_tally_connectivity`) |
| Alembic head | `0033_tally_connectivity` |
| Index/FK coverage | Documented in schema docs; no structural tests for 0027–0030 (DB-001) |
| Backup/restore | Enterprise backup engine tested; `custom_access_roles` missing from catalog (BACK-007) |
| Seed data | Reference seed scripts present |
| Migration test whitelists | **Stale** — capped at `0014` (BACK-004) |

---

## 7. Dependency Audit

See [DEPENDENCY_AUDIT.md](./DEPENDENCY_AUDIT.md).

**Summary:** `pnpm audit` reports **23 vulnerabilities** (1 critical, 5 high) — primarily dev/build toolchain (Vite, Electron). Python deps use minimum-version pins without lockfile in repo.

---

## 8. Release Configuration

| Platform | Build compiles | Icons | Signing | Installer config |
|----------|----------------|-------|---------|------------------|
| Windows Desktop | ✅ Vite + Electron | ✅ `.ico` | ❌ M12 | ❌ M12 |
| macOS Desktop | ✅ | ✅ `.icns` | ❌ M12 | ❌ M12 |
| Android | ✅ | ⚠️ Template launcher | ❌ Debug keystore | ❌ M12 |
| iOS | ✅ Scaffold | ⚠️ Template AppIcon | ❌ Manual Xcode | ❌ M12 |
| Server | ✅ | N/A | TLS via env | ❌ M12 |

**Bundle IDs:** Android `com.webstudio.webstudio_ims` vs iOS `com.webstudio.webstudioIms` — **mismatch**.

---

## 9. File System Audit

| Path | Purpose | Cross-platform |
|------|---------|----------------|
| `userData/webstudio_*.json` | Desktop config/storage | ✅ Electron |
| `webstudio-client.log` | Desktop logs | ✅ |
| Backend backup dir | Configurable via settings | ✅ |
| Temp upload paths | Backend product images | ✅ |
| Flutter Hive/SharedPreferences | Offline queue, prefs | ✅ |

---

## 10. Test Coverage Audit

| Suite | Count | Last run (11Y) | Status |
|-------|-------|----------------|--------|
| Backend pytest | 328 collected | **293 pass, 6 fail, 27 errors, 2 skip** (~8 min, requires PostgreSQL) | ⚠️ Fixture/session isolation (BACK-010) |
| Backend network (11X) | 9 | 9/9 pass | ✅ |
| Desktop Vitest | 95 | 95/95 pass | ✅ |
| Flutter unit + QA | 121 | 121/121 pass | ✅ |
| Flutter integration | 9 | Pass in CI script | ✅ Logic-level, not device E2E |
| shared-kernel / api-client | 0 | — | ⚠️ |

See [NETWORK_DISCOVERY_TEST_REPORT.md](../m11x/NETWORK_DISCOVERY_TEST_REPORT.md) for 11X coverage.

---

## 11. Installation Readiness

| Scenario | Ready | Notes |
|----------|-------|-------|
| Fresh server + DB | ✅ | Docker/scripts documented |
| Fresh client connect | ✅ | mDNS + manual (11X) |
| Upgrade (same DB) | ✅ | Alembic upgrade |
| Rollback | ⚠️ | Backup restore tested; installer rollback N/A |
| Windows Service | ❌ | M12 scope |
| Firewall docs | ✅ | `docs/network/NETWORK_REQUIREMENTS.md` |

---

## 12. Documentation Audit

| Document set | Sync status |
|--------------|-------------|
| M11 QA reports | ✅ Current |
| M11X network discovery | ✅ Current |
| Deployment guides | ⚠️ Some refs still cite RN mobile |
| OpenAPI spec | ⚠️ Placeholder (`paths: {}`) |
| ADR mDNS | ⚠️ Still marked TBD in ADR-0010 |

---

## 13. Cleanup Performed

This audit pass **did not remove code** — only verification and documentation. Recommended cleanup (M12 first sprint):

- Remove or archive `apps/mobile` (legacy RN) from workspace
- Gate desktop Preview mode behind `development` / build flag
- Update migration test whitelists to head `0033`
- Unify bundle identifiers and display names
- Wire CI workflows (replace placeholders)

---

## 14. Findings by Severity

### Critical (0)

None identified in application runtime code.

### High — Must resolve before customer release

| ID | Issue |
|----|-------|
| 11Y-H01 | Desktop **Preview/demo mode** ungated — bypasses server authentication |
| 11Y-H02 | **No release signing** (Android debug keystore; no desktop notarization) |
| 11Y-H03 | **CI/CD placeholders** — no automated regression gate |
| 11Y-H04 | **No installer tooling** (electron-builder, release APK/IPA pipeline) |

### Medium — Resolve during M12

| ID | Issue |
|----|-------|
| 11Y-M01 | Version metadata fragmentation (`0.1.0-mvp`, hardcoded headers) |
| 11Y-M02 | Backend full pytest suite instability without DB / fixture isolation |
| 11Y-M03 | Rate limiting flag without middleware |
| 11Y-M04 | 23 npm audit findings (incl. 1 critical in dev deps) |
| 11Y-M05 | Legacy `apps/mobile` in workspace |
| 11Y-M06 | OpenAPI spec placeholder |
| 11Y-M07 | Android/iOS bundle ID mismatch |

### Low — Backlog

Orphan desktop components (DESK-008), UpdateService stub, OpenAPI TBD, deferred items in KNOWN_ISSUES_REPORT.

---

## 15. Cross-Reference

| Report | Path |
|--------|------|
| Release checklist | [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md) |
| Version matrix | [VERSION_MATRIX.md](./VERSION_MATRIX.md) |
| Dependency audit | [DEPENDENCY_AUDIT.md](./DEPENDENCY_AUDIT.md) |
| Deployment checklist | [PRODUCTION_DEPLOYMENT_CHECKLIST.md](./PRODUCTION_DEPLOYMENT_CHECKLIST.md) |
| Engineering signoff | [FINAL_ENGINEERING_SIGNOFF.md](./FINAL_ENGINEERING_SIGNOFF.md) |
