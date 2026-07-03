---
Title: Tally Deployment Guide — Enterprise Production
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12E
Related Documents:
  - docs/milestones/m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md
  - docs/milestones/m12d/NETWORK_DEPLOYMENT_REPORT.md
  - docs/integrations/tally-erp9/incremental-sync-engine.md
---

# Tally Deployment Guide — Enterprise Production

Deploy WEBSTUDIO IMS Tally synchronization for a retail showroom using Tally ERP 9 on a dedicated billing PC.

---

## Architecture overview

```
[Tally ERP 9 PC]  ←LAN→  [WEBSTUDIO Server]  ←LAN/WiFi→  [Desktop / Mobile clients]
     port 9000              PostgreSQL + API              Settings → Tally (metrics only)
```

- **Tally workstation** runs during business hours with company books open.
- **WEBSTUDIO Server** polls Tally on a configurable interval (default 5 minutes).
- **Clients** display operational sync metrics only — no XML, GUID, or MasterID.

---

## Prerequisites

| Component | Requirement |
|-----------|-------------|
| Tally ERP 9 | Release 6.x+ with ODBC/XML enabled |
| Tally company | Exact company name as shown in Tally (case-sensitive) |
| Network | Server can reach Tally host:port (see M12D network guide) |
| WEBSTUDIO Server | Windows service installed (M12C server installer) |
| Scheduler | `WEBSTUDIO_TALLY_SCHEDULER=1` on server |
| Connectivity probe | `WEBSTUDIO_TALLY_CONNECTIVITY_PROBE=1` (recommended) |

---

## Step 1 — Enable Tally XML on billing PC

1. Open Tally → **F12** → **Advanced Configuration**.
2. Set **Tally acting as** → **Both** (or **Server**).
3. Enable **Tally.NET** / port **9000** (default).
4. Ensure the correct **company** is loaded when Tally is open.
5. Confirm firewall allows inbound TCP **9000** from the WEBSTUDIO server IP (`infra/windows/configure-firewall.ps1` on server; allow outbound on Tally PC if needed).

---

## Step 2 — Configure WEBSTUDIO Server

### Environment variables (server service)

| Variable | Value | Purpose |
|----------|-------|---------|
| `WEBSTUDIO_TALLY_SCHEDULER` | `1` | Enable automatic sync loop |
| `WEBSTUDIO_TALLY_CONNECTIVITY_PROBE` | `1` | Background Tally reachability checks |
| `WEBSTUDIO_DATA_ROOT` | e.g. `D:\WEBSTUDIO` | Data and logs path |

Restart the WEBSTUDIO Server service after changing environment variables.

### Settings (admin UI)

Open **Settings → Integrations → Tally**:

| Setting | Guidance |
|---------|----------|
| **Enable Tally sync** | On |
| **Host** | Tally PC hostname or IP (prefer hostname for DHCP resilience — M12D) |
| **Port** | `9000` |
| **Company name** | Must match Tally exactly |
| **Sync interval** | 300 seconds (5 min) typical; range 60–3600 |

Use **Test Connection** before saving. A green result confirms XML export works.

---

## Step 3 — Verify scheduler persistence

The server stores scheduler timing in `webstudio.scheduler_runtime_state`:

- **Configurable interval** — updated when Tally settings change
- **Persistent `next_run_at`** — survives server restart
- **Single running instance** — global sync lock prevents overlapping imports
- **Automatic retry** — next poll after offline periods (weekends, WiFi loss, power cycles)

After server install, confirm startup logs show scheduler state restored (M12B startup orchestration).

---

## Step 4 — First sync behaviour

| Condition | Behaviour |
|-----------|-----------|
| No prior successful sync | Imports **today’s** vouchers only |
| After first success | Incremental window from last successful sync **date** |
| Known GUID | Skipped (idempotent) |
| Changed voucher (same fingerprint) | Skipped if prior import succeeded |

Operators see **Imported Today** increment as sales appear in WEBSTUDIO.

---

## Step 5 — Business-hours operation

For daily power-on/power-off (M12B):

| Event | Tally sync behaviour |
|-------|---------------------|
| Morning server start | Clears stale sync locks; resumes from persisted `next_run_at` |
| Evening graceful stop | Checkpoints in-progress sync; saves scheduler state |
| Weekend / holiday | On Monday, fetches from last sync date; DB dedup skips already-imported |
| Tally PC off | Probe marks offline; sync retries when Tally returns |

Optional scripts: `infra/windows/start-business-day.ps1`, `stop-business-day.ps1`.

---

## Step 6 — Operator training

Show staff **Settings → Tally** only:

- **Sync Health** — Healthy / Needs attention / Offline
- **Last Sync** / **Next Sync**
- **Last Invoice** — printed invoice number (not GUID)
- **Imported Today / Week / Month**

Do **not** train operators on XML, GUID, or MasterID — these are internal only.

---

## Developer reference

Backend engineers: [XML Developer Guide](../../integrations/tally-erp9/xml-developer-guide.md)

---

## Troubleshooting entry points

| Symptom | Guide |
|---------|-------|
| Pre go-live checks | [Validation Guide](VALIDATION_GUIDE.md) |
| After outage | [Recovery Guide](RECOVERY_GUIDE.md) |
| Network / SSID issues | [M12D Troubleshooting](../m12d/TROUBLESHOOTING_GUIDE.md) |
| Windows service | [M12B Windows Service Guide](../m12b/WINDOWS_SERVICE_GUIDE.md) |
