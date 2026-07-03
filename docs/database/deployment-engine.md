---
Title: Deployment Engine Database Schema
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related: M13D, migration 0040_deployment_engine
---

# Deployment Engine — Database Schema

## Table: `webstudio.release_deployment_runs`

Tracks orchestrated deployment runs with step-level audit and rollback metadata.

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Run identifier |
| `job_id` | BIGINT | FK to `release_download_jobs` (nullable) |
| `release_version` | VARCHAR(32) | Target semver |
| `build_number` | INTEGER | Target build |
| `release_channel` | `release_channel` enum | Channel |
| `status` | VARCHAR(32) | `pending`, `running`, `completed`, `failed`, `rolling_back`, `rolled_back` |
| `current_step` | VARCHAR(64) | Last active step name |
| `steps_json` | JSONB | Array of `{step, status, timestamp, detail?, error?}` |
| `pre_backup_run_id` | BIGINT | `backup_runs.id` from pre-deploy backup |
| `pre_backup_filename` | VARCHAR(256) | Archive used for rollback |
| `rollback_backup_run_id` | BIGINT | Reserved for post-rollback restore run |
| `scheduler_snapshot` | JSONB | Scheduler state at deploy start |
| `config_snapshot_path` | TEXT | Path to configuration snapshot directory |
| `service_config_snapshot_path` | TEXT | Path to service config snapshot |
| `previous_release_id` | BIGINT | Catalog row to revert on rollback |
| `bundle_dir` | TEXT | Source package directory |
| `error_message` | TEXT | Failure / rollback detail |
| `performed_by_user_id` | BIGINT | Administrator who approved deploy |
| `created_at`, `updated_at`, `completed_at` | TIMESTAMPTZ | Lifecycle timestamps |

## Indexes

- `ix_release_deployment_runs_created` on `created_at`
- `ix_release_deployment_runs_status` on `status`

## Migration

`database/migrations/versions/0040_deployment_engine.py`
