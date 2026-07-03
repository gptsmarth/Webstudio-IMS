---
Title: Tally Validation Guide — Enterprise Go-Live
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12E
---

# Tally Validation Guide — Enterprise Go-Live

Use this checklist before enabling automatic Tally sync in production.

---

## 1. Infrastructure validation

| # | Check | Pass criteria |
|---|-------|---------------|
| 1.1 | WEBSTUDIO Server service running | `sc query WEBSTUDIO-Server` → RUNNING |
| 1.2 | PostgreSQL running | Server startup check `postgresql: ok` |
| 1.3 | `WEBSTUDIO_TALLY_SCHEDULER=1` | Tally scheduler active (not “manual sync only”) |
| 1.4 | Disk space | ≥ 5% free on data volume |
| 1.5 | Server clock | Correct timezone (sync timestamps accurate) |

---

## 2. Network validation

| # | Check | Pass criteria |
|---|-------|---------------|
| 2.1 | Server → Tally port 9000 | Settings → Test Connection → **Connected** |
| 2.2 | Hostname resolution | Health endpoint shows resolved IP |
| 2.3 | Multi-SSID (if applicable) | M12D Network Admin Wizard → all stages green |
| 2.4 | Firewall | Server outbound and Tally inbound allowed |

API (admin): `GET /api/v1/integrations/tally/health`

---

## 3. Tally configuration validation

| # | Check | Pass criteria |
|---|-------|---------------|
| 3.1 | Company name | Matches Tally **exactly** (including spaces) |
| 3.2 | Voucher types | Sales and NEW SALE used in showroom |
| 3.3 | Serial numbers | Present on inventory lines (SERIALNUMBER or BASICUSERDESCRIPTION) |
| 3.4 | Printed invoice | REFERENCE field populated on vouchers |
| 3.5 | Tally open during hours | Company loaded when sync expected |

---

## 4. Sync engine validation

Run manual sync once before relying on scheduler:

1. Settings → Tally → **Sync now** (or `POST /api/v1/integrations/tally/sync/trigger`)
2. Wait for completion (typically under 2 minutes for same-day window)

| # | Check | Pass criteria |
|---|-------|---------------|
| 4.1 | Sync completes | Last Sync timestamp updates |
| 4.2 | Sales created | Imported Today > 0 (if Tally had today’s sales) |
| 4.3 | Serial match | Inventory items move to SOLD in WEBSTUDIO |
| 4.4 | Duplicate safety | Second manual sync → invoices **skipped**, not duplicated |
| 4.5 | Sync history | Run shows checked/imported/skipped counts |
| 4.6 | No internal IDs in UI | No GUID, MasterID, or AlterID visible anywhere |

---

## 5. User-facing metrics validation

Confirm **Settings → Tally** shows only business fields:

| Field | Expected |
|-------|----------|
| Last Sync | ISO timestamp after successful run |
| Last Invoice | Printed invoice number (e.g. `WEB/25-26/00042`) |
| Last Invoice Date | Voucher date |
| Next Sync | Future timestamp aligned with interval |
| Imported Today / Week / Month | Non-negative integers |
| Sync Health | `healthy` when connected and no errors |

Desktop dashboard widget and mobile Tally screen should match the same values.

---

## 6. Scheduler validation

| # | Check | Pass criteria |
|---|-------|---------------|
| 6.1 | Interval persisted | Change interval in settings → Next Sync adjusts |
| 6.2 | Server restart | After restart, sync resumes without manual trigger |
| 6.3 | Single instance | Overlapping triggers do not run two imports (lock) |
| 6.4 | Offline retry | Stop Tally → health offline → restart Tally → sync recovers |

---

## 7. Notification validation (optional)

| # | Check | Pass criteria |
|---|-------|---------------|
| 7.1 | `tally_alerts_enabled` on | New imports create Tally notification |
| 7.2 | `tally_alerts_enabled` off | No Tally sync notifications |
| 7.3 | Repeated failures | After 3 consecutive failures → error notification |

---

## 8. Metadata privacy validation

Automated tests: `tests/tally/test_tally_enterprise_metadata.py`

Manual spot-check:

- Sales detail drawer — **no GUID row**
- Tally sync history CSV — no GUID/MasterID columns
- API JSON — no `tally_voucher_guid`, `tally_master_id`, `alter_id`

---

## 9. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| System admin | | | |
| Showroom manager | | | |
| Engineering | | | |

**Go-live approved** when all sections 1–8 pass.

---

## Reference commands (admin)

```powershell
# Server service status
sc query WEBSTUDIO-Server

# Tail server logs (path per install)
Get-Content D:\WEBSTUDIO\logs\server.log -Tail 50 -Wait
```

```bash
# API health (replace token)
curl -s -H "Authorization: Bearer $TOKEN" \
  http://server:8000/api/v1/integrations/tally/health
```
