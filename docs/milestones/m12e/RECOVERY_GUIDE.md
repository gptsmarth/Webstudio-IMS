---
Title: Tally Recovery Guide — Enterprise Outages
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12E
Related Documents:
  - docs/milestones/m12b/RECOVERY_GUIDE.md
  - docs/milestones/m12e/TALLY_DEPLOYMENT_GUIDE.md
---

# Tally Recovery Guide — Enterprise Outages

WEBSTUDIO automatically resumes Tally synchronization after common disruptions. Use this guide when automatic recovery does not restore **Sync Health: Healthy** within one sync interval.

---

## Automatic resume (no action required)

| Event | Engine behaviour |
|-------|------------------|
| **Weekend / holiday** | Next business day: fetch from `last_successful_sync_at` date; GUID dedup skips prior imports |
| **Power loss (server)** | On boot: startup orchestration restores scheduler; clears stale `sync_in_progress` |
| **Power loss (Tally PC)** | Probe marks offline; sync retries each interval until Tally responds |
| **WiFi loss** | Connectivity probe detects outage; no watermark change; retry when network returns |
| **Server restart** | Scheduler resumes from `scheduler_runtime_state.next_run_at` |
| **Tally restart** | Next successful connection test → sync continues incremental window |
| **Graceful evening shutdown** | Shutdown orchestrator checkpoints open sync runs; morning resume normal |

**Operator view:** Sync Health may show **Offline** during outage; **Next Sync** countdown continues.

---

## Recovery procedures

### A — Tally workstation offline

**Symptoms:** Sync Health **Offline**, “Waiting for Tally workstation”, connectivity probe failed.

1. Confirm Tally PC is powered on and company is open.
2. Verify Tally XML port 9000 (F12 → Advanced Configuration).
3. Settings → Tally → **Test Connection**.
4. If failed: check LAN cable/WiFi, firewall, and hostname (M12D network guide).
5. When connected, wait for **Next Sync** or tap **Sync now**.

**Expected:** Last Sync updates; Imported counts catch up for the date window (duplicates skipped).

---

### B — Server restarted mid-sync

**Symptoms:** Brief “Synchronization in progress” stuck state, or skipped run in history with “Server shutdown — sync checkpointed”.

1. Confirm WEBSTUDIO Server service is running.
2. No manual DB intervention required — startup clears `sync_in_progress`.
3. Trigger **Sync now** or wait for next scheduled run.

**Expected:** Partially processed invoices resume at **line level** (completed lines skipped).

---

### C — Wrong company name or host

**Symptoms:** Sync fails every run; error in sync history; zero imports.

1. Settings → Tally — verify **Company name** matches Tally exactly.
2. Update **Host** to current IP or stable hostname.
3. Test Connection → save → Sync now.

---

### D — Duplicate concern after long outage

**Symptoms:** Operator worried about double imports after multi-day gap.

**Reassurance:** GUID is the primary dedup key. Re-fetching a date window does **not** create duplicate sales if GUIDs were already imported.

**Validation:** Run sync twice; second run should show high **skipped** count, zero new imports.

---

### E — Serial not matching / missing imports

**Symptoms:** Invoice in Tally but not in WEBSTUDIO; sync history shows errors or missing serial notifications.

1. Open sync history → note error summary for the run.
2. Confirm serial on Tally voucher (SERIALNUMBER or BASICUSERDESCRIPTION).
3. Confirm serial exists in WEBSTUDIO inventory as **AVAILABLE**.
4. Re-run sync — failed lines retry; successful lines skip.

---

### F — Scheduler not running

**Symptoms:** “Manual sync only (scheduler not active on server)”.

1. Set `WEBSTUDIO_TALLY_SCHEDULER=1` in server service environment.
2. Restart WEBSTUDIO Server service.
3. Confirm scheduler status changes to idle/syncing on next interval.

---

### G — Repeated sync failures (3+ runs)

**Symptoms:** Error notification “Tally synchronization failing repeatedly”; Sync Health **Needs attention**.

1. Check server logs for XML or connection errors.
2. Run Test Connection and Network Admin validation (M12D).
3. Verify PostgreSQL and disk space.
4. If Tally data issue (malformed XML): fix voucher in Tally or contact engineering with log excerpt — **do not** expose GUID to operators; use printed invoice number instead.

---

## Escalation data for engineering

When contacting support, provide:

| Item | Example |
|------|---------|
| Printed invoice number | `WEB/25-26/00042` |
| Last Sync timestamp | From Settings → Tally |
| Sync history status | Success / Partial / Failed |
| Server log excerpt | Around sync run time |
| Test Connection result | Connected / error message |

**Do not** send GUID, MasterID, or raw XML in operator tickets unless explicitly requested by engineering (developer guide only).

---

## Windows scripts

| Script | Use |
|--------|-----|
| `infra/windows/start-business-day.ps1` | Morning start after unplanned overnight off |
| `infra/windows/recover-server.ps1` | Full server recovery (M12B) |
| `infra/windows/configure-firewall.ps1` | Restore port 8000/5432 rules |

---

## Related recovery

| Scope | Document |
|-------|----------|
| Full server / PostgreSQL | [M12B Recovery Guide](../m12b/RECOVERY_GUIDE.md) |
| Network / SSID | [M12D Troubleshooting](../m12d/TROUBLESHOOTING_GUIDE.md) |
