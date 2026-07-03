---
Title: Performance Certification
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14G
Related Documents:
  - docs/milestones/m14/PRODUCTION_CERTIFICATION_REPORT.md
  - docs/api/MILESTONE_9B_PERFORMANCE_REPORT.md
  - docs/SYSTEM_ARCHITECTURE.md
---

# Performance Certification (M14G)

## Scope

Production performance certification validates WEBSTUDIO IMS readiness for:

| Target | Value |
|--------|-------|
| Inventory items | **10,000** |
| Sales records | **50,000** |
| Concurrent sessions | **100** |

**Verdict:** Architecture and indexes are **certified**; row-count and load-test evidence is collected on the production or staging server before final sign-off.

---

## Certification matrix

| Target | Check key | Validation method |
|--------|-----------|-------------------|
| Inventory scale | `inventory_10000` | Row count vs 10,000 + index verification |
| Sales scale | `sales_50000` | Row count vs 50,000 + index verification |
| Concurrent sessions | `concurrent_sessions_100` | `refresh_tokens` table + `database_pool_size` |
| Query indexes | `indexes_inventory_items`, `indexes_sales` | PostgreSQL `pg_indexes` (migrations 0012, 0027) |
| Observability | `slow_request_observability` | Requests ≥ 750 ms logged |

---

## Index coverage (required)

### Inventory (`webstudio.inventory_items`)

| Index | Purpose |
|-------|---------|
| `ix_inventory_items_created_at` | Report streaming, recent lists |
| `ix_inventory_items_status` | Status filters |

### Sales (`webstudio.sales`)

| Index | Purpose |
|-------|---------|
| `ix_sales_sold_at` | Date-range reports |
| `ix_sales_recorded_by_user_id` | Per-user sales filters |

Additional Sprint 2C indexes (serial, location, model) remain in place from migration `0012_inventory_performance`.

---

## Architecture benchmarks (M9B)

From [MILESTONE_9B_PERFORMANCE_REPORT.md](../../api/MILESTONE_9B_PERFORMANCE_REPORT.md):

| Scenario | Expected latency (indexed, warm cache) |
|----------|----------------------------------------|
| 10,000 inventory — list page 1 | ~40–80 ms |
| 50 concurrent dashboard loads | ~50–80 ms (parallel distribution queries) |
| Tally aggregate stats | O(1) SQL `SUM`/`COUNT` |

PostgreSQL on a dedicated Windows 11 Pro server handles V1 scale without replication or Redis.

---

## 100 concurrent sessions

| Component | Guidance |
|-----------|----------|
| `DATABASE_POOL_SIZE` | Recommend **≥ 20** for 100 active sessions |
| PostgreSQL `max_connections` | Tune above pool size + admin overhead |
| Uvicorn workers | Single worker sufficient at V1 LAN scale; add workers if CPU-bound |
| Refresh tokens | One row per active device session |

The certification API reports `warning` when `database_pool_size < 20`.

---

## Staging load test procedure

Run on a server seeded with production-like data:

1. **Seed data:** Import or migrate until `inventory_items` ≥ 10,000 and `sales` ≥ 50,000.
2. **Inventory list:** `GET /api/v1/inventory?page=1&page_size=50` — median < 200 ms on LAN.
3. **Sales list:** `GET /api/v1/sales?page=1&page_size=50` — median < 200 ms on LAN.
4. **Concurrent logins:** Use a load tool (e.g. `hey`, `k6`) with 100 parallel `POST /api/v1/auth/login` from distinct test users — error rate < 1%.
5. **Record evidence:** Save API certification JSON, pg_stat counts, and load-tool summary.

---

## Operator validation

```http
GET /api/v1/deployment/production-certification
Authorization: Bearer <network-admin-token>
```

Inspect `performance_certification`:

- `targets` — scale goals
- `checks` — per-target status (`passed` when row counts meet targets on commissioned server)
- `warning` on empty dev DB is **expected** until production data is loaded

---

## Automated tests

| Test file | Coverage |
|-----------|----------|
| `tests/test_performance.py` | Index existence (migration 0027) |
| `tests/deployment/test_production_certification_validation.py` | M14G certification checks |

Run: `pytest apps/backend/tests/deployment/test_production_certification_validation.py apps/backend/tests/test_performance.py`
