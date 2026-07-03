---
Title: Tally Production Guide
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14C
Related Documents:
  - docs/milestones/m14/TALLY_VALIDATION_CHECKLIST.md
  - docs/milestones/m14/XML_VERIFICATION_GUIDE.md
  - docs/milestones/m12h/TALLY_GUIDE.md
  - docs/integrations/tally-erp9/TALLY_SYNC_ENGINE_ARCHITECTURE.md
---

# Tally Production Guide (M14C)

Operator and engineer guide for **production Tally ERP 9 integration** after WEBSTUDIO IMS deployment.

**Assumption:** Live Tally is available on the billing PC during commissioning and business hours.

---

## 1. Architecture summary

| Component | Role |
|-----------|------|
| **Tally billing PC** | Runs Tally ERP 9 with XML interface (TCP **9000**) |
| **WEBSTUDIO Server** | Polls Tally, parses XML, imports sales, updates inventory |
| **Desktop / mobile** | Read sync status from dashboard — no direct Tally access |

**Direction:** Tally → WEBSTUDIO only (read-only integration).

---

## 2. Production configuration

### Server environment (`.env` on dedicated server PC)

| Variable | Production value |
|----------|------------------|
| `WEBSTUDIO_TALLY_SCHEDULER` | `1` |
| `WEBSTUDIO_TALLY_CONNECTIVITY_PROBE` | `1` |

### Settings → Tally (Main Admin)

| Field | Guidance |
|-------|----------|
| **Enable** | On |
| **Host** | Billing laptop **hostname** (e.g. `LENOVO-TALLY`) — not static IP |
| **Port** | `9000` |
| **Company** | Exact Tally company name |
| **Sync interval** | `300` seconds (5 min); range 60–3600 |

Run **Test Connection** before sign-off.

---

## 3. Synchronization behaviour

### Incremental sync

- First successful sync requests vouchers from **today** (or last imported date).
- Subsequent syncs request from `last_successful_sync_at` date — **not** full history.
- Voucher types: **Sales**, **NEW SALE** (see `MONITORED_VOUCHER_TYPES`).

### GUID checkpoint

After each successful voucher import, WEBSTUDIO updates:

- `tally_company_sync.last_processed_guid`
- `tally_company_sync.last_imported_voucher_date`
- `tally_company_sync.last_successful_sync_at`

### Duplicate prevention

- Each Tally voucher GUID is stored in `tally_processed_invoice`.
- Re-sync skips GUIDs already marked **SUCCESS**.

### Offline handling

When Tally is off or unreachable:

1. Sync run recorded as **offline** / skipped in `tally_sync_history`.
2. No data loss — checkpoint dates preserved.
3. When Tally returns, next sync replays the incremental window.

---

## 4. Recovery scenarios

### After WEBSTUDIO Server restart

1. Windows Service starts WEBSTUDIO Server.
2. `tally_sync` scheduler restores from `scheduler_runtime_state`.
3. In-progress syncs checkpointed on graceful shutdown (`checkpoint_tally_sync`).
4. Next scheduled sync runs automatically if `WEBSTUDIO_TALLY_SCHEDULER=1`.

**Validation:** Restart server service; confirm dashboard **Next Sync** updates and a sync run appears in history within one interval.

### After Tally restart

1. `tally_connectivity_probe` scheduler detects workstation return.
2. Connection status moves from offline → connected.
3. Next `tally_sync` cycle imports pending vouchers.

**Validation:** Close and reopen Tally; wait for probe interval or trigger **Sync now**.

---

## 5. Manual vs automatic sync

| Mode | Trigger |
|------|---------|
| **Automatic** | `tally_sync` background scheduler (configurable interval) |
| **Manual** | Settings → Tally → **Sync now** or `POST /api/v1/integrations/tally/sync/trigger` |

Both use the same `TallySyncService.run_sync` pipeline.

---

## 6. Dashboard synchronization status

Staff and admins see (no internal GUID/XML):

| Field | Source |
|-------|--------|
| **Sync Health** | healthy / degraded / offline |
| **Last Sync** | `last_successful_sync_at` |
| **Last Invoice** | Last imported printed invoice number |
| **Next Sync** | Scheduler runtime + interval |
| **Imported Today / Week / Month** | `tally_sync_history` aggregates |

API: `GET /api/v1/integrations/tally/dashboard` and `/status`.

---

## 7. Production validation

### API (authenticated — `tally:view_status`)

```http
GET /api/v1/integrations/tally/production-validation
```

Returns 12 commissioning checks plus live connectivity probe when Tally is enabled.

### Windows server script

```powershell
cd C:\WEBSTUDIO\ims\infra\windows
.\validate-production-tally.ps1 -ApiBaseUrl "http://127.0.0.1:8000" -BearerToken "<admin-jwt>" -TallyHost "LENOVO-TALLY"
```

### Desktop

1. **Settings → Tally** — Test Connection, Sync now
2. **Tally workspace** — Sync Health, history panel
3. **Dashboard** — Tally panel (if enabled)

---

## 8. Sign-off prerequisites

Complete [TALLY_VALIDATION_CHECKLIST.md](TALLY_VALIDATION_CHECKLIST.md) with evidence.

Minimum for go-live:

- [ ] Test Connection **passed**
- [ ] At least one successful automatic sync
- [ ] Dashboard shows **healthy** sync health during business hours
- [ ] Duplicate re-sync test passed (see checklist TLY-11)
- [ ] Server restart recovery test passed (TLY-08)

---

## 9. Related files

| File | Purpose |
|------|---------|
| `services/tally_sync_service.py` | Sync engine |
| `services/tally_production_validation_service.py` | M14C validation |
| `integrations/tally/xml_client.py` | XML request generation |
| `integrations/tally/incremental_sync.py` | Date window + interval clamp |
| `services/shutdown_orchestrator.py` | Server restart checkpoint |
| `services/tally_connectivity_scheduler.py` | Tally restart probe |
