---
Title: Recovery Guide — WEBSTUDIO Windows Server
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12B
---

# Recovery Guide — WEBSTUDIO Server on Windows

Procedures when the business-hours server fails, crashes, or loses power unexpectedly.

---

## Service recovery (automatic)

The WEBSTUDIO Server service is configured with:

| Policy | Setting |
|--------|---------|
| Startup | Automatic (Delayed Start) |
| First failure | Restart after 60 s |
| Second failure | Restart after 60 s |
| Third failure | Restart after 60 s |
| Fail count reset | 24 hours |

Configured by `infra/windows/configure-service-recovery.ps1`.

**After unclean power loss:** Windows boots → PostgreSQL starts → WEBSTUDIO Server starts (delayed) → startup orchestration restores scheduler state.

---

## Manual recovery steps

### Service will not start

1. Check PostgreSQL: `Get-Service postgresql-x64-16`  
2. Run `ensure-postgresql.ps1`  
3. Inspect `D:\WEBSTUDIO-IMS\logs\webstudio-api-error.log`  
4. Verify `.env` — especially `JWT_SECRET` length and `DATABASE_URL`  
5. Run migrations manually: `python -m alembic upgrade head`  
6. `Start-Service "WEBSTUDIO Server"`

### Scheduler state corrupted / stuck Tally sync

```sql
-- Clear stale in-progress flags (API also does this on startup)
UPDATE webstudio.tally_company_sync SET sync_in_progress = false WHERE sync_in_progress = true;
```

Scheduler timing rows live in `webstudio.scheduler_runtime_state`. Deleting a row resets that scheduler to immediate run on next start (last resort).

### Database restore required

1. Stop WEBSTUDIO Server  
2. Restore latest verified `pg_dump`  
3. `alembic upgrade head` if restore is behind current release  
4. Start service  
5. Clients reconnect automatically  

See DEPLOY-001 §13 Restore.

---

## Unexpected evening power loss

| Concern | Mitigation |
|---------|------------|
| Tally sync mid-run | Startup clears `sync_in_progress`; shutdown checkpoint when graceful |
| Scheduler timers | Persisted in PostgreSQL — resume from `next_run_at` |
| In-flight API requests | Lost; clients retry with exponential backoff |
| Open transactions | PostgreSQL crash recovery on PG start |

---

## Client-side recovery

| Symptom | Action |
|---------|--------|
| Desktop shows offline | Wait 15–30 s after server boot; or focus window |
| Mobile cannot reach server | App resumes polling on foreground; verify Wi‑Fi same subnet |
| Session expired | Re-login (refresh token may expire over long weekends) |

---

## Escalation checklist

- [ ] PostgreSQL running  
- [ ] WEBSTUDIO Server running  
- [ ] `/health/ready` returns 200  
- [ ] Disk space > 5% on `WEBSTUDIO_DATA_ROOT`  
- [ ] Latest backup verified this month  
- [ ] Tally dashboard shows expected scheduler status  

---

## Related documents

- [WINDOWS_SERVICE_GUIDE.md](./WINDOWS_SERVICE_GUIDE.md)  
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)  
- [DEPLOY-001 §16 Disaster Recovery](../../deployment/DEPLOYMENT_GUIDE.md)
