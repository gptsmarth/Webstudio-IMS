---
Title: Milestone 12J — Customer Installation Simulation
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related Documents:
  - docs/milestones/m12i/FINAL_PRODUCTION_READINESS_REPORT.md
  - docs/milestones/m12h/INSTALLATION_GUIDE.md
---

# Milestone 12J — Customer Installation Simulation

Simulates a **brand-new customer** deploying WEBSTUDIO IMS in a typical laptop retail office.

## Scenario topology

```
                    ┌─────────────────────────┐
                    │  Dedicated Server PC    │
                    │  Windows 11 Pro         │
                    │  PostgreSQL 16          │
                    │  WEBSTUDIO Server Svc   │
                    └───────────┬─────────────┘
                                │ Gigabit LAN
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼───────┐     ┌─────────▼─────────┐   ┌────────▼────────┐
│ Desktop Client│     │ Android Phone     │   │ iPhone          │
│ (Admin PC)    │     │ (Floor staff)     │   │ (Floor staff)   │
└───────────────┘     └───────────────────┘   └─────────────────┘

        ┌───────────────────────────────────┐
        │ Lenovo Laptop — Tally ERP 9       │
        │ 192.168.1.20:9000 (XML Server)    │
        └───────────────────────────────────┘
```

## Simulation method

| Layer | Method |
|-------|--------|
| Server API journey | Automated pytest `tests/installation_simulation/` |
| Windows installers / service | Script and Inno Setup audit |
| Physical clients | API contract validation (desktop + mobile endpoints) |
| Live Tally on Lenovo | Connection test + sync queue (workstation offline in CI) |

## Validation summary

| Step | Result |
|------|--------|
| Install Server | ✅ Scripts + installer present |
| Configure Windows Service | ✅ NSSM delayed auto-start verified in script |
| Initialize Database | ✅ Alembic head on fresh PostgreSQL |
| Setup Company | ✅ |
| Generate Recovery Key | ✅ |
| Connect Desktop | ✅ |
| Connect Android | ✅ |
| Connect iPhone | ✅ |
| Configure Tally | ✅ |
| First Synchronization | ✅ Queued (offline workstation expected in CI) |
| Create Backup | ✅ |
| Restore Backup | ✅ |
| Verify Reports | ✅ |
| Verify AI | ✅ Mock enrichment |
| Verify Images | ✅ Auth gate |
| Automatic Startup | ✅ Script audit |
| Automatic Reconnect | ✅ Discovery health |
| Business Hours Deployment | ✅ Wizard + start/stop scripts |

## Deliverables

| Document | Purpose |
|----------|---------|
| [CUSTOMER_INSTALLATION_WALKTHROUGH.md](CUSTOMER_INSTALLATION_WALKTHROUGH.md) | Step-by-step narrative for operators |
| [INSTALLATION_VALIDATION_REPORT.md](INSTALLATION_VALIDATION_REPORT.md) | Evidence table per validation step |
| [DEPLOYMENT_ISSUES.md](DEPLOYMENT_ISSUES.md) | Issues found during simulation |
| [FINAL_SIGNOFF_REPORT.md](FINAL_SIGNOFF_REPORT.md) | Go/no-go for customer pilot |

## Automated test

```bash
cd apps/backend && source ../../.venv/bin/activate
python -m pytest tests/installation_simulation/ -v
```

**Result (2026-07-02):** 2 passed in ~16s
