---
Title: Deployment Analytics Report
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: M13I
Related Documents:
  - docs/api/openapi/deployment-center-v1.yaml
  - docs/database/deployment-monitoring.md
---

# Deployment Analytics Report (M13I)

## Executive Summary

M13I delivers **Enterprise Deployment Monitoring** for WEBSTUDIO IMS. Administrators can view aggregated analytics inside **Settings → Deployment** (Administration) without UI redesign. A single analytics API aggregates release downloads, deployment and rollback history, health checks, client version distribution, failures, retry queue, GitHub polling, and scheduler recovery.

## Tracked Metrics

| Metric | Source | Analytics section |
|--------|--------|-------------------|
| Release downloads | `release_download_jobs` | `release_downloads`, summary counts |
| Deployment history | `release_deployment_events` | `deployment_history` |
| Rollback history | `enterprise_rollback_runs` | `rollback_history` |
| Deployment duration | `release_deployment_runs` timestamps | `deployment_durations` |
| Health check history | Deploy `steps_json`, rollback `health_status` | `health_check_history` |
| Desktop version distribution | `client_version_observations` | `desktop_version_distribution` |
| Mobile version distribution | `client_version_observations` | `mobile_version_distribution` |
| Deployment failures | Events, runs, rollbacks, failed downloads | `deployment_failures` |
| Retry queue | `release_download_jobs` retry fields | `retry_queue` |
| GitHub polling history | `scheduler_runtime_state` + sync status | `github_polling_history` |
| Scheduler recovery | `scheduler_runtime_state.state_json` | `scheduler_recovery` |
| Tally scheduler recovery | `tally_sync` scheduler row | `tally_scheduler_recovery` |
| Backup scheduler recovery | `backup` scheduler row | `backup_scheduler_recovery` |

## Architecture

| Component | Path |
|-----------|------|
| Analytics service | `apps/backend/src/webstudio_backend/services/deployment_monitoring_service.py` |
| Deployment Center delegate | `apps/backend/src/webstudio_backend/services/deployment_center_service.py` |
| Client version telemetry | `client_version_observation_repository.py` + `client_update_service.py` |
| API endpoint | `GET /api/v1/deployment/center/analytics` |
| OpenAPI | `docs/api/openapi/deployment-center-v1.yaml` |
| Database migration | `0042_deployment_monitoring` → `client_version_observations` |

## Administration UI

Extended **Deployment Center** (`apps/desktop/src/components/settings/DeploymentCenter.tsx`) with analytics panels using existing `stg-backup-admin` table and readonly grid patterns:

- Summary metrics (pending/failed downloads, retry queue, failures)
- Retry queue table
- Deployment failures table
- Deployment durations table
- Health check history table
- Desktop and mobile version distribution tables
- Rollback history table
- GitHub polling and scheduler recovery panels

No new navigation items or layout redesign.

## Client Version Telemetry

Each `GET /api/v1/client-updates/check` upserts a row in `client_version_observations` keyed by `(platform, client_version)`. Observation count and `last_seen_at` update on every check, powering version distribution analytics without client-side changes beyond existing update checks.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/releases/test_deployment_monitoring.py` | Analytics endpoint + service |
| OpenAPI `deployment-center-v1.yaml` | `/analytics` path documented |
| Desktop Deployment Center | Loads analytics alongside dashboard |

## Sign-off

Enterprise Deployment Monitoring is **complete**. Analytics are available in Administration (Deployment Center) and via the deployment analytics API.

**STOP — M13I deliverable complete.**
