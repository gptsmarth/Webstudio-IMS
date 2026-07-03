---
Title: Production Deployment Report
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14A
Related Documents:
  - docs/milestones/m14/INSTALLATION_MANUAL.md
  - docs/milestones/m14/PRODUCTION_COMMISSIONING_GUIDE.md
  - docs/milestones/m14/FIRST_STARTUP_CHECKLIST.md
---

# Production Deployment Report (M14A)

## Executive Summary

Milestone **14A** delivers the **complete production deployment guide** for WEBSTUDIO IMS. The 14-step installation sequence was validated against existing M12/M13 production code, installers, and startup orchestration — **no application code changes** were required.

| Deliverable | Path |
|-------------|------|
| Installation Manual | [INSTALLATION_MANUAL.md](INSTALLATION_MANUAL.md) |
| Production Commissioning Guide | [PRODUCTION_COMMISSIONING_GUIDE.md](PRODUCTION_COMMISSIONING_GUIDE.md) |
| First Startup Checklist | [FIRST_STARTUP_CHECKLIST.md](FIRST_STARTUP_CHECKLIST.md) |

---

## Installation sequence validation

Each step maps to **implemented** production artifacts (validated by code and script review).

| # | Step | Implementation | Validation method |
|---|------|----------------|-------------------|
| 1 | Windows server installation | Windows **11 Pro** dedicated PC (project standard) | OS checklist in Installation Manual §1 |
| 2 | PostgreSQL installation | PG 16 service `postgresql-x64-16`; `ensure-postgresql.ps1` | `Get-Service`; installer detect |
| 3 | WEBSTUDIO Server installation | `WEBSTUDIO Server Setup.exe` + `server-install-post.ps1` | Directory layout; pip install |
| 4 | Windows Service registration | `install-webstudio-service.ps1` (NSSM, delayed auto) | `Get-Service "WEBSTUDIO Server"` |
| 5 | Environment configuration | `config/env/.env` from template; JWT generation | `config.py` production gates |
| 6 | Database initialization | `alembic upgrade head` in post-install + service install | `webstudio.alembic_version` |
| 7 | Scheduler initialization | `run_startup_orchestration()` → `restore_scheduler_state()` | `scheduler_runtime_state` table |
| 8 | Backup scheduler | `WEBSTUDIO_BACKUP_SCHEDULER=1` → `backup_scheduler_loop()` | Env + scheduler row `backup` |
| 9 | Notification scheduler | `WEBSTUDIO_NOTIFICATION_SCHEDULER=1` → `notification_scheduler_loop()` | Env + row `notification_delivery` |
| 10 | Tally scheduler | `WEBSTUDIO_TALLY_SCHEDULER=1` → `_tally_scheduler_loop()` | Env + row `tally_sync`; settings post-wizard |
| 11 | AI provider configuration | `.env` keys + Settings → Integrations; `resolve_ai_config()` | Startup `ai_configuration` check |
| 12 | API key configuration | Settings → Integration keys; `/api/v1/admin/integration-keys` | Encrypted storage; post-wizard |
| 13 | First administrator login | Blocked until init; desktop routes to wizard | `GET /api/v1/setup/status` |
| 14 | Setup Wizard completion | `SetupService.initialize` + `confirm_recovery_key` | `system_initialized=true` |

**Verdict:** Sequence is **complete and consistent** with production codebase.

---

## Key code references

| Concern | Path |
|---------|------|
| Post-install orchestration | `infra/windows/server-installer/server-install-post.ps1` |
| Service install | `infra/windows/install-webstudio-service.ps1` |
| Startup checks + scheduler restore | `services/startup_orchestrator.py` |
| Scheduler background tasks | `app.py` lifespan (Tally, backup, notification, …) |
| Setup wizard API | `services/setup_service.py` |
| Desktop wizard UI | `apps/desktop/src/pages/SetupWizardPage.tsx` |
| Alembic head (current) | `0042_deployment_monitoring` |

---

## Scheduler environment matrix (production)

| Scheduler | Env flag | Default in NSSM / `.env.example` |
|-----------|----------|----------------------------------|
| Tally sync | `WEBSTUDIO_TALLY_SCHEDULER` | `1` |
| Backup | `WEBSTUDIO_BACKUP_SCHEDULER` | `1` |
| Notifications | `WEBSTUDIO_NOTIFICATION_SCHEDULER` | `1` |
| Maintenance | `WEBSTUDIO_MAINTENANCE_SCHEDULER` | `1` |
| Audit retention | `WEBSTUDIO_AUDIT_RETENTION_SCHEDULER` | `1` |
| Tally connectivity probe | `WEBSTUDIO_TALLY_CONNECTIVITY_PROBE` | `1` |
| GitHub release sync | `WEBSTUDIO_RELEASE_SYNC_SCHEDULER` | Optional; off unless enabled in settings |

Persistence: `webstudio.scheduler_runtime_state` (migration 0035+).

---

## Setup Wizard flow (steps 13–14)

```
Desktop connects → GET /api/v1/setup/status
    → system_initialized: false
    → Setup Wizard (3 steps)
    → POST /api/v1/setup/initialize
    → POST /api/v1/setup/confirm-recovery-key
    → system_initialized: true
    → Login enabled
```

Recovery key is **mandatory** before production use; stored offline by Main Admin.

---

## Gaps and operator notes

| Item | Note |
|------|------|
| OS naming | User sequence says “Windows Server”; product deploys to **Windows 11 Pro** dedicated server PC per PROJECT_BIBLE and M12B |
| Live install evidence | 14A validates **documentation against code**; field execution evidence is captured in 14B–14D |
| PostgreSQL bundling | Optional payload in server installer; manual PG install supported |
| Integration keys | Post-wizard only; not required for first boot |
| Tally / AI | Configured after wizard in Settings; schedulers start but sync/enrichment respect settings |

---

## M14A exit criteria

| Criterion | Status |
|-----------|--------|
| Installation Manual published | ✅ |
| Production Commissioning Guide published | ✅ |
| First Startup Checklist published | ✅ |
| 14-step sequence validated against codebase | ✅ |
| No feature / UI / API / DB redesign | ✅ |

---

## Next sub-milestone

**14B — Production configuration** — apply and verify production `.env`, schedules, release channel, and security hardening on target hardware.

**STOP — M14A complete.**
