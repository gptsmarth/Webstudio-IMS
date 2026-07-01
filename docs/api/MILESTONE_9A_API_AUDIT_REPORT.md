# Milestone 9A — Enterprise Backend API Audit Report

**Date:** 2026-06-30  
**Scope:** `apps/backend/src/webstudio_backend/`  
**Status:** Audit complete — **stop for review**

---

## Executive Summary

The WEBSTUDIO IMS backend already follows a **de facto enterprise contract**: JSON envelope responses, centralized error handling, RBAC on protected routes, and repository-level pagination. Milestone 9A confirmed consistency across 20 router modules (~130+ routes) and applied **targeted standardization** without rewriting working business logic.

### Changes Applied in 9A

| Area | Change |
|------|--------|
| **Version API** | Added `GET /api/v1/version` (backend, schema, API, build, min client versions) |
| **Capabilities API** | Added `GET /api/v1/capabilities` (modules, AI, Tally, backup, feature flags) |
| **Pagination meta** | Standardized `has_next`, `has_previous`, `total` on all paginated list endpoints |
| **Shared helpers** | Added `api/response_helpers.py` (`build_envelope`, `build_page_meta`) |
| **Error codes** | Extended `ErrorCode` with `NOT_CONFIGURED`, `API_ERROR`, `TIMEOUT`, `QUOTA_EXCEEDED` |
| **Config** | Added `min_desktop_version`, `min_mobile_version`, `build_version` settings |

### Deferred (Recommended for 9B+)

- Migrate remaining 16 routers to shared `build_envelope` (currently duplicated locally)
- Populate `docs/api/openapi/webstudio-ims-api-v1.yaml` from live FastAPI schema
- Add pagination to catalogue list endpoints (brands, locations, product-models)
- Normalize `audit_logs` path to kebab-case alias `/api/v1/audit-logs`
- Unify `AppError` vs `HTTPException` usage in auth/users/setup routers

---

## 1. Response Contract

### Success Envelope (Standard)

All JSON API endpoints return:

```json
{
  "data": { },
  "meta": { },
  "request_id": "uuid",
  "correlation_id": "uuid",
  "timestamp": "2026-06-30T00:00:00+00:00"
}
```

**Schema:** `api/schemas/responses.py` → `Envelope[T]`, `ResponseMeta`

**Headers (all responses):** `X-Request-ID`, `X-Correlation-ID`, `API-Version`

### Error Envelope (Standard)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": [{ "field": "model_number", "code": "VALIDATION_ERROR", "message": "..." }]
  },
  "request_id": "uuid",
  "correlation_id": "uuid",
  "timestamp": "..."
}
```

**Schema:** `api/schemas/errors.py` → `ErrorResponse`, `ErrorBody`, `ErrorDetail`  
**Handlers:** `core/exceptions.py` → `AppError`, `RequestValidationError`, `HTTPException`, unhandled `Exception`

### Exceptions (By Design)

| Route type | Format |
|------------|--------|
| `GET /api/v1/product-images/proxy` | Raw image bytes |
| `GET /api/v1/reports/export` | File download (`Content-Disposition`) |
| `GET /api/v1/security/export` | File download |
| `GET /api/v1/settings/backups/*/download` | File download |

---

## 2. Pagination Audit

### Standard Query Parameters

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `page` | int | 1 | `ge=1` |
| `page_size` | int | 50 | `ge=1`, `le=100` |

**Repository layer:** `infrastructure/database/repositories/pagination.py` → `PageParams`, `PageResult`, `paginate()`

### Standard Response Meta (After 9A)

| Field | Type | Description |
|-------|------|-------------|
| `page` | int | Current page (1-based) |
| `page_size` | int | Items per page |
| `total_items` | int | Total matching records |
| `total` | int | Alias of `total_items` |
| `total_pages` | int | Computed page count |
| `has_next` | bool | `page < total_pages` |
| `has_previous` | bool | `page > 1` |
| `has_more` | bool | Alias of `has_next` (legacy) |

**Legacy aliases (inventory only):** `total_records`, `current_page` — retained for desktop backward compatibility.

### Paginated Endpoints ✅

| Endpoint | Default `page_size` | Sort | Search |
|----------|---------------------|------|--------|
| `GET /api/v1/inventory` | 50 | `sort=field:dir` | `search` |
| `GET /api/v1/sales` | 50 | `sort` / `sort_field` | `search` |
| `GET /api/v1/users` | 50 | — | — |
| `GET /api/v1/notifications` | 50 | — | — |
| `GET /api/v1/audit_logs` | 50 | — | filters |
| `GET /api/v1/audit_logs/lifecycle/by-serial/{serial}` | 50 | — | — |
| `GET /api/v1/audit_logs/by-entity/{type}/{id}` | 50 | — | — |
| `GET /api/v1/audit_logs/by-inventory-item/{id}` | 50 | — | — |
| `GET /api/v1/reports/inventory` | 50 | — | filters |
| `GET /api/v1/reports/sales` | 50 | — | filters |
| `GET /api/v1/reports/audit` | 50 | — | filters |
| `GET /api/v1/reports/notifications` | 50 | — | filters |
| `GET /api/v1/settings/backups/admin/history` | **25** ⚠️ | — | filters |
| `GET /api/v1/settings/backups/mobile/history` | **25** ⚠️ | — | — |

⚠️ **Inconsistency (documented, not changed):** Backup history defaults to `page_size=25` while other lists use 50. Intentional for admin UI density.

### Unpaginated List Endpoints ⚠️

| Endpoint | Notes |
|----------|-------|
| `GET /api/v1/brands` | Loads all, sorts in Python |
| `GET /api/v1/locations` | Loads all |
| `GET /api/v1/product-models` | Loads all; filter `archived` |
| `GET /api/v1/admin/integration-keys` | Loads all |

**Recommendation (9B):** Add optional pagination when catalogue exceeds ~500 rows.

---

## 3. Filtering & Sorting Audit

### Inventory (`/api/v1/inventory`)

- **Filters:** `status`, `brand_id`, `location_id`, `product_model_id`, `include_archived`, date ranges
- **Search:** `search` (serial, model number, notes)
- **Sort:** `sort=field:direction` — allowed: `serial_number`, `status`, `color`, `created_at`, `updated_at`, `purchase_date`

### Sales (`/api/v1/sales`)

- **Filters:** `date_from`, `date_to`, `brand_id`, `location_id`, `product_model_id`, `user_id`, `invoice_number`, `customer_name`, `payment_mode`, `sale_source`
- **Search:** `search`
- **Sort:** `sort` or `sort_field` + `sort_direction`

### Audit (`/api/v1/audit_logs`)

- **Filters:** `entity_type`, `entity_id`, `action`, `source`, `user_id`, `date_from`, `date_to`
- **Sub-routes:** by serial, by entity, by inventory item

### Reports (`/api/v1/reports/*`)

- Shared `ReportFilters` via `infrastructure/repositories/report_filters.py`
- Export: `GET /api/v1/reports/export?report_type=&format=`

### Notifications (`/api/v1/notifications`)

- **Filters:** `category`, `type`, `severity`, `status`, `is_resolved`, date range

### Users (`/api/v1/users`)

- **Filters:** `role`, `status`, `search`

### Catalogue

- Brands/Locations: no query filters (full list)
- Product models: `archived` boolean filter only

**Assessment:** Filtering is **consistent within each domain**. Cross-module naming is aligned (`date_from`/`date_to`, `brand_id`, `location_id`).

---

## 4. Validation & Error Codes

### Field-Level Validation

FastAPI `RequestValidationError` → `422` with per-field `details[]`:

```json
{ "field": "body.model_number", "code": "VALIDATION_ERROR", "message": "..." }
```

### Domain Errors (`AppError`)

| Code | HTTP | Used By |
|------|------|---------|
| `VALIDATION_ERROR` | 400/422 | General |
| `NOT_FOUND` | 404 | Inventory, catalogue, notifications |
| `PERMISSION_DENIED` | 403 | RBAC |
| `INVALID_CREDENTIALS` | 401 | Auth |
| `SERVICE_UNAVAILABLE` | 503 | AI disabled, setup |
| `RATE_LIMITED` | 429 | AI providers |
| `API_ERROR` | 502 | AI providers *(added 9A)* |
| `TIMEOUT` | 502 | AI providers *(added 9A)* |
| `QUOTA_EXCEEDED` | 502 | AI providers *(added 9A)* |
| `NOT_CONFIGURED` | 503 | AI providers *(added 9A)* |
| `SERIAL_NUMBER_DUPLICATE` | 409 | Inventory |
| `ALREADY_SOLD` | 409 | Inventory |
| `NOTIFICATION_ALREADY_RESOLVED` | 409 | Notifications |
| `LOCATION_HAS_INVENTORY` | 409 | Locations |

### Mixed Error Styles ⚠️

| Pattern | Routers |
|---------|---------|
| `raise AppError(...)` | inventory, brands, locations, product_models, notifications, reports |
| `raise HTTPException(...)` | auth, users, setup, audit_logs, sales, settings, tally |

Both produce the **same JSON error shape** via global handlers. `HTTPException` loses semantic codes (e.g. 409 → generic `VALIDATION_ERROR`).

---

## 5. Version & Capabilities Endpoints

### Before 9A

| Path | Purpose |
|------|---------|
| `GET /health/version` | Partial version info |
| `GET /health/live` | Liveness + version |
| `GET /metadata/info` | Service metadata |

### After 9A

#### `GET /api/v1/version` (Public)

```json
{
  "data": {
    "backend_version": "0.1.0",
    "schema_version": "0026_backup_enterprise",
    "api_version": "1.0",
    "build_version": "0.1.0",
    "environment": "development",
    "min_desktop_version": "0.1.0",
    "min_mobile_version": "0.1.0",
    "min_client_version": "0.1.0"
  }
}
```

`build_version` resolves from `WEBSTUDIO_BUILD_VERSION` → `WEBSTUDIO_GIT_COMMIT` → config → `app_version`.

#### `GET /api/v1/capabilities` (Public)

```json
{
  "data": {
    "installed_version": "0.1.0",
    "api_version": "1.0",
    "schema_version": "...",
    "modules": { "inventory": true, "tally": false, ... },
    "ai": { "enrichment_enabled": true, "primary_provider": "gemini", ... },
    "tally_enabled": false,
    "backup_enabled": true,
    "reports_enabled": true,
    "feature_flags": { ... }
  }
}
```

**Implementation:** `api/routers/platform.py`, `services/platform_info_service.py`

---

## 6. Router Inventory

| Router | Prefix | Routes | Auth | Pagination |
|--------|--------|--------|------|------------|
| health | `/health` | 4 | Public | — |
| metadata | `/metadata` | 1 | Public | — |
| **platform** | `/api/v1` | **2** | **Public** | — |
| setup | `/api/v1/setup` | 3 | Mixed | — |
| auth | `/api/v1/auth` | 11 | Mixed | sessions list |
| security | `/api/v1/security` | 2 | Admin | — |
| users | `/api/v1/users` | 13 | Admin | ✅ |
| integration_keys | `/api/v1/admin/integration-keys` | 5 | Admin | — |
| brands | `/api/v1/brands` | 6 | RBAC | — |
| locations | `/api/v1/locations` | 6 | RBAC | — |
| product_models | `/api/v1/product-models` | 9 | RBAC | — |
| product_images | `/api/v1/product-images` | 1 | Auth | — |
| inventory | `/api/v1/inventory` | 9 | RBAC | ✅ |
| sales | `/api/v1/sales` | 2 | RBAC | ✅ |
| dashboard | `/api/v1/dashboard` | 3 | Auth | — |
| notifications | `/api/v1/notifications` | 4 | RBAC | ✅ |
| reports | `/api/v1/reports` | 5 | RBAC | ✅ |
| audit_logs | `/api/v1/audit_logs` | 5 | RBAC | ✅ |
| settings | `/api/v1/settings` | 33 | RBAC | partial |
| tally | `/api/v1/integrations/tally` | 6 | RBAC | sync-log |

---

## 7. OpenAPI / Documentation

| Item | Status |
|------|--------|
| FastAPI auto-docs (`/docs`) | ✅ Dev only |
| `docs/api/openapi/webstudio-ims-api-v1.yaml` | ⚠️ **Placeholder** (`paths: {}`) |
| Endpoint descriptions | ✅ Added on platform routes; sparse elsewhere |
| Duplicate schemas | None detected in Pydantic models |
| Request examples | ⚠️ Minimal in OpenAPI |

**Recommendation:** Export live schema via `app.openapi()` in CI and commit to `docs/api/openapi/`.

---

## 8. Naming Conventions

| Convention | Standard | Exceptions |
|------------|----------|------------|
| API prefix | `/api/v1/` | health, metadata at root |
| Resource paths | kebab-case | `audit_logs` uses underscore |
| Query params | snake_case | Consistent |
| JSON fields | snake_case | Consistent |
| Error codes | SCREAMING_SNAKE | Consistent |

---

## 9. Client Readiness Matrix

| Client | Ready | Notes |
|--------|-------|-------|
| Electron Desktop | ✅ | Uses envelope + pagination; inventory legacy aliases preserved |
| Flutter Mobile | ✅ | `/api/v1/version` + `/api/v1/capabilities` for discovery |
| Future Web Portal | ✅ | Standard contract; CORS configured |
| External Integrations | ⚠️ | Integration keys API exists; OpenAPI spec needed |

---

## 10. Test & Build Results

| Check | Result | Notes |
|-------|--------|-------|
| App import / route registration | ✅ Pass | 21 top-level route groups |
| Ruff lint (new files) | ✅ Pass | `response_helpers`, `platform`, `platform_info_service` |
| Unit tests (`test_response_helpers`) | ✅ Ready | No DB required |
| Integration tests | ⚠️ Requires PostgreSQL | `conftest.py` runs migrations |
| Full backend suite | ⚠️ Not run (DB unavailable in audit environment) | Run locally: `pytest apps/backend/tests` |

### New Tests Added

- `tests/test_platform.py` — version + capabilities endpoints
- `tests/test_response_helpers.py` — pagination meta helper

---

## 11. Files Changed (9A)

```
apps/backend/src/webstudio_backend/
  api/response_helpers.py                    NEW
  api/routers/platform.py                    NEW
  api/schemas/responses.py                   has_next, has_previous, total
  api/schemas/errors.py                      extended ErrorCode
  core/config.py                             min_desktop/mobile, build_version
  services/platform_info_service.py          NEW
  app.py                                     register platform router
  api/routers/{inventory,sales,audit_logs,users,notifications,reports,settings}.py
                                             use build_page_meta

apps/backend/tests/
  test_platform.py                           NEW
  test_response_helpers.py                 NEW

docs/api/
  MILESTONE_9A_API_AUDIT_REPORT.md           NEW (this file)
```

---

## 12. Review Checklist

- [ ] Approve new `/api/v1/version` and `/api/v1/capabilities` contract
- [ ] Confirm pagination meta fields (`total`, `has_next`, `has_previous`) for desktop/mobile clients
- [ ] Decide on backup history `page_size=25` vs standardizing to 50
- [ ] Prioritize 9B: OpenAPI export, catalogue pagination, envelope helper migration
- [ ] Run full test suite with PostgreSQL before merge

---

*Generated as part of Milestone 9A — Enterprise Backend Audit & API Standardization.*
