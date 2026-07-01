# Milestone 9B — Backend Performance Engineering Report

**Date:** 2026-06-30  
**Scope:** `apps/backend/` + `database/migrations/`  
**Status:** Audit complete — **stop for review**

---

## Executive Summary

Milestone 9B audited all major backend services for query efficiency, memory use, blocking I/O, and observability. **Business logic was not changed** — optimizations target data access patterns, indexes, parallelism, and event-loop blocking.

### Optimizations Applied

| Priority | Change | Impact |
|----------|--------|--------|
| P0 | Tally `_match_inventory_by_model` — single JOIN query instead of N×`get_detail` | Eliminates worst N+1 in codebase |
| P0 | `TallySyncLogRepository.aggregate_stats` — SQL `SUM`/`COUNT` | O(1) vs loading all sync logs |
| P1 | Migration `0027_performance_indexes` — 6 new indexes | Reports, audit JSONB, notification inbox |
| P1 | Dashboard distribution — `asyncio.gather` (3 parallel queries) | ~3× faster distribution endpoint |
| P1 | User list — batch creator name lookup (`get_display_names_by_ids`) | N queries → 1 |
| P1 | Report export — `asyncio.to_thread` for XLSX/PDF CPU work | Unblocks event loop |
| P1 | Backup `pg_dump` — `asyncio.to_thread` | Unblocks event loop during dump |
| P2 | Slow request logging — `http_request_slow` at ≥750ms + `response_bytes` | Observability |

---

## 1. Service-by-Service Audit

### Inventory

| Finding | Severity | Status |
|---------|----------|--------|
| List/search uses 4-table JOIN (no ORM lazy N+1) | — | ✅ Good |
| Sprint 2C indexes (`0012`) on serial, status, location, model | — | ✅ Good |
| Correlated `EXISTS` subquery on `sales` for free-text search | Medium | Documented |
| `ILIKE '%term%'` on brand/model/location (no trigram) | Medium | Deferred 9C |
| Post-mutation `get_detail()` re-query | Low | Acceptable for single-item API |
| `transfer_all_movable_from_location` loop (latent N+1) | Medium | Not called from API; deferred |

**9B:** Added `ix_inventory_items_created_at` for report streaming sort.

### Sales

| Finding | Severity | Status |
|---------|----------|--------|
| Unique index on `inventory_item_id` | — | ✅ Good |
| `ix_sales_sold_at`, `ix_sales_invoice_number` | — | ✅ Good |
| Missing index on `recorded_by_user_id` for report filter | Medium | ✅ Fixed (0027) |

### Reports

| Finding | Severity | Status |
|---------|----------|--------|
| Batched streaming (`STREAM_BATCH_SIZE=500`) | — | ✅ Good |
| Export collects all batches in RAM before write | High | Partial — CPU moved to thread |
| OFFSET-based stream pagination | Medium | Deferred (keyset pagination) |
| XLSX/PDF build blocks event loop | Medium | ✅ Fixed (`to_thread`) |

### Dashboard

| Finding | Severity | Status |
|---------|----------|--------|
| SQL `COUNT`/`GROUP BY` aggregates | — | ✅ Good |
| 3 sequential distribution queries | Medium | ✅ Fixed (`asyncio.gather`) |
| `get_recent_business_activity` loads full ORM rows | Low | Deferred |

### Audit

| Finding | Severity | Status |
|---------|----------|--------|
| `search_enriched` — single 4-way OUTER JOIN | — | ✅ Good |
| JSONB filters on `new_value` without GIN | High | ✅ Fixed (GIN index) |
| Count over joined subquery (2 queries/page) | Medium | Acceptable |
| `ILIKE '%term%'` on description/actor | Medium | Deferred (trigram) |

**9B:** Added `ix_audit_logs_new_value_gin`, `ix_audit_logs_created_entity`.

### Notifications

| Finding | Severity | Status |
|---------|----------|--------|
| Standard `paginate()` on list | — | ✅ Good |
| No composite index for inbox pattern | Medium | ✅ Fixed (`is_resolved, is_read, created_at`) |
| No index on `inventory_item_id` FK | Low | ✅ Fixed |

### Backup & Restore

| Finding | Severity | Status |
|---------|----------|--------|
| `subprocess.run(pg_dump)` blocks event loop | High | ✅ Partial (`to_thread` on dump) |
| Tar/compress still sync on main thread | Medium | Deferred |
| Restore runs sync SQL in async handler | High | Deferred (background worker) |
| Retention deletes sequential | Low | Deferred |

**Recommendation (9C):** Move backup/restore to dedicated background worker queue.

### Tally

| Finding | Severity | Status |
|---------|----------|--------|
| `_match_inventory_by_model` N+1 (full scan + per-item detail) | **Critical** | ✅ Fixed |
| `aggregate_stats` loads all logs into Python | High | ✅ Fixed |
| Per-voucher/per-line DB round-trips during sync | High | Documented; batch in 9C |
| Extra `get_detail` when serial known (L520) | Medium | Deferred |
| Notification per line failure (write churn) | Medium | Deferred |

### Users

| Finding | Severity | Status |
|---------|----------|--------|
| Session counts batched via `count_active_by_user_ids` | — | ✅ Good |
| Creator names N+1 in user list | Medium | ✅ Fixed |
| `extras_for_user` still 2 queries for detail view | Low | Acceptable |

### Catalogue (Brands, Locations, Product Models)

| Finding | Severity | Status |
|---------|----------|--------|
| All list endpoints load full table (no pagination) | Medium | Deferred 9C |
| Product model routes fetch brand separately | Low | Deferred |
| `archive_all_active_for_brand` N+1 audits | Medium | Deferred |

---

## 2. Database Indexes (Migration 0027)

```sql
-- inventory_items(created_at DESC)     — report export sort
-- sales(recorded_by_user_id)           — sales report user filter
-- notifications(is_resolved, is_read, created_at DESC)  — inbox
-- notifications(inventory_item_id)     — FK lookups
-- audit_logs GIN(new_value jsonb_path_ops)  — security JSONB filters
-- audit_logs(created_at, entity_type)  — default audit list
```

**Apply:** `alembic upgrade head` (revision `0027_performance_indexes`)

---

## 3. Background Processing Assessment

| Operation | Current | Recommended |
|-----------|---------|-------------|
| Large report exports | Sync in request handler (CPU in thread) | Background job + download URL |
| Backup create | Async handler, sync subprocess (partial thread) | Dedicated worker + status polling |
| Restore | Blocks request until complete | Worker + progress endpoint |
| Tally XML parse | Sync in scheduler task | Acceptable; `to_thread` for huge XML |
| AI enrichment | Sync in request (15–120s) | Already cached; consider async job for wizard |
| Image download | Sync in enrichment finalize | `to_thread` or background queue |

**No new worker infrastructure added in 9B** — documented for 9C.

---

## 4. Observability

### Before 9B

- HTTP `duration_ms` on every request (`http_request` INFO)
- Backup/restore/Tally/AI log their own `duration_ms`

### After 9B

| Signal | Log event | Fields |
|--------|-----------|--------|
| Normal request | `http_request` | `duration_ms`, `method`, `path`, `status_code` |
| Slow request (≥750ms) | `http_request_slow` | Same + `response_bytes` when available |
| Threshold | `SLOW_REQUEST_THRESHOLD_MS` env / `slow_request_threshold_ms` setting | Default 750ms |

### Still Missing (9C)

- Per-endpoint DB query count
- SQLAlchemy slow-query logging
- Memory profiling on large exports

---

## 5. Benchmark Scenarios (Projected)

*Estimates based on query plan analysis — formal load tests require PostgreSQL + locust/k6 harness (9C).*

| Scenario | Before (est.) | After 9B (est.) | Notes |
|----------|---------------|-----------------|-------|
| **10,000 inventory** list page 1 | ~50–80ms | ~40–60ms | Existing indexes; created_at helps reports |
| **100,000 audit logs** enriched page 1 | ~200–400ms | ~120–250ms | GIN + composite index on created_at/entity |
| **50 concurrent users** dashboard | ~150ms×3 sequential | ~50–80ms | Parallel distribution queries |
| **Tally sync** 500 lines, model match fallback | **Minutes** (N+1) | **Seconds** | Single JOIN replaces N×detail |
| **Tally dashboard stats** 10k log rows | ~500ms+ RAM | ~5–15ms | SQL aggregation |
| **Large XLSX export** 50k rows | Blocks API 30s+ | API responsive | CPU in thread pool |
| **Backup pg_dump** | Blocks API 10–60s | API responsive | Dump in thread pool |

---

## 6. Files Changed (9B)

```
database/migrations/versions/0027_performance_indexes.py   NEW

apps/backend/src/webstudio_backend/
  api/middleware/request_logging.py          slow request warnings
  core/config.py                             slow_request_threshold_ms
  services/dashboard_service.py              asyncio.gather
  services/tally_sync_service.py             _match_inventory_by_model fix
  services/user_admin_service.py             batch creator lookup
  services/report_export_service.py          asyncio.to_thread
  services/backup_engine.py                    asyncio.to_thread (pg_dump)
  infrastructure/repositories/
    tally_sync_log_repository.py             SQL aggregate_stats
    user_repository.py                         get_display_names_by_ids

apps/backend/tests/test_performance.py       NEW

docs/api/MILESTONE_9B_PERFORMANCE_REPORT.md  NEW (this file)
```

---

## 7. Test Results

| Check | Result |
|-------|--------|
| App import | ✅ Pass |
| Ruff (changed files) | ✅ Pass |
| `test_performance.py` | Requires PostgreSQL (migration 0027) |
| Full pytest suite | Run locally: `pytest apps/backend/tests` |

---

## 8. Review Checklist

- [ ] Apply migration `0027_performance_indexes` on dev/staging
- [ ] Verify Tally sync with model-match fallback on realistic voucher set
- [ ] Monitor `http_request_slow` logs after deploy
- [ ] Approve 9C scope: background workers, catalogue pagination, keyset report streaming, trigram search
- [ ] Run formal load benchmark with 10k inventory / 100k audit / 50 users

---

## 9. Deferred to 9C (Not in Scope)

1. Background job queue for backup/restore/large exports
2. Keyset pagination for report streaming (replace OFFSET)
3. Stream-to-disk exports without `_collect_batches` RAM spike
4. Catalogue list pagination
5. `pg_trgm` indexes for `%search%` filters
6. Tally sync batch persistence (reduce per-line commits)
7. Denormalize audit display fields to reduce join fan-out

---

*Generated as part of Milestone 9B — Backend Performance Engineering.*
