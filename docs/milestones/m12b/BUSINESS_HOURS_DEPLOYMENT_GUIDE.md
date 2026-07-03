---
Title: Business Hours Deployment Guide
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12B
---

# Business Hours Deployment Guide

WEBSTUDIO IMS runs on a **dedicated Windows 11 Pro server PC** that is **powered ON during business hours only** and **powered OFF every evening**.

This guide defines daily operations, boot/shutdown behaviour, and scheduler continuity.

---

## Operating model

| Phase | Server PC | PostgreSQL | WEBSTUDIO Server | Clients |
|-------|-----------|------------|------------------|---------|
| **Morning** | Power ON | Auto-start | Delayed auto-start | Auto-reconnect |
| **Business hours** | Running | Running | Running | Connected |
| **Evening** | Graceful stop → Power OFF | Optional stop | Graceful stop | Offline OK |
| **Overnight** | Off | Off | Off | Cached/offline mobile |

**UPS recommended** for graceful shutdown if power fails before scheduled stop.

---

## Morning startup (automatic)

When the server PC powers on:

```
Windows Boot
    → PostgreSQL Windows Service (Automatic)
    → WEBSTUDIO Server Service (Automatic Delayed Start)
        → Verify PostgreSQL connection
        → Startup health checks (storage, config, AI, Tally)
        → Restore scheduler_runtime_state from database
        → Resume schedulers from persisted next_run_at
        → mDNS advertisement (if enabled)
        → Accept API requests
```

Optional manual script (if services not set to automatic):

```powershell
.\infra\windows\start-business-day.ps1
```

---

## Evening shutdown (graceful)

Recommended sequence before powering off the PC:

```powershell
.\infra\windows\stop-business-day.ps1 -GracefulWaitSeconds 45
# Optional: -StopPostgreSQL if PG should not run overnight
```

Shutdown orchestration inside the API:

1. Signal schedulers to stop scheduling new work  
2. Wait for active Tally sync (up to 30 s default)  
3. Checkpoint interrupted Tally history rows  
4. Persist all scheduler `next_run_at` timestamps  
5. Flush logs  
6. Close database pool  

Then stop the Windows service or shut down the PC.

---

## Scheduler continuity

**Requirement:** Never restart scheduling from zero after overnight power-off.

Implementation:

| Scheduler | Default interval | Persistence |
|-----------|------------------|-------------|
| Tally sync | 300 s (configurable) | `scheduler_runtime_state.tally_sync` |
| Backup | 900 s poll | Uses `last_backup_at` + schedule |
| Audit retention | 24 h | `scheduler_runtime_state.audit_retention` |
| Notification delivery | 300 s | `scheduler_runtime_state.notification_delivery` |
| Maintenance | 3600 s | `scheduler_runtime_state.maintenance` |

Background task persists state every **60 s** (`WEBSTUDIO_SCHEDULER_PERSIST_SECONDS`).

**Example:** Tally sync runs at 17:55, interval 5 min → `next_run_at = 18:00`. Server powers off at 18:05. Next morning boot at 09:00 → first sync runs immediately (deadline passed), not after a fresh 5-minute idle wait.

---

## Client behaviour during power cycles

### Desktop (Electron)

- Saved server URL in local config  
- Workspace polls health every **15 seconds**  
- On recovery: session refresh via existing token flow  
- On failure: connection badge shows offline; automatic retry  

### Flutter (Mobile)

- Saved API URL in SharedPreferences  
- `ServerReconnectLifecycleObserver` polls every **15 seconds**  
- Offline inventory cache available when configured  
- Mandatory update gate unchanged  

**Users do not re-enter server URL** after normal evening shutdown if URL was saved.

---

## Task Scheduler alternative (optional)

If the PC must remain powered but services stopped:

| Task | Trigger | Action |
|------|---------|--------|
| WEBSTUDIO Morning | Weekdays 08:00 | `start-business-day.ps1` |
| WEBSTUDIO Evening | Weekdays 20:00 | `stop-business-day.ps1` |

Delayed Start already covers boot; Task Scheduler is optional for service-only stop/start without PC power cycle.

---

## Weekend / holiday

- If PC stays off multiple days: schedulers catch up on first run (backup may trigger immediately if overdue)  
- Tally incremental sync uses `last_successful_sync_at` — no full reload  
- Review Tally dashboard Monday morning for sync failures over the break  

---

## Checklist

### Daily open

- [ ] Server PC powered on (or already running)  
- [ ] `/health/live` returns OK from one client  
- [ ] Tally operational widget shows expected status  

### Daily close

- [ ] Run `stop-business-day.ps1` or confirm graceful service stop  
- [ ] Power off server PC (or leave PC on with services stopped per policy)  

---

## Related documents

- [WINDOWS_SERVICE_GUIDE.md](./WINDOWS_SERVICE_GUIDE.md)  
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)  
- [RECOVERY_GUIDE.md](./RECOVERY_GUIDE.md)
