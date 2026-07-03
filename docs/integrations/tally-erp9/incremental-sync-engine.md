---
Title: Tally Incremental Sync Engine
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related Documents: docs/integrations/tally-erp9/sync-strategy.md, docs/milestones/m12e/README.md
---

# Tally Incremental Sync Engine

Enterprise incremental synchronization implemented in migration `0034_tally_incremental_sync`. Production deployment procedures: [M12E Tally Deployment Guide](../milestones/m12e/TALLY_DEPLOYMENT_GUIDE.md).

## Behaviour

| Concern | Implementation |
|---------|----------------|
| Fetch window | From `last_successful_sync_at.date()` (first sync: today only) |
| Primary dedup | `tally_voucher_guid` on `tally_processed_invoice` |
| Fallback dedup | voucher date + voucher number + amount + normalized party name |
| Polling interval | Default 300s, clamped 60–3600s (`tally_sync_interval_seconds`) |
| Overlap guard | Process `asyncio.Lock` + `tally_company_sync.sync_in_progress` |
| Restart recovery | `clear_all_sync_in_progress()` on scheduler startup |
| Run history | `tally_sync_history` — checked / imported / skipped / errors / duration |
| Notifications | New imports only; repeated failures after 3 consecutive error runs |
| Offline | No watermark change, no notifications; retry next poll |

## Internal state (never exposed in API)

- `last_successful_sync_at`
- `last_processed_guid` (last imported GUID cursor)
- `last_processed_master_id` (stored for traceability; never shown in UI)
- `last_imported_voucher_date`

Dashboard, settings, sync history, and sales detail APIs omit GUID, MasterID, and AlterID. Developer XML reference: [xml-developer-guide.md](xml-developer-guide.md).

## Client surfaces

- **Desktop** — Settings → Tally: operational metrics grid, sync history modal (filter/search/export), connection settings form
- **Mobile** — More/Settings → Tally: same business metrics; dedicated sync history screen with CSV export
- **Dashboard widgets** — Connected, last sync, pending retry, today's imports, sync health

## Key modules

- `integrations/tally/incremental_sync.py` — interval clamping, date window, fingerprint helpers
- `services/tally_sync_service.py` — orchestration
- `infrastructure/repositories/tally_sync_history_repository.py` — run-level history
