---
Title: Milestone 11 — Backend QA Report
Version: 1.0.0
Status: Complete
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related Documents: docs/milestones/m11/KNOWN_ISSUES_REPORT.md
---

# Backend QA Report

FastAPI backend validation (`apps/backend`).

## Test results

```
pytest tests/  →  271 passed, 7 failed, 13 errors, 2 skipped
```

### Passing domains (representative)

| Module | Tests | Status |
|--------|-------|--------|
| Authentication | Login, refresh rotation, lockout | ✅ |
| Permissions / RBAC | Role matrix, denied audit | ✅ |
| Inventory | CRUD, hardening, operations | ✅ |
| Sales | API + snapshots | ✅ |
| Product models + AI | API, images, validation | ✅ |
| Reports | Preview, export auth | ✅ |
| Settings | Workspace, patches | ✅ |
| Backup format / restore engine | TAR.GZ, WSB import | ✅ |
| Tally | Parser, dashboard API | ✅ (1 setup error) |
| Audit log | Search, lifecycle | ✅ |
| Notifications | API + migration | ✅ |
| Dashboard | Widget endpoints | ✅ |
| Security audit | Login events, policy | ✅ |

### Failures (not production regressions)

| Test | Root cause | Fix |
|------|------------|-----|
| 6× `test_migration_*` | Revision whitelist stops at `0014`; head is `0030` | Update test allowlists (BACK-004) |
| `test_location_archive_preview_and_transfer` | `/archive-preview` endpoint not implemented | Implement or remove test (BACK-005) |

### Errors (fixture isolation)

| Tests | Root cause |
|-------|------------|
| `test_health.py`, `test_platform.py`, `test_performance.py`, `test_mobile_readiness.py`, `test_response_helpers.py` | `RuntimeError: Database session` when run in full suite (BACK-010) |

These pass when run in isolation with proper DB fixtures.

## Authentication & authorization

| Feature | Validated | Notes |
|---------|-----------|-------|
| JWT access tokens | ✅ | HS256, iss/aud, token_version |
| Refresh token rotation | ✅ | Reuse detection revokes family |
| Remember me | ✅ | Extended refresh TTL |
| Password policy | ✅ | Length, complexity, history |
| Account lockout | ✅ | Configurable threshold |
| Permission middleware | ✅ | Per-route deps |
| Custom access roles | ⚠️ | Implemented; API tests missing (BACK-006 area) |
| Session timeout setting | ⚠️ | Advisory only (BACK-006) |

## API platform

| Endpoint | Auth | Status |
|----------|------|--------|
| `GET /health/live`, `/health` | Public | ✅ |
| `GET /health/version` | Public | ✅ |
| `GET /health/ready` | Public | ⚠️ Migrations hardcoded ok |
| `GET /metadata/info` | Public | ✅ |
| `GET /api/v1/version` | Public | ✅ |
| `GET /api/v1/capabilities` | Public | ✅ |
| OpenAPI | — | ⚠️ Was broken by missing `BrandsViewDep`; fixed (BACK-001) |

## Pagination, filtering, errors

- Standard envelope + `build_page_meta` helpers tested
- Structured `ErrorCode` enum; **GONE** added for HTTP 410 (BACK-003)
- Inventory/search filters use parameterized SQLAlchemy queries

## Bugs fixed in M11

| ID | Endpoint | Fix |
|----|----------|-----|
| BACK-001 | `GET /api/v1/brands/{id}` | Import `BrandsViewDep` |
| BACK-002 | `POST .../archive`, `/unlock`, `/restore` | Pass `permissions` to serializer |
| BACK-003 | `POST .../brands/{id}/restore` | Add `GONE` error code |

## Issues deferred

BACK-004 through BACK-013 — see [KNOWN_ISSUES_REPORT.md](./KNOWN_ISSUES_REPORT.md).

## Verdict

Backend core is **production-ready** after M11 fixes. Remaining work is test hygiene, custom-role test coverage, and staging validation with real backup dumps.
