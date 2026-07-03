---
Title: Recovery Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Recovery Guide

Disaster recovery and outage procedures for showroom operations.

---

## 1. Recovery readiness

**Recovery Center** (Settings → Backup) shows:

| Metric | Meaning |
|--------|---------|
| System health | Overall status |
| Recovery readiness | Ready / Partial / Not ready |
| Database status | PostgreSQL reachable |
| Backup status | Recent successful backup |
| Storage free | Disk space |

Run **Recovery wizard** quarterly.

---

## 2. Outage types

| Event | First response |
|-------|----------------|
| Server PC off | Power on; wait for auto-start services |
| PostgreSQL down | `ensure-postgresql.ps1`; start service |
| API not responding | Check logs; restart WEBSTUDIO Server |
| Network down | Fix router; clients auto-reconnect |
| Tally offline | Sync retries; see [Tally Guide](TALLY_GUIDE.md) |
| Data corruption | Restore from backup |

---

## 3. Business hours recovery (M12B)

### Morning

1. Power on server PC
2. PostgreSQL starts automatically
3. WEBSTUDIO Server (Delayed Start) — ~2 min
4. Clients reconnect automatically

Script: `infra/windows/start-business-day.ps1`

### Evening

1. `stop-business-day.ps1` — graceful API shutdown
2. Optional PostgreSQL stop
3. Power off server PC

---

## 4. Server restart mid-day

1. `Stop-Service "WEBSTUDIO Server"` or UPS shutdown
2. Startup orchestration clears stale Tally locks
3. Schedulers resume from `scheduler_runtime_state`
4. No manual Tally re-sync required

---

## 5. Full disaster recovery

**Scenario:** Server PC replaced or disk failure.

1. Install Windows + PostgreSQL on new hardware
2. Run **WEBSTUDIO Server Setup.exe** or restore files to `D:\WEBSTUDIO-IMS`
3. `alembic upgrade head` to current migration
4. Restore latest off-site backup ([Restore Guide](RESTORE_GUIDE.md))
5. Update DHCP reservation / DNS to new server if IP changed
6. Re-run Office Deployment Wizard
7. Validate with Network wizard + Tally validation

---

## 6. Recovery wizard steps

1. **Assessment** — Recovery Center dashboard
2. **Validation** — automated checks
3. **Recovery** — backup or restore actions
4. **Restart** — service restart acknowledgment
5. **Verification** — confirm health green

---

## 7. Escalation

Provide to support:

| Item | Example |
|------|---------|
| Backup filename | `backup-2026-07-01.tar.gz` |
| Server log excerpt | Last 50 lines of `webstudio-api.log` |
| Manifest | From backup or `version-manifest.json` |
| Symptom timeline | When sync/backup failed |

**Do not email** JWT secrets or recovery key.

---

## 8. Related milestone guides

- [M12B Recovery Guide](../m12b/RECOVERY_GUIDE.md) — Windows service
- [M12E Tally Recovery](../m12e/RECOVERY_GUIDE.md) — Tally outages
- [M12D Troubleshooting](../m12d/TROUBLESHOOTING_GUIDE.md) — network
