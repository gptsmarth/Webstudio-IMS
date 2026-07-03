---
Title: Scheduler Runtime State
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Migration: 0035_scheduler_runtime_state
---

# Scheduler Runtime State

Persists background job timing across business-hours server power cycles (Milestone 12B).

## Table

`webstudio.scheduler_runtime_state`

| Column | Purpose |
|--------|---------|
| `scheduler_key` | `tally_sync`, `backup`, `audit_retention`, `notification_delivery`, `maintenance` |
| `next_run_at` | When the scheduler should run next |
| `last_run_at` | Last completed cycle |
| `last_run_status` | `completed`, `failed`, `waiting`, etc. |
| `interval_seconds` | Default poll interval |
| `state_json` | Extra checkpoint metadata |

## Behaviour

- Updated after every scheduler cycle and every `WEBSTUDIO_SCHEDULER_PERSIST_SECONDS` (default 60)  
- On API startup, schedulers sleep until `next_run_at` instead of resetting timers  
- On graceful shutdown, final snapshot written before database pool closes  

See [BUSINESS_HOURS_DEPLOYMENT_GUIDE.md](../milestones/m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md).
