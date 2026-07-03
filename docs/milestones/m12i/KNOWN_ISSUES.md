---
Title: Known Issues — Milestone 12I
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related Documents:
  - docs/milestones/m11/KNOWN_ISSUES_REPORT.md
  - docs/milestones/m12i/FINAL_PRODUCTION_READINESS_REPORT.md
---

# Known Issues — Release Candidate 0.1.0

Issues at final M12I validation. **Fixed in M12I** items are closed; **Deferred** items are accepted for post-RC; **Open** items need attention before GA.

**Legend:** Fixed | Deferred | Open

---

## Fixed in M12I

| ID | Component | Issue | Resolution |
|----|-----------|-------|------------|
| M12I-001 | Backend tests | 6 migration revision whitelist failures | `tests/helpers/migrations.py` — `assert_at_least_migration()` |
| M12I-002 | Backend tests | DB session / event loop errors in full suite | TestClient → AsyncClient; skip `close_db` in test lifespan |
| M12I-003 | Backend tests | AI enrichment tests hung (web image scrape) | Skip external scrape when `APP_ENV=test` |
| M12I-004 | Backend tests | Slow/hung teardown (30s graceful shutdown) | Graceful shutdown production-only |
| BACK-004 | Backend tests | Migration whitelist stale (M11) | **Fixed** (same as M12I-001) |
| BACK-010 | Backend tests | Health/platform/performance collection errors (M11) | **Fixed** (same as M12I-002) |

---

## High (deferred — not RC blockers for staging)

| ID | Component | Issue | Disposition |
|----|-----------|-------|-------------|
| MOB-001 | Flutter E2E | No `integration_test` device suite | **Deferred** — add before mobile GA |
| REL-02 | Release | No production code signing (desktop/mobile) | **Deferred** — configure certs in CI |
| REL-04 | QA | Staging acceptance drills not executed on packaged builds | **Open** — required before customer GA |

---

## Medium (deferred)

| ID | Component | Issue | Disposition |
|----|-----------|-------|-------------|
| DESK-004 | Desktop Tally | Tally settings use `settings:modify` not `tally:configure` | Deferred |
| DESK-005 | Desktop Tally | TallyService swallows dashboard errors | Deferred |
| DESK-006 | Desktop search | GlobalSearchService silent failure | Deferred |
| BACK-005 | Backend | Location archive-preview endpoint missing | Deferred |
| BACK-006 | Backend | `session_timeout_minutes` advisory only | Deferred |
| BACK-007 | Backend | `custom_access_roles` in backup catalog | Deferred |
| BACK-008 | Backend Tally | `/sync/retry` aliases trigger | Deferred |
| BACK-009 | Backend health | `/health/ready` migrations check hardcoded | Deferred |
| BACK-011 | Backend Tally | Fixture brand collision in one test | Deferred |
| MOB-002 | Flutter auth | Post-login always `/dashboard` | Deferred |
| MOB-003 | Flutter barcode | Camera permission not pre-requested | Deferred |
| MOB-004 | Flutter Android | `INTERNET` manifest verification | Deferred |
| SEC-001 | Backend upload | Content-Type only image validation | Deferred |
| SEC-002 | Backend backup | No upload size cap on import | Deferred |
| TEST-001 | Backend security | No SQL injection fuzz tests | Deferred |

---

## Low (deferred)

| ID | Component | Issue | Disposition |
|----|-----------|-------|-------------|
| DESK-008–010 | Desktop | Orphan components, duplicate helpers, UpdateService stub | Deferred |
| BACK-012–013 | Backend | Tally `retry_count` column; backup stub dump in test | Deferred |
| MOB-005–006 | Flutter | Unimplemented scan sources; analyze warnings | Deferred |
| DB-001 | Database | No structural tests for migrations 0027–0036 | Deferred |

---

## Informational (accepted)

| Item | Notes |
|------|-------|
| Preview/demo mode | May remain in dev builds; gate for production packaging per REL-01 |
| npm audit findings | Dev toolchain; track in dependency hardening sprint |
| iOS device testing | Requires physical devices and Apple developer account |
| Tally live sync | Requires customer Tally instance; validated by unit tests + staging drill |

---

## Issue trend

| Milestone | Critical | High open | Medium open |
|-----------|----------|-----------|-------------|
| M11 | 0 | 1 (MOB-001) | 15 |
| M12I | 0 | 2 (MOB-001, REL-04) | 15 (unchanged, deferred) |

**No new critical or high runtime defects** identified during M12I validation.
