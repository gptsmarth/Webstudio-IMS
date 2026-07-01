# Milestone 9E — Production Readiness Report

**Date:** 2026-07-01  
**Scope:** `apps/backend/src/webstudio_backend/` (full engineering review)  
**Status:** Audit complete — **stop for review**

---

## Executive Summary

The WEBSTUDIO IMS backend is **functionally mature** — 262 of 283 tests pass, the desktop build succeeds, and TypeScript typecheck is clean. The architecture is sound: FastAPI + async SQLAlchemy, repository pattern, RBAC, JSON envelope API, provider-based AI, and enterprise backup/restore.

**Production deployment is not yet recommended** without addressing **5 critical** and **9 high-priority** findings below. The most urgent gaps are: weak JWT defaults, silent exception handling, fake migration health checks, long-running Tally transactions, and missing distributed job locks for multi-worker deployments.

### Readiness Scorecard

| Area | Grade | Notes |
|------|-------|-------|
| Configuration | ⚠️ C+ | Env-based; weak production validation |
| Logging | ⚠️ B− | Structured JSON available; global 500s not logged |
| Error Handling | ⚠️ B | Envelope contract solid; unhandled exceptions invisible |
| Security Headers | ✅ B+ | Core headers present; HSTS missing |
| Database Migrations | ✅ A− | 27 migrations, linear chain; runtime check missing |
| Health Checks | ⚠️ C | Liveness OK; readiness fakes migration status |
| Scheduler / Background Jobs | ⚠️ C | In-process only; silent Tally failures |
| Backup / Restore | ⚠️ B− | Feature-complete; key leakage, blocking restore |
| AI Providers | ✅ B+ | Provider framework solid; mock-in-prod risk |
| Tally Integration | ⚠️ B− | Functional; txn scope + alert flood |
| Notifications | ✅ B | Centralized service; no retention policy |
| Test Suite | ⚠️ B | 93% pass rate; migration tests stale |
| Lint / Typecheck | ⚠️ C+ | ESLint/TS clean; Ruff 434 issues; Mypy 109 |
| Build | ✅ A | Desktop production build succeeds |

---

## 1. Architecture Review

### 1.1 System Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                     Clients (Desktop / Future Mobile)            │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS / JSON REST
┌────────────────────────────▼────────────────────────────────────┐
│  FastAPI Application (app.py)                                      │
│  ├── Middleware: CORS → Security Headers → Request Log → Corr ID  │
│  ├── 22 Router Modules (~140 routes)                              │
│  ├── Exception Handlers (AppError, HTTP, Validation, Unhandled)   │
│  └── Lifespan: init_db, Tally scheduler, Backup scheduler         │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐  ┌─────────────────┐  ┌──────────────────┐
│  PostgreSQL   │  │  External APIs  │  │  Local Filesystem │
│  (webstudio   │  │  Groq, Gemini,  │  │  Backups, assets, │
│   schema)     │  │  Tally XML/HTTP │  │  exports          │
└───────────────┘  └─────────────────┘  └──────────────────┘
```

### 1.2 Layered Design

| Layer | Location | Assessment |
|-------|----------|------------|
| **API** | `api/routers/`, `api/schemas/` | Consistent envelope; some routers still use local `_envelope` helpers |
| **Services** | `services/` | Business logic centralized; clear domain boundaries |
| **Repositories** | `infrastructure/repositories/` | Pagination, filtering, audit recording |
| **Database** | `infrastructure/database/` | Async SQLAlchemy; pool size 10 |
| **Integrations** | `integrations/tally/` | XML client isolated from sync orchestration |
| **AI** | `services/ai/` | Provider interface + factory + fallback chain |

### 1.3 Strengths

- **API-only contract** — JSON envelope, standardized errors, RBAC on all protected routes
- **Audit trail** — Field-level changes recorded for inventory, models, settings
- **Disaster recovery** — Backup manifests, verification, restore engine, recovery service
- **AI modernization** — Groq default, Gemini fallback, mock for tests (Milestone 9D)
- **Performance work** — N+1 fixes, SQL aggregates, 6 new indexes (Milestone 9B)
- **Multi-client prep** — Sync state, unified search, catalogue pagination (Milestone 9C)

### 1.4 Architectural Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Single-process schedulers | Duplicate jobs with multiple workers | Distributed locks or external cron |
| Long DB transactions (Tally) | Pool exhaustion, lock contention | Per-voucher commits |
| In-memory AI health | Misleading status after restart | Persist or document as ephemeral |
| `get_settings()` `@lru_cache` | Frozen config until restart | Document; clear in tests |
| No rate limiting middleware | Brute-force on auth endpoints | Implement before public exposure |

---

## 2. Area-by-Area Review

### 2.1 Configuration

**File:** `core/config.py`

| Setting | Default | Production Concern |
|---------|---------|-------------------|
| `jwt_secret` | `"change-me-in-production"` | **CRITICAL** — no validation in production |
| `log_level` | `"DEBUG"` | High log volume in production |
| `database_url` | Embedded dev credentials | Accidental deploy risk |
| `rate_limit_enabled` | `false` | Advertised but not enforced |
| `cors_origins` | `["http://localhost:5173"]` | Must override for production |
| `tls_*` paths | Empty | `tls_ca_path` defined but unused |

**Positive:** Pydantic Settings with env file support; test env isolation in `conftest.py`.

---

### 2.2 Logging

**Files:** `core/logging.py`, `api/middleware/request_logging.py`, `services/ai/logging.py`

| Feature | Status |
|---------|--------|
| JSON structured output | ✅ Auto-enabled in production |
| Request/correlation IDs | ✅ All responses |
| Slow request logging | ✅ ≥750ms threshold (9B) |
| AI enrichment events | ✅ Structured `layer=ai` bindings (9D) |
| Unhandled 500 logging | ❌ **CRITICAL** — no `logger.exception()` |
| Scheduler failure logging | ❌ Tally loop swallows exceptions silently |

---

### 2.3 Error Handling

**File:** `core/exceptions.py`

| Handler | Status |
|---------|--------|
| `AppError` | ✅ Maps to envelope + HTTP status |
| `HTTPException` | ✅ Code mapping (404→NOT_FOUND, etc.) |
| `RequestValidationError` | ✅ Field-level details |
| `Exception` (catch-all) | ⚠️ Returns generic 500, **logs nothing** |

Error codes align with desktop retry logic: `RATE_LIMITED`, `QUOTA_EXCEEDED`, `TIMEOUT`, `API_ERROR`, `NOT_CONFIGURED`, `SERVICE_UNAVAILABLE`.

---

### 2.4 Security Headers

**File:** `api/middleware/security_headers.py`

| Header | Present |
|--------|---------|
| `X-Content-Type-Options: nosniff` | ✅ |
| `X-Frame-Options: DENY` | ✅ |
| `Referrer-Policy: no-referrer` | ✅ |
| `Content-Security-Policy` | ✅ (API-appropriate) |
| `X-XSS-Protection: 0` | ✅ (modern best practice) |
| `Strict-Transport-Security` | ❌ Missing when TLS enabled |
| `Cache-Control: no-store` | ❌ Missing for authenticated routes |
| `Permissions-Policy` | ❌ Missing |

---

### 2.5 Database Migrations

**Path:** `database/migrations/versions/` — **27 migrations** (0001 → 0027)

| Check | Result |
|-------|--------|
| Linear revision chain | ✅ Intact |
| Schema bootstrap | ✅ `webstudio` schema in `env.py` |
| Performance indexes | ✅ Migration 0027 (notifications, audit, inventory) |
| Runtime version check | ❌ `/health/ready` hardcodes `migrations: ok` |
| Migration tests | ⚠️ Stale — allowlists stop at revision 0014 |

---

### 2.6 Health Checks

**File:** `api/routers/health.py`

| Endpoint | Purpose | Assessment |
|----------|---------|------------|
| `GET /health/live` | Liveness | ✅ Returns version + headers |
| `GET /health/ready` | Readiness | ⚠️ DB ping real; migrations **faked**; disk checks `/` not backup mount |
| `GET /health/version` | Info | ⚠️ Exposes `environment` publicly |

```python
# health.py:65-68 — migrations never verified
checks: dict[str, str] = {
    "database": "unknown",
    "migrations": "ok",  # ← always "ok"
    "disk_space": "unknown",
}
```

---

### 2.7 Scheduler & Background Jobs

**Files:** `app.py`, `services/backup_scheduler.py`, `api/routers/tally.py`

| Job | Trigger | Concurrency | Error Handling |
|-----|---------|-------------|----------------|
| Tally sync scheduler | `WEBSTUDIO_TALLY_SCHEDULER=1` | Process-local `asyncio.Lock` | ❌ Silent `except Exception` |
| Backup scheduler | `WEBSTUDIO_BACKUP_SCHEDULER=1` (default) | None | ✅ Creates backup alert notification |
| Manual Tally sync | `POST /tally/sync` | Background task | Single `session_scope` for entire sync |
| Report export | On-demand | Thread pool (9B) | ✅ |

**Multi-worker risk:** Each Uvicorn worker starts independent scheduler loops. No distributed lock.

---

### 2.8 Backup & Restore

**Files:** `services/backup_engine.py`, `services/restore_engine.py`, `services/recovery_service.py`

| Feature | Status |
|---------|--------|
| Full backup (pg_dump data-only) | ✅ Thread-offloaded (9B) |
| Settings snapshot in archive | ⚠️ Only `gemini_api_key` redacted; `groq_api_key`, `openrouter_api_key` in plaintext |
| Backup encryption | ⚠️ `NoOpBackupEncryption` — archives unencrypted |
| Manifest + verification | ✅ |
| Restore entire database | ⚠️ Blocks event loop (sync subprocess) |
| Session held during pg_dump | ⚠️ Connection idle-in-transaction |

---

### 2.9 AI Providers

**Path:** `services/ai/` (Milestone 9D)

| Feature | Status |
|---------|--------|
| Provider interface (`AIProvider`) | ✅ |
| Groq default / Gemini fallback | ✅ |
| Automatic fallback chain | ✅ |
| Caching (`ai_enrichment_cache`) | ✅ (race condition on concurrent writes) |
| Health tracking | ✅ In-memory per process |
| Mock provider in production | ⚠️ Not blocked when `app_env != test` |
| Structured logging | ✅ `services/ai/logging.py` |

---

### 2.10 Tally Integration

**Files:** `services/tally_sync_service.py`, `integrations/tally/xml_client.py`

| Feature | Status |
|---------|--------|
| XML voucher import | ✅ |
| Inventory matching | ⚠️ Full-table scan for model matching (9B partially fixed JOIN) |
| Sync logging + stats | ✅ SQL aggregates (9B) |
| Connection test | ✅ |
| Alert on failure | ✅ But `tally_alerts_enabled` setting **not checked** |
| HTTP to Tally | ⚠️ Unencrypted (`http://host:port`) — localhost only |
| Transaction scope | ❌ Entire sync in one DB transaction |

---

### 2.11 Notification Services

**File:** `services/notification_service.py`

| Feature | Status |
|---------|--------|
| Centralized creation | ✅ Used by Tally, backup, security alerts |
| Paginated inbox | ✅ Indexed (migration 0027) |
| Mark read / resolved | ✅ |
| Retention / purge | ❌ Table grows unbounded |
| Settings gating | ⚠️ `tally_alerts_enabled` ignored; `audit_alerts_enabled` default mismatch |

---

## 3. Code Quality Findings

### 3.1 Bugs Found During Audit

| Severity | Issue | File | Detail |
|----------|-------|------|--------|
| **HIGH** | Missing `AppError` import | `api/routers/brands.py` | `NameError` on duplicate brand name (F821) |
| **HIGH** | Invalid `sort` kwarg | `services/global_search_service.py:44` | `InventoryItemRepository.search()` has no `sort` param |
| **MEDIUM** | TestClient closes DB factory | `tests/test_health.py` | `close_db()` in TestClient teardown breaks later session tests (13 errors) |
| **LOW** | Migration tests stale | `tests/*/test_migration.py` | Allowlists stop at revision 0014; head is 0027 |

### 3.2 Unused / Dead Code

| Item | File |
|------|------|
| `_background_tasks: set[asyncio.Task]` never used | `api/routers/tally.py` |
| `_copy_company_logo()` duplicate of sync variant | `services/backup_engine.py` |
| `tls_ca_path` defined, never read | `core/config.py` |
| `gemini_config.py` thin re-export shim | `services/gemini_config.py` |
| `GeminiLookupError` was unused in router | `api/routers/product_models.py` (removed 9D) |

### 3.3 Duplicate Logic

- Company logo copy: sync + async variants in `backup_engine.py`
- Schema version lookup: `platform_info_service.py`, `backup_engine.py`, `recovery_service.py`, `health.py` (missing)
- AI config: `services/ai/config.py` vs `gemini_config.py` shim

### 3.4 Concurrency & Race Conditions

| Issue | Location | Risk |
|-------|----------|------|
| Process-local Tally sync lock | `tally_sync_service.py` | Duplicate sync across workers |
| No backup overlap protection | `backup_scheduler.py` + manual backup | Concurrent `pg_dump` |
| AI cache read-modify-write | `services/ai/cache.py` | Last-write-wins on concurrent enrichment |
| `AIProviderHealthTracker` global dict | `services/ai/health.py` | Thread-safe (Lock) but not cross-process |

### 3.5 Memory / Resource Concerns

| Issue | Location | Risk |
|-------|----------|------|
| Unbounded notifications table | `notification_repository.py` | Storage growth |
| AI enrichment cache (500 entries) | `services/ai/cache.py` | Bounded ✅ |
| DB pool size 10, no overflow | `infrastructure/database/session.py` | Exhaustion under load |
| Long Tally transaction | `tally_sync_service.py` | Connection held for minutes |

---

## 4. CI / Pipeline Results

### 4.1 Full Test Suite

```
262 passed, 8 failed, 13 errors, 2 skipped (283 total)
Duration: ~2m 25s
```

| Category | Count | Root Cause |
|----------|-------|------------|
| **Passed** | 262 | Core business logic, auth, inventory, sales, settings, AI |
| **Failed** | 8 | 6 migration tests (stale revision allowlist); 2 reference API tests |
| **Errors** | 13 | TestClient `close_db()` conflicts with session-scoped `database_engine` fixture |
| **Skipped** | 2 | Conditional skips |

### 4.2 Typecheck

| Target | Result |
|--------|--------|
| TypeScript monorepo (`pnpm typecheck`) | ✅ **PASS** — all 7 packages |
| Python mypy (`webstudio_backend`) | ❌ **109 errors** in 25 files (non-strict mode) |

Notable mypy issues: `brands.py` missing `AppError`, `global_search_service.py` type errors, `enrichment_service.py` variable shadowing.

### 4.3 Lint

| Target | Result |
|--------|--------|
| ESLint (`pnpm lint`) | ✅ **PASS** — all packages |
| Ruff (`apps/backend/src`) | ❌ **434 errors** — 304 line-length (E501), 59 unused imports (F401), 7 undefined names (F821) |

### 4.4 Build

| Target | Result |
|--------|--------|
| Desktop (`pnpm desktop:build`) | ✅ **PASS** |
| Warnings | Chunk size >500 kB; font paths unresolved at build time (cosmetic) |

---

## 5. Recommendations (Priority Order)

### P0 — Block Production Deploy

| # | Action | Effort |
|---|--------|--------|
| 1 | Enforce `JWT_SECRET` ≥32 bytes in production; reject default value | S |
| 2 | Add `logger.exception()` to unhandled exception handler | S |
| 3 | Implement real migration version check in `/health/ready` | M |
| 4 | Fix `brands.py` missing `AppError` import | S |
| 5 | Fix `global_search_service.py` invalid `sort` parameter | S |

### P1 — High Priority (Pre-Launch)

| # | Action | Effort |
|---|--------|--------|
| 6 | Refactor Tally sync to commit per voucher/batch | L |
| 7 | Add distributed job locking (PostgreSQL advisory locks) | M |
| 8 | Redact all `*_api_key` settings in backup snapshots | S |
| 9 | Implement rate limiting on `/api/v1/auth/*` | M |
| 10 | Log exceptions in Tally scheduler loop | S |
| 11 | Gate Tally notifications on `tally_alerts_enabled` | S |
| 12 | Run restore subprocesses via `asyncio.to_thread()` | M |
| 13 | Set `LOG_LEVEL=INFO` default for production | S |
| 14 | Block `mock` AI provider when `app_env != test` | S |

### P2 — Medium Priority (Post-Launch)

| # | Action | Effort |
|---|--------|--------|
| 15 | Add HSTS header when TLS is configured | S |
| 16 | Check disk space on backup directory, not `/` | S |
| 17 | Add notification retention policy (90-day purge) | M |
| 18 | Tune DB pool: `max_overflow`, `pool_recycle` | S |
| 19 | Fix TestClient / `close_db()` test isolation | M |
| 20 | Update migration test revision allowlists to 0027 | S |
| 21 | Separate `ENCRYPTION_KEY` from `JWT_SECRET` | M |
| 22 | Add backup overlap protection (advisory lock) | S |

### P3 — Low Priority (Technical Debt)

| # | Action | Effort |
|---|--------|--------|
| 23 | Remove dead code (`_background_tasks`, duplicate logo copy) | S |
| 24 | Centralize schema version resolution | S |
| 25 | Migrate `BaseHTTPMiddleware` to pure ASGI middleware | M |
| 26 | Fix 304 Ruff E501 line-length violations | M |
| 27 | Enable stricter mypy gradually | L |
| 28 | Code-split desktop bundle (687 kB JS) | M |

---

## 6. Pre-Production Checklist

```
Configuration
  [ ] JWT_SECRET set to cryptographically random ≥32 bytes
  [ ] DATABASE_URL points to production PostgreSQL
  [ ] LOG_LEVEL=INFO, LOG_JSON=true
  [ ] CORS_ORIGINS restricted to known client origins
  [ ] APP_ENV=production

Security
  [ ] Rate limiting enabled on auth endpoints
  [ ] TLS termination configured (reverse proxy or uvicorn SSL)
  [ ] API keys stored in DB settings, not env files on disk
  [ ] Backup archives encrypted or stored in restricted location

Infrastructure
  [ ] Single worker OR distributed job locks configured
  [ ] WEBSTUDIO_BACKUP_SCHEDULER=1 only on designated worker
  [ ] WEBSTUDIO_TALLY_SCHEDULER=1 only on designated worker
  [ ] /health/ready wired to load balancer (after migration check fix)
  [ ] Backup directory on monitored volume with ≥5% free space

Database
  [ ] alembic upgrade head applied
  [ ] Connection pool sized for expected concurrency
  [ ] pg_dump tested against production schema

Monitoring
  [ ] Log aggregation configured (JSON → ELK/Datadog/CloudWatch)
  [ ] Alert on /health/ready failures
  [ ] Alert on backup scheduler failures
  [ ] Alert on Tally sync consecutive failures

Testing
  [ ] Full pytest suite green (fix 8 failures + 13 errors)
  [ ] Smoke test: login → inventory CRUD → sale → report export
  [ ] Disaster recovery drill: backup → restore → verify
```

---

## 7. Files Referenced

| Area | Primary Files |
|------|---------------|
| Config | `core/config.py` |
| Logging | `core/logging.py`, `api/middleware/request_logging.py` |
| Errors | `core/exceptions.py`, `api/schemas/errors.py` |
| Security | `api/middleware/security_headers.py` |
| Health | `api/routers/health.py` |
| Scheduler | `app.py`, `services/backup_scheduler.py` |
| Backup | `services/backup_engine.py`, `services/restore_engine.py` |
| AI | `services/ai/` |
| Tally | `services/tally_sync_service.py`, `integrations/tally/` |
| Notifications | `services/notification_service.py` |
| Tests | `apps/backend/tests/conftest.py` |

---

**Next step:** Review this report. Address P0 items before any production deployment. P1 items should be completed before exposing the API to the public internet.
