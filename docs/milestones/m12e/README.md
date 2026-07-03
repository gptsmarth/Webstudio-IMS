---
Title: Milestone 12E — Enterprise Tally Deployment
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
---

# Milestone 12E — Enterprise Tally Deployment

Final production Tally deployment using the **approved** incremental sync architecture (migration `0034`, `incremental-sync-engine.md`).

## Deliverables

| Area | Location |
|------|----------|
| GUID + incremental sync engine | `services/tally_sync_service.py`, migration `0034` |
| Hidden metadata (no GUID/MasterID/AlterID in UI/API) | Sales API, Tally dashboard, desktop/mobile Tally panels |
| Persistent scheduler + auto-resume | M12B `scheduler_runtime_state` + M12E interval sync |
| User-facing metrics only | `TallyDashboardService.operational` |
| Developer XML documentation | [xml-developer-guide.md](../../integrations/tally-erp9/xml-developer-guide.md) |
| Operator guides | This folder |

## Operator guides

1. [Tally Deployment Guide](TALLY_DEPLOYMENT_GUIDE.md) — install and configure production Tally sync
2. [Validation Guide](VALIDATION_GUIDE.md) — verify sync health before go-live
3. [Recovery Guide](RECOVERY_GUIDE.md) — resume after outages

## User-visible fields (only)

Operators see these Tally metrics in Settings → Tally (desktop/mobile):

- Last Sync
- Last Invoice
- Last Invoice Date
- Next Sync
- Imported Today
- Imported This Week
- Imported This Month
- Sync Health

Raw XML and internal identifiers are **never** shown in the application.

## Related milestones

- **12B** — Business-hours server, scheduler persistence, graceful shutdown
- **12D** — Multi-SSID networking and Tally connectivity probe
