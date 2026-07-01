# Milestone 9C — Mobile & Multi-Client Readiness Report

**Date:** 2026-06-27  
**Scope:** Backend multi-client preparation, desktop API-only audit, Flutter readiness (no Flutter build)  
**Status:** Audit complete — **stop for review**

---

## Executive Summary

The WEBSTUDIO IMS backend is **ready for multiple clients** (desktop, future Flutter, future web). All business workflows are exposed through authenticated REST APIs. Milestone 9C closed the highest-impact gaps for mobile: **unified search**, **sync state preparation**, **catalogue pagination**, and **server-side image upload**.

The desktop app already routes all data operations through 20 API service modules and does **not** connect to PostgreSQL directly. Remaining desktop gaps are **client-side optimizations** (full-list prefetch, localStorage image cache, raw `fetch` on binary exports) — not missing backend APIs.

### Changes Applied in 9C

| Area | Change |
|------|--------|
| **Sync state** | Added `GET /api/v1/sync/state` — server time, schema version, per-entity high-water marks |
| **Global search** | Added `GET /api/v1/search` — inventory, brands, locations, product models in one request |
| **Catalogue pagination** | Optional `page`, `page_size`, `search` on brands, locations, product-models (backward compatible when `page` omitted) |
| **Image upload** | Added `POST /api/v1/product-images/upload` — multipart upload, managed asset storage, audit trail |
| **Router registration** | Registered `sync` and `search` routers in `app.py` |
| **Desktop prep** | Added `PlatformService.ts` for `/version` and `/capabilities` (not yet wired on boot) |

### Deferred (Post-9C / Flutter Phase)

- Per-entity delta sync (`GET /sync/changes?since=`) — sync/state is preparation only
- Background job APIs for long-running backup/restore and large exports
- `pg_trgm` full-text search indexes
- Desktop: migrate `GlobalSearchService` to `/api/v1/search`
- Desktop: migrate `ProductImageService` localStorage cache to upload API
- Desktop: route report/security exports through `RetryingApiClient` for token refresh
- Desktop: call `PlatformService` on boot for version negotiation
- Parameterize `clientPlatform` header (`macos_desktop` → `ios` / `android` / `web`)

---

## 1. Workflow API Coverage Matrix

Every workflow below can be completed **API-only**. Desktop uses the listed service modules; no hidden local business logic.

| Workflow | Desktop Service | Key Endpoints | API-Only | Mobile Notes |
|----------|-----------------|---------------|----------|--------------|
| **Authentication** | `AuthenticationService` | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/change-password` | ✅ | Token refresh via `RetryingApiClient`; exports bypass refresh (see §5) |
| **Inventory** | `InventoryService` | `GET/POST /inventory`, `GET/PATCH/DELETE /inventory/{id}`, status/location/condition updates, bulk ops | ✅ | Paginated (`page`, `page_size`, `search`, `sort`); desktop prefetches all pages in hierarchy view |
| **Sales** | `SalesService` | `GET /sales`, `POST /sales`, `GET /sales/{id}` | ✅ | Paginated list with search |
| **Catalogue — Brands** | `BrandService` | `GET/POST /brands`, `GET/PATCH/DELETE /brands/{id}` | ✅ | Optional pagination + `search` (9C) |
| **Catalogue — Locations** | `LocationService` | `GET/POST /locations`, `GET/PATCH/DELETE /locations/{id}` | ✅ | Optional pagination + `search` (9C) |
| **Catalogue — Product Models** | `ProductModelService` | `GET/POST /product-models`, spec lookup, resolve-image, selling price | ✅ | Optional pagination + `search` (9C); AI spec lookup server-side |
| **Reports** | `ReportService` | `GET /reports/*`, `GET /reports/export` | ✅ | Export returns file stream (not JSON envelope) |
| **Notifications** | `NotificationService` | `GET /notifications`, mark read, dismiss | ✅ | Paginated |
| **Users** | `UserService` | Full CRUD, roles, password reset, lock/unlock | ✅ | Paginated list |
| **Audit** | `AuditService` | `GET /audit_logs`, lifecycle, by-entity, by-serial | ✅ | Paginated with filters |
| **Settings** | `SettingsService` | Company, preferences, AI, integrations, security | ✅ | All persisted server-side |
| **Backup** | `SettingsService` | `GET/POST /settings/backups`, restore, download | ✅ | Long operations synchronous; background jobs deferred |
| **Tally** | `TallyService` | Config, test, sync, logs, stats | ✅ | Module gated via capabilities |
| **Dashboard** | `DashboardService` | `GET /dashboard/summary`, distributions | ✅ | Aggregated server-side |
| **Setup** | `SetupService` | `GET /setup/status`, initialize | ✅ | Public pre-auth |
| **Platform** | `PlatformService` *(new)* | `GET /version`, `GET /capabilities` | ✅ | Public; desktop not yet calling on boot |
| **Search** | `GlobalSearchService` *(client)* | `GET /search` *(new)* | ✅ | Desktop still uses multi-fetch client search |
| **Sync** | — | `GET /sync/state` *(new)* | ✅ | Preparation for offline; no delta endpoints yet |
| **Media** | `ProductImageService` *(local)* | `GET /product-images/proxy`, `POST /product-images/upload` *(new)* | ✅ | Desktop caches in localStorage; mobile should use upload |

---

## 2. Authentication & Token Refresh

### Backend

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `POST /api/v1/auth/login` | Public | Issue access + refresh tokens |
| `POST /api/v1/auth/refresh` | Refresh token | Rotate access token |
| `POST /api/v1/auth/logout` | Bearer | Invalidate session |
| `GET /api/v1/auth/me` | Bearer | Current user profile |

All protected routes require `Authorization: Bearer <access_token>`. RBAC enforced per-module via dependency injection (`*ViewDep`, `*EditDep`, etc.).

### Desktop Client

`RetryingApiClient` (`apps/desktop/src/services/api/client.ts`):

- On `401`, attempts single refresh via `AuthenticationService.refresh()`
- Retries original request with new access token
- Network errors: up to 3 attempts with exponential backoff

### Gaps for Mobile

| Gap | Severity | Recommendation |
|-----|----------|----------------|
| Report/security export uses raw `fetch` | Medium | Route through shared client with refresh interceptor |
| No `clientPlatform` negotiation on boot | Low | Call `GET /version` + compare `min_mobile_version` |
| Refresh token storage | — | Flutter: secure storage (Keychain/Keystore) |

---

## 3. Offline Sync Preparation

### New: `GET /api/v1/sync/state`

Returns:

```json
{
  "data": {
    "server_time": "2026-06-27T12:00:00+00:00",
    "app_version": "0.1.0",
    "schema_version": "0027",
    "sync_token": "2026-06-27T12:00:00+00:00",
    "high_water_marks": {
      "inventory": "2026-06-27T11:55:00+00:00",
      "sales": "...",
      "notifications": "...",
      "audit_logs": "...",
      "product_models": "...",
      "brands": "...",
      "locations": "..."
    },
    "poll_interval_seconds": 60,
    "supported_entities": ["inventory", "sales", ...],
    "incremental_sync": {
      "status": "preparation",
      "note": "Use high_water_marks as baseline cursors..."
    }
  }
}
```

**Flutter strategy (future):**

1. On login, fetch sync state and store high-water marks locally
2. Poll periodically (60s default) to detect server changes
3. When delta APIs ship, use marks as `since` cursors per entity
4. Queue offline mutations with idempotency keys (not yet in API)

---

## 4. Image Upload & Download

### Download

| Method | Endpoint | Use Case |
|--------|----------|----------|
| Proxy | `GET /api/v1/product-images/proxy?url=` | Fetch external HTTPS images through backend (CORS bypass) |
| Static | `GET /assets/product-images/{id}.{ext}` | Managed images stored on server filesystem |
| Resolve | `POST /api/v1/product-models/{id}/resolve-image` | Auto-discover image via AI/scraper |

### Upload (New in 9C)

`POST /api/v1/product-images/upload`

- **Auth:** `product_models.edit` permission
- **Body:** `multipart/form-data` — `product_model_id` (UUID), `file` (image)
- **Limits:** 5 MB; JPEG, PNG, WebP, GIF
- **Storage:** `apps/desktop/public/assets/product-images/` (managed assets dir)
- **Response:** `{ product_model_id, product_image_url, source: "upload" }`
- **Audit:** Field update recorded via `ProductModelRepository.update`

### Mobile Recommendation

Flutter should **always** use `POST /upload` or `resolve-image` — never local-only storage. Serve images via absolute URL: `{apiBaseUrl}/assets/product-images/{filename}`.

---

## 5. Large Lists, Pagination & Search

### Paginated Endpoints (Standard Contract)

Query: `page` (≥1), `page_size` (1–100, default 50)  
Meta: `page`, `page_size`, `total_items`, `total`, `total_pages`, `has_next`, `has_previous`

| Endpoint | Search | Sort | Notes |
|----------|--------|------|-------|
| `GET /inventory` | ✅ | ✅ | Primary operational list |
| `GET /sales` | ✅ | ✅ | |
| `GET /users` | — | — | |
| `GET /notifications` | — | — | |
| `GET /audit_logs` | filters | — | |
| `GET /reports/*` | varies | — | Report-specific |
| `GET /brands` | ✅ *(9C)* | display_order | Full list when `page` omitted |
| `GET /locations` | ✅ *(9C)* | name | Full list when `page` omitted |
| `GET /product-models` | ✅ *(9C)* | model_name | Full list when `page` omitted |

### Unified Search (New in 9C)

`GET /api/v1/search?q={term}&types[]=inventory&limit=10`

- Types: `inventory`, `brand`, `location`, `product_model`
- Default limit: 10, max 25 per type
- Replaces desktop `GlobalSearchService` multi-fetch pattern

### Desktop Anti-Patterns (Not Backend Gaps)

| Location | Behavior | Mobile Alternative |
|----------|----------|-------------------|
| `useInventoryHierarchyData.ts` | Fetches ALL inventory pages | Use paginated `GET /inventory` + lazy tree expansion |
| `productModelSummary.ts` | `fetchAllInventoryForModel` loops pages | Add `GET /inventory?product_model_id=` filter (exists) with pagination |
| `GlobalSearchService.ts` | Client-side merge of 4 API calls | `GET /search` |

---

## 6. Version Negotiation

### `GET /api/v1/version` (Public)

Returns: `backend_version`, `schema_version`, `api_version`, `build_version`, `min_desktop_version`, `min_mobile_version`

### `GET /api/v1/capabilities` (Public)

Returns: `modules`, `tally_enabled`, `backup_enabled`, `reports_enabled`, `feature_flags`, AI provider status

### Client Boot Sequence (Recommended)

```
1. GET /health/live          → server reachable
2. GET /version              → compare min_mobile_version
3. GET /capabilities         → hide disabled modules in UI
4. GET /setup/status         → redirect if uninitialized
5. POST /auth/login          → store tokens
6. GET /sync/state           → baseline cursors
```

`PlatformService.ts` added for steps 2–3; not yet integrated into desktop boot.

---

## 7. API Consistency: Desktop vs Flutter vs Web

| Concern | Desktop Today | Flutter / Web Target |
|---------|---------------|----------------------|
| Response envelope | `{ data, meta, request_id, ... }` | Same — use shared `@webstudio/api-client` patterns |
| Errors | `{ error: { code, message, details } }` | Same |
| Pagination meta | `has_next`, `total`, `total_items` | Same |
| Auth header | `Authorization: Bearer` | Same |
| Client identification | `X-Client-Platform: macos_desktop` (hardcoded) | `ios`, `android`, `web` — parameterize |
| Client version | `X-Client-Version: 0.1.0` | Match app store / web deploy version |
| File downloads | Raw `fetch` + blob | Same pattern; add refresh wrapper |
| JSON mutations | `RetryingApiClient` | Port refresh interceptor to Dart/TS web |
| Static assets | Served by Electron/Vite dev server | Serve from API host or CDN path |

All three clients should share the **same API contract** documented in Milestone 9A. No client-specific backend forks required.

---

## 8. Desktop API-Only Verification

| Check | Result |
|-------|--------|
| Direct database access from desktop | ❌ None found |
| Business logic only in backend services | ✅ |
| All CRUD via REST | ✅ (20 API service modules) |
| Local-only data affecting server state | ⚠️ `ProductImageService` localStorage cache (UI only; server has upload API) |
| Hidden retry/enrichment logic in desktop | ⚠️ Removed in prior milestone; backend owns AI retries |
| Export bypasses API client | ⚠️ `ReportService`, `AuthenticationService` raw `fetch` |

**Verdict:** Desktop is API-only for all server-mutating workflows. Remaining local logic is UI preference (theme, column widths, recent searches) — acceptable for desktop, not required for mobile.

---

## 9. Flutter Readiness Checklist

| Item | Status | Notes |
|------|--------|-------|
| Auth (login/refresh/logout) | ✅ Ready | Standard JWT flow |
| RBAC enforcement server-side | ✅ Ready | No client trust |
| Paginated list APIs | ✅ Ready | All major entities |
| Catalogue pagination | ✅ Ready | 9C — optional `page` param |
| Global search API | ✅ Ready | 9C — `GET /search` |
| Sync state baseline | ✅ Ready | 9C — preparation only |
| Delta sync APIs | ⏳ Deferred | Use high-water marks when added |
| Image upload | ✅ Ready | 9C — multipart upload |
| Image proxy/download | ✅ Ready | Proxy + static assets |
| Version negotiation | ✅ Ready | Public `/version` |
| Capability discovery | ✅ Ready | Public `/capabilities` |
| File export (reports) | ✅ Ready | Binary stream endpoints |
| Offline mutation queue | ⏳ Deferred | No idempotency keys yet |
| Push notifications | ⏳ Deferred | Poll-based notifications exist |
| WebSocket / SSE | ❌ Not implemented | Polling sufficient for v1 |

---

## 10. Test Results

```
tests/test_mobile_readiness.py
  test_sync_state_requires_auth       PASSED
  test_search_requires_auth           PASSED
  test_version_and_capabilities_public PASSED
```

Full suite (`pytest`) requires PostgreSQL with `alembic upgrade head`. Run:

```bash
cd apps/backend
../../.venv/bin/python -m pytest tests/test_mobile_readiness.py -v
../../.venv/bin/python -m pytest -q
```

---

## 11. Files Changed in 9C

| File | Purpose |
|------|---------|
| `services/sync_state_service.py` | High-water mark aggregation |
| `api/routers/sync.py` | Sync state endpoint |
| `services/global_search_service.py` | Unified search logic |
| `api/routers/search.py` | Search endpoint |
| `api/routers/brands.py` | Optional pagination |
| `api/routers/locations.py` | Optional pagination |
| `api/routers/product_models.py` | Optional pagination |
| `api/routers/product_images.py` | Multipart upload |
| `app.py` | Register sync + search routers |
| `tests/test_mobile_readiness.py` | Auth + public endpoint tests |
| `apps/desktop/.../PlatformService.ts` | Version/capabilities client |
| `apps/desktop/.../index.ts` | Export PlatformService |

---

**Next step:** Review this report. Flutter implementation should begin only after approval. Priority desktop cleanups (optional): wire `PlatformService` on boot, migrate search to `/api/v1/search`, route exports through `RetryingApiClient`.
