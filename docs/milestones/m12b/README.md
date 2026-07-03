---
Title: Milestone 12B — Business Hours Windows Deployment
Version: 1.0.0
Status: Complete
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
---

# Milestone 12B — Index

| Document | Description |
|----------|-------------|
| [WINDOWS_SERVICE_GUIDE.md](./WINDOWS_SERVICE_GUIDE.md) | WEBSTUDIO Server Service installation and operation |
| [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) | End-to-end server deployment |
| [RECOVERY_GUIDE.md](./RECOVERY_GUIDE.md) | Failure and disaster recovery |
| [BUSINESS_HOURS_DEPLOYMENT_GUIDE.md](./BUSINESS_HOURS_DEPLOYMENT_GUIDE.md) | Daily power on/off operations |

## Implementation summary

- Migration **0035** — `scheduler_runtime_state` table  
- Startup orchestrator — PostgreSQL, storage, config, AI, Tally checks  
- Graceful shutdown — Tally checkpoint, scheduler persist, log flush  
- Windows scripts — `infra/windows/*.ps1`  
- Client auto-reconnect — Desktop + Flutter (15 s polling)  
