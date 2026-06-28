# Milestone 10 — Production Tally ERP 9 Integration

## Summary

Milestone 10 delivers production-ready **one-way** Tally ERP 9 synchronization: XML voucher processing, printed invoice number support, voucher-type store mapping, serial-first matching with product model fallback, dashboard widgets, notifications, audit integration, and background polling.

## Delivered

### 1. Backend Tally engine
- `integrations/tally/` — XML client, parser, voucher types, store mapping constants
- `TallySyncService` — voucher/line processing, duplicate detection (GUID → MASTERID → voucher number), sale reflection
- `TallyDashboardService` — connection status, stats, recent synchronizations
- Database migration `0016_tally_integration` — `tally_company_sync`, `tally_processed_invoice`, `tally_processed_invoice_line`, `tally_sync_log`, sales traceability columns
- Automatic polling every 30 minutes (configurable) when `WEBSTUDIO_TALLY_SCHEDULER=1` is set at backend startup
- Manual sync / retry / connection test API (non-blocking background tasks)

### 2. Voucher type → store mapping
| Voucher Type | Store |
|--------------|-------|
| Sales | WEBSTUDIO |
| NEW SALE | AES |

### 3. Matching rules (frozen)
1. **Serial number** — authoritative; always marks sold when matched in available inventory
2. **Product model** — fallback when serial missing; informational mismatch notifications never block sales
3. **Duplicate detection** — GUID, then MASTERID, then internal voucher number (not printed invoice)

### 4. API endpoints
| Method | Path |
|--------|------|
| GET | `/api/v1/integrations/tally/dashboard` |
| GET | `/api/v1/integrations/tally/status` |
| GET | `/api/v1/integrations/tally/sync-log` |
| POST | `/api/v1/integrations/tally/connection/test` |
| POST | `/api/v1/integrations/tally/sync/trigger` |
| POST | `/api/v1/integrations/tally/sync/retry` |

RBAC: `tally:dashboard` (includes Salesperson read-only), `tally:sync` (Admin/Main Admin).

### 5. Desktop updates
- Enhanced `TallyService`, `TallyReadinessPanel` with voucher types and sync metrics
- `lib/tally.ts` — store mapping helpers
- Sales drawer shows printed invoice vs internal voucher number
- Dashboard continues Tally status widget with live backend data

### 6. Notifications & audit
- Types: sync started/completed, connection lost/restored, duplicate sale, missing serial, missing model, model mismatch, sync failure
- Audit entries with `TALLY_SYNC` source for sync lifecycle, voucher processing, inventory sold

### 7. Tests
- `apps/backend/tests/tally/test_tally_api.py`
- `apps/desktop/tests/tally.test.ts`

## Verification

```bash
cd database && alembic upgrade head
cd apps/desktop && npm run typecheck && npm run lint && npm run test && npm run build
cd apps/backend && pytest tests/tally/test_tally_api.py -q
```

## Stop for review

Milestone 10 is implementation-complete pending your review with Tally ERP 9 running on the LAN (enable integration in System Settings, configure host/port/company name, ensure WEBSTUDIO and AES locations exist).
