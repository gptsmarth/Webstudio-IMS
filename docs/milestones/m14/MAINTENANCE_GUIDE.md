---
Title: Maintenance Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14H
Audience: IT operators, Main Admin, WEBSTUDIO engineers
Related Documents:
  - docs/milestones/m14/ADMINISTRATOR_MANUAL.md
  - docs/milestones/m14/OPERATIONS_MANUAL.md
---

# Maintenance Guide (M14H)

Preventive maintenance, scheduled care, and deep troubleshooting for **WEBSTUDIO IMS** production deployments.

---

## 1. Maintenance philosophy

| Principle | Application |
|-----------|-------------|
| **Evidence over assumption** | Run validation scripts; keep logs |
| **Backup before change** | Manual backup before every upgrade |
| **Least disruption** | Schedule maintenance outside business hours |
| **No manual DDL** | Database changes only via Alembic migrations |
| **Document every change** | Record version, date, operator in handover log |

---

## 2. Maintenance schedule

| Task | Frequency | Owner | Reference |
|------|-----------|-------|-----------|
| Verify backup succeeded | Daily | Admin | [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md) § Backups |
| Review Tally sync health | Daily | Admin | Dashboard |
| Check disk space (data root) | Weekly | IT | § 4 Disk maintenance |
| Off-site backup copy | Weekly | IT | USB/NAS |
| Review user access / disabled accounts | Monthly | Admin | Settings → Users |
| Windows security updates | Monthly | IT | After hours + reboot test |
| PostgreSQL vacuum stats review | Monthly | IT | § 5 Database |
| Integration key rotation (if policy) | Quarterly | Admin | [ADMINISTRATOR_MANUAL.md](ADMINISTRATOR_MANUAL.md) § API keys |
| Restore drill | Quarterly | IT + Admin | [RESTORE_CHECKLIST.md](RESTORE_CHECKLIST.md) |
| Password policy review | Quarterly | Admin | Settings → Security |
| Production certification re-run | Quarterly | WEBSTUDIO engineer | § 8 Validation |
| Software upgrade | Per release | IT | [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md) § Updates |

---

## 3. Daily maintenance

### 3.1 Server

- [ ] **WEBSTUDIO Server** service = Running
- [ ] PostgreSQL service = Running
- [ ] No repeating ERROR lines in `webstudio-api.log` (last 15 minutes)
- [ ] Backup timestamp updated (if scheduled overnight)

### 3.2 Integrations

- [ ] Tally PC on with company loaded (if Tally sync enabled)
- [ ] Tally Sync Health = Healthy or documented Offline reason
- [ ] AI enrichment: optional — verify only if staff report failures

### 3.3 Clients

- [ ] Desktop toolbar **Connected** on sample workstations
- [ ] Mobile sync status on floor devices (if used)

---

## 4. Disk and storage maintenance

### 4.1 Monitor free space

Startup orchestration warns when data root free space is low. Check weekly:

```powershell
Get-PSDrive D | Select-Object Used, Free
```

| Threshold | Action |
|-----------|--------|
| < 20% free | Archive old logs; prune backup retention |
| < 10% free | **Urgent** — expand disk or move backup folder |
| Backup failures | Often disk-full — see logs |

### 4.2 Log rotation

| Log | Location | Rotation |
|-----|----------|----------|
| API log | `WEBSTUDIO_LOG_DIR` / `logs\webstudio-api.log` | 10 MB × 5 files (automatic) |
| Service stdout | NSSM rotation (service install) | Automatic |
| Desktop client | `%APPDATA%\WEBSTUDIO\logs` | Manual archive if large |

Example config: `config/logging/logrotate-webstudio.conf.example`

### 4.3 Backup folder hygiene

- Enforce retention policy in Settings → Backup.
- Move archives older than retention to off-site storage before deletion.
- Never delete the most recent **verified** backup.

---

## 5. Database maintenance

| Task | Procedure |
|------|-----------|
| **Migrations** | Only `alembic upgrade head` — never manual SQL on production |
| **Vacuum** | PostgreSQL autovacuum — monitor `pg_stat_user_tables` if bloat suspected |
| **Connections** | Tune `DATABASE_POOL_SIZE` if concurrent user warnings in certification |
| **Audit retention** | Scheduler purges per policy — no manual deletion |

```powershell
cd D:\WEBSTUDIO-IMS\apps\backend
..\..\venv\Scripts\alembic.exe current
..\..\venv\Scripts\alembic.exe heads
```

Current and head revision must match after every upgrade.

---

## 6. Service and Windows maintenance

### 6.1 Service health

```powershell
Get-Service "WEBSTUDIO Server", "postgresql-x64-16"
```

After Windows updates that require reboot:

1. Confirm both services start automatically.
2. `GET /health/ready`
3. Spot-check inventory search from desktop.

### 6.2 Certificate renewal (HTTPS)

If using TLS on LAN:

| Step | Action |
|------|--------|
| 1 | Generate new certificate before expiry |
| 2 | Update `TLS_CERT_PATH` and `TLS_KEY_PATH` in `.env` |
| 3 | `Restart-Service "WEBSTUDIO Server"` |
| 4 | Update client saved URLs if hostname changed |

LAN HTTP deployments (no TLS) skip this section.

### 6.3 Scheduler runtime

Schedulers (backup, Tally sync, audit purge) persist state in `scheduler_runtime_state`.

- After long outages: no manual fix — startup restores `next_run_at`.
- If paths changed: re-run Office Deployment Wizard.

---

## 7. Software maintenance

### 7.1 Patch cadence

| Component | Guidance |
|-----------|----------|
| WEBSTUDIO IMS | Upgrade per stable release — see Operations Manual |
| Windows 11 | Monthly security patches — test service after reboot |
| PostgreSQL | Minor patches via DBA policy — backup first |
| Desktop/mobile clients | Match server version after server upgrade |

### 7.2 Pre-upgrade maintenance

1. Manual backup + verify checksum
2. Export deployment summary (Deployment Center)
3. Note current `alembic` revision and `GET /api/v1/version`
4. Schedule maintenance window

### 7.3 Post-upgrade maintenance

1. `GET /health/ready`
2. Run all `validate-production-*.ps1` scripts
3. Spot-check Tally sync and backup create
4. Confirm client minimum versions accepted

---

## 8. Validation maintenance

Re-run certification quarterly or after major changes:

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\validate-production-certification.ps1 -BearerToken "<token>"
.\validate-production-network.ps1 -BearerToken "<token>"
.\validate-production-backup.ps1 -BearerToken "<token>"
.\validate-production-tally.ps1 -BearerToken "<token>"
```

| Report | When to archive |
|--------|-----------------|
| Certification JSON | Quarterly |
| Network validation | After firewall/IP change |
| Backup validation | After restore drill |
| Tally validation | After Tally PC replacement |

**References:** [PRODUCTION_CERTIFICATION_REPORT.md](PRODUCTION_CERTIFICATION_REPORT.md) · [NETWORK_VALIDATION_REPORT.md](NETWORK_VALIDATION_REPORT.md)

---

## 9. Troubleshooting (maintenance depth)

### 9.1 Diagnostic collection

When escalating to WEBSTUDIO support, collect:

| Artifact | Path / command |
|----------|----------------|
| API log (last 200 lines) | `logs\webstudio-api.log` |
| Service status | `Get-Service "WEBSTUDIO Server"` |
| Health endpoints | `/health/live`, `/health/ready` |
| Version | `GET /api/v1/version` |
| Alembic revision | `alembic current` |
| Certification output | `validate-production-certification.ps1` |
| Windows version | `winver` |

### 9.2 PostgreSQL issues

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| API 503 on `/health/ready` | PG stopped | `Start-Service postgresql-x64-16` |
| Connection pool exhausted | Too many clients | Increase `DATABASE_POOL_SIZE` |
| Migration mismatch | `alembic current` ≠ head | `alembic upgrade head` after backup |

### 9.3 Performance degradation

| Symptom | Check |
|---------|-------|
| Slow inventory search | Certification performance section; index migrations 0012/0027 applied |
| Slow reports | Disk I/O; run during off-peak |
| High concurrent users | Pool size; see [PERFORMANCE_CERTIFICATION.md](PERFORMANCE_CERTIFICATION.md) |

Load-test procedure documented in Performance Certification for staging servers with ≥10k inventory / ≥50k sales.

### 9.4 Tally maintenance

| Issue | Maintenance action |
|-------|-------------------|
| Checkpoint stale | Manual sync; verify GUID advances in dashboard |
| Repeated model mismatches | Update product model catalogue |
| Tally PC replaced | Update hostname in Settings → Tally; test connection |

### 9.5 AI provider maintenance

| Issue | Action |
|-------|--------|
| Rate limited | Check provider dashboard; adjust fallback chain |
| Key expired | Rotate in Settings → Integrations |
| Enrichment disabled | Toggle `ai_enrichment_enabled` |

### 9.6 Recovery Center

Desktop **Recovery Center** (Settings → Backup) provides:

- Network diagnostics wizard
- Backup verify and restore preview
- Guided recovery after server outage

**Reference:** [m12h/RECOVERY_GUIDE.md](../m12h/RECOVERY_GUIDE.md) · [m12e/RECOVERY_GUIDE.md](../m12e/RECOVERY_GUIDE.md)

---

## 10. End-of-life and decommission

| Step | Action |
|------|--------|
| 1 | Final full backup + off-site copy |
| 2 | Export audit log and reports if required for compliance |
| 3 | Revoke AI and integration API keys at providers |
| 4 | Stop WEBSTUDIO Server service |
| 5 | Archive or securely wipe `D:\WEBSTUDIO-IMS` per data policy |
| 6 | Remove firewall rules (`WEBSTUDIO IMS*`) |

---

## 11. Related documents

| Topic | Document |
|-------|----------|
| Administrator setup | [ADMINISTRATOR_MANUAL.md](ADMINISTRATOR_MANUAL.md) |
| Daily operations | [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md) |
| Disaster recovery | [DISASTER_RECOVERY_GUIDE.md](DISASTER_RECOVERY_GUIDE.md) |
| Business hours | [m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md](../m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md) |
| Employee guide | [m12h/EMPLOYEE_GUIDE.md](../m12h/EMPLOYEE_GUIDE.md) |
