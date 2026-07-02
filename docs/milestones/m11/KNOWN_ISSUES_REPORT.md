---
Title: Milestone 11 — Known Issues Report
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related Documents: docs/milestones/m11/SYSTEM_QA_REPORT.md
---

# Known Issues Report

All issues discovered during Milestone 11 QA. Each entry includes severity, root cause, recommended fix, and disposition.

**Legend:** Fixed = corrected in this milestone | Deferred = accepted for post-M11 | Open = not yet fixed

---

## Critical

| ID | Component | Issue | Severity | Root Cause | Recommended Fix | Fixed | Deferred |
|----|-----------|-------|----------|------------|-----------------|-------|----------|
| — | — | No critical production blockers identified | — | — | — | — | — |

---

## High

| ID | Component | Issue | Severity | Root Cause | Recommended Fix | Fixed | Deferred |
|----|-----------|-------|----------|------------|-----------------|-------|----------|
| DESK-001 | Desktop Audit | Export buttons ignore `audit:export` permission | High | `canExport` only checks active filters | Gate export on `audit:export` permission | **Yes** | — |
| DESK-002 | Desktop exports | Report and security exports bypass `RetryingApiClient` | High | Raw `fetch` without 401 refresh/retry | Route exports through shared client or add refresh wrapper | **Yes** | — |
| DESK-003 | Desktop build | TypeScript typecheck fails (2 errors) | High | Null session in SettingsPage; `inventoryId: null` vs `undefined` in search types | Fix null guards and align SearchResult type | **Yes** | — |
| BACK-001 | Backend Brands API | `GET /api/v1/brands/{id}` returned 422 | High | `BrandsViewDep` used but not imported in `brands.py` | Add import | **Yes** | — |
| BACK-002 | Backend Users API | Archive/unlock/restore endpoints crash with TypeError | High | `_serialize_detail()` requires `permissions` kwarg; three endpoints omitted it | Resolve permissions via `PermissionResolver` | **Yes** | — |
| BACK-003 | Backend errors | Brand restore 410 response failed envelope validation | High | `GONE` not in `ErrorCode` literal | Add `GONE` to error schema | **Yes** | — |
| MOB-001 | Flutter E2E | No `integration_test` suite for device flows | High | M11 scope was unit/QA logic tests only | Add integration_test for login, barcode, offline on device | No | **Yes** |

---

## Medium

| ID | Component | Issue | Severity | Root Cause | Recommended Fix | Fixed | Deferred |
|----|-----------|-------|----------|------------|-----------------|-------|----------|
| DESK-004 | Desktop Tally | Tally settings write gated by `settings:modify` not `tally:configure` | Medium | `useTallySettings` uses generic settings write permission | Align with granular Tally permissions | No | **Yes** |
| DESK-005 | Desktop Tally | TallyService swallows dashboard/status errors | Medium | `catch { return null }` with no UI signal | Surface error state to dashboard widget | No | **Yes** |
| DESK-006 | Desktop search | GlobalSearchService returns `[]` on any failure | Medium | Silent catch hides backend/network errors | Return partial results + error flag | No | **Yes** |
| DESK-007 | Desktop tests | 3/18 Vitest files failing | Medium | Stale expectations (nav labels, spec line order) | Update tests to match current UX | **Yes** | — |
| BACK-004 | Backend tests | 6 migration revision whitelist tests fail | Medium | Whitelists capped at `0014`; head is `0030` | Update allowed revisions to `0030_brand_hard_delete` | No | **Yes** |
| BACK-005 | Backend tests | `test_location_archive_preview_and_transfer` 404 | Medium | `/archive-preview` endpoint never implemented | Implement preview API or remove stale test | No | **Yes** |
| BACK-006 | Backend auth | `session_timeout_minutes` not enforced server-side | Medium | Setting is advisory; JWT TTL is fixed | Enforce idle timeout on refresh or document as client-only | No | **Yes** |
| BACK-007 | Backend backup | `custom_access_roles` tables missing from `BACKUP_DATABASE_TABLES` | Medium | Catalog not updated for migration 0029 | Add tables to completeness catalog | No | **Yes** |
| BACK-008 | Backend Tally | `/sync/retry` aliases `/sync/trigger` | Medium | No failed-invoice retry semantics | Implement scoped retry or document behavior | No | **Yes** |
| BACK-009 | Backend health | `/health/ready` migrations check hardcoded `"ok"` | Medium | No Alembic revision validation | Compare `alembic_version` to expected head | No | **Yes** |
| BACK-010 | Backend tests | 13 pytest errors (health/platform/performance) | Medium | DB session fixture scope/isolation when collected with full suite | Fix conftest session sharing or mark as integration | No | **Yes** |
| BACK-011 | Backend Tally test | `test_tally_xml_processing_creates_sale` setup error | Medium | Duplicate brand "ASUS" in fixture collision | Isolate test data or use unique brand names | No | **Yes** |
| MOB-002 | Flutter auth | Post-login always navigates to `/dashboard` | Medium | Hardcoded route vs `defaultRouteForUser()` | Use permission-based default route | No | **Yes** |
| MOB-003 | Flutter barcode | Scanner skips `DevicePermissions.ensure(camera)` | Medium | Relies on `mobile_scanner` implicit permission | Pre-request camera like product image flow | No | **Yes** |
| MOB-004 | Flutter Android | `INTERNET` not in main manifest | Medium | Only in debug/profile overlays | Verify release merged manifest; add if missing | No | **Yes** |
| SEC-001 | Backend upload | Product image upload trusts Content-Type only | Medium | No magic-byte check on upload path | Reuse `_content_looks_like_image` before write | No | **Yes** |
| SEC-002 | Backend backup | Backup import has no upload size cap | Medium | Full file read into memory | Add max size middleware | No | **Yes** |
| TEST-001 | Backend security | No SQL injection fuzz tests | Medium | Test gap | Add malicious payload tests for search/filter | No | **Yes** |

---

## Low

| ID | Component | Issue | Severity | Root Cause | Recommended Fix | Fixed | Deferred |
|----|-----------|-------|----------|------------|-----------------|-------|----------|
| DESK-008 | Desktop | Orphan `TallyPage`, `BulkOperationsDialog`, `ChangeRoleDialog` | Low | Legacy/unwired components | Wire or remove in M12 cleanup | No | **Yes** |
| DESK-009 | Desktop | Duplicate `parseApiError` in inventory hook | Low | Local copy vs shared lib | Import from `lib/apiError.ts` | No | **Yes** |
| DESK-010 | Desktop | `UpdateService` stub only | Low | Reserved for auto-updater | Implement in release milestone | No | **Yes** |
| BACK-012 | Backend Tally | `retry_count` column never incremented | Low | Schema ahead of implementation | Wire on retry or deprecate column | No | **Yes** |
| BACK-013 | Backend backup | Test env uses stub SQL dump unless `WEBSTUDIO_BACKUP_REAL_DUMP=1` | Low | By design for speed | Run real dump in staging QA | No | **Yes** |
| MOB-005 | Flutter | QR/NFC/BT scan throw `UnimplementedError` | Low | Camera-only by design | Document; implement if required | No | **Yes** |
| MOB-006 | Flutter analyze | 33 info/warnings (const, deprecated dropdown) | Low | Style/deprecation | Address in cleanup pass | No | **Yes** |
| DB-001 | Database | No structural tests for migrations 0027–0030 | Low | Coverage gap | Add index/FK tests for new migrations | No | **Yes** |

---

## Informational (accepted)

| ID | Notes |
|----|-------|
| INFO-001 | Incremental backup falls back to full with warning |
| INFO-002 | Tally HTTP client single-attempt (no exponential retry) — acceptable for LAN |
| INFO-003 | Flutter inventory/catalogue tablet uses bottom sheets; Sales has master-detail (10J known difference) |
| INFO-004 | Live Tally server unavailable — UAT checklist deferred to post-connectivity |

---

## Issue count summary

| Severity | Total | Fixed | Open | Deferred |
|----------|-------|-------|------|----------|
| Critical | 0 | 0 | 0 | 0 |
| High | 7 | 6 | 0 | 1 |
| Medium | 17 | 1 | 0 | 16 |
| Low | 8 | 0 | 0 | 8 |
