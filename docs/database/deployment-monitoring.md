---
Title: Deployment Monitoring Schema
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
---

# Deployment Monitoring

## Tables

### `webstudio.client_version_observations`

Records client version telemetry when desktop or mobile clients call `GET /api/v1/client-updates/check`.

| Column | Type | Description |
|--------|------|-------------|
| `platform` | `varchar(32)` | e.g. `desktop_windows`, `mobile_android` |
| `client_version` | `varchar(32)` | Installed client version |
| `release_channel` | `varchar(16)` | Channel at observation time |
| `observation_count` | `int` | Incremented on each check |
| `first_seen_at` | `timestamptz` | First observation |
| `last_seen_at` | `timestamptz` | Most recent observation |

Unique on (`platform`, `client_version`).

## Analytics API

`GET /api/v1/deployment/center/analytics` aggregates:

- Release download queue, history, and failures
- Deployment and rollback run history
- Deployment durations and health check results
- Desktop and mobile version distribution
- Retry queue and GitHub polling state
- Scheduler recovery for backup, Tally, and GitHub sync

Migration: `0042_deployment_monitoring`.
