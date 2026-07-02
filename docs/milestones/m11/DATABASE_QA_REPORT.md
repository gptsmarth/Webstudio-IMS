---
Title: Milestone 11 — Database QA Report
Version: 1.0.0
Status: Complete
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related Documents: docs/milestones/m11/BACKUP_RECOVERY_VALIDATION_REPORT.md
---

# Database QA Report

PostgreSQL schema validation (`database/migrations/`, `webstudio` schema).

## Migration inventory

| Metric | Value |
|--------|-------|
| Migration files | 30 |
| Current head | `0030_brand_hard_delete` |
| Test DB setup | Alembic upgrade head via `conftest.py` |

### Recent migrations (0015–0030)

Includes: sales snapshots, Tally integration, auth security, performance indexes (9B), custom access roles (0029), brand hard-delete with sale snapshot backfill (0030).

## Indexes validated

### Milestone 9B (`0027_performance_indexes.py`)

Tested in `tests/test_performance.py`:

| Table | Index |
|-------|-------|
| `inventory_items` | `ix_inventory_items_created_at` |
| `sales` | `ix_sales_recorded_by_user_id` |
| `notifications` | `ix_notifications_inbox`, `ix_notifications_inventory_item_id` |
| `audit_logs` | `ix_audit_logs_new_value_gin`, `ix_audit_logs_created_entity` |

### Sprint 2C (`0012_inventory_performance.py`)

Tested in `tests/inventory_item/test_inventory_hardening.py`:

- `ix_inventory_items_serial_number_lower`
- `ix_inventory_items_list_default`
- `ix_inventory_items_location_status`
- `ix_inventory_items_model_status`

## Constraints & foreign keys

| Migration | Constraint |
|-----------|------------|
| 0020 | `password_history.user_id`, `login_events.user_id` FKs |
| 0029 | `users.custom_access_role_id` → custom roles (cascade) |
| 0030 | Brand hard-delete preserves sale snapshots before FK nulling |
| Various | Inventory → product_model, location; sales → inventory |

`backup_completeness.verify_foreign_key_integrity()` validates `pg_constraint.convalidated`.

## Transactions & rollback

- Service layer uses async SQLAlchemy sessions with explicit `commit()` / rollback on error
- Inventory operations tested for status transition integrity
- Restore engine uses transactional apply with validation preview

## Migration test status

| Issue | Severity | Root cause | Fixed | Deferred |
|-------|----------|------------|-------|----------|
| BACK-004 | Medium | 6 tests whitelist revision `0014` max | No | Yes |
| DB-001 | Low | No structural tests for 0027–0030 | No | Yes |

**No schema corruption or broken migrations identified.**

## Performance at scale (not load-tested in M11)

| Target | M11 action | Recommendation |
|--------|------------|----------------|
| 10,000 inventory | Index tests only | Seed staging + list/search benchmark |
| 50,000 sales | Index on `recorded_by_user_id` | Report query benchmark |
| 100,000 audit logs | GIN index on `new_value` | Audit search benchmark |

See [PERFORMANCE_QA_REPORT.md](./PERFORMANCE_QA_REPORT.md).

## Verdict

Database schema is **production-ready**. Migration test maintenance and staging load tests are recommended before high-volume deployment.
