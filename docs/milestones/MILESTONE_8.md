# Milestone 8 — Audit Center & System Activity

## Summary

Milestone 8 delivers a Main Administrator **Audit Center** workspace: searchable audit table, filters, detail drawer with before/after values, chronological timeline view, and filtered Excel/PDF exports.

## Delivered

### 1. Backend extensions
- Enriched audit list via `search_enriched` (serial, location, model, invoice joins)
- `AuditLogListEntry` — module, operation, result, contextual columns
- `AuditLogDetail` — request/correlation IDs (when stored in payloads), related inventory/sale/Tally flags
- Extended filters: `search`, `actor_role`, `location_id`, `invoice_number`, `model_number`, `result`
- `AuditReadDep` — all audit endpoints require `audit:read` permission

### 2. Desktop Audit Center
- `AuditPage` replaces placeholder
- `useAuditWorkspace` — paginated list, filters, drawer detail, exports
- Components under `components/audit/`:
  - `AuditTable` — full column set per spec
  - `AuditTimeline` — vertical lifecycle-style timeline
  - `AuditDetailDrawer` — who/when, before/after JSON, traceability, related records
  - `AuditToolbar` — search, table/timeline toggle, export actions
  - `AuditFiltersPanel` — user, role, operation, module, date range, location, result

### 3. Export
- Filtered Excel/PDF via existing `ReportService.exportReport('audit', …)`
- Export buttons enabled only when search or filters are active

### 4. Access
- Gated by `audit:read` from session permissions (Main Admin)

### 5. Tests
- `apps/desktop/tests/audit.test.ts`
- Backend audit API tests updated for auth + enriched payload

## Verification

```bash
cd apps/desktop && npm run typecheck && npm run lint && npm run test && npm run build
cd apps/backend && pytest tests/audit_log/test_api.py -q
```

## Stop for review

Milestone 8 is implementation-complete pending your review of the Audit Center (Main Admin login required).
