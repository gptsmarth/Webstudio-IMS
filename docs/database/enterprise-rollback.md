---
Title: Enterprise Rollback Platform Schema
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related: M13F, migration 0041_enterprise_rollback
---

# Enterprise Rollback Platform — Database Schema

## Table: `webstudio.enterprise_rollback_runs`

Permanent rollback audit trail. **Records are never deleted by the application.**

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT PK | Rollback run identifier |
| `release_channel` | `release_channel` enum | Channel |
| `status` | VARCHAR(32) | `pending`, `running`, `completed`, `failed` |
| `current_step` | VARCHAR(64) | Last active step |
| `steps_json` | JSONB | Step audit array |
| `from_release_version` | VARCHAR(32) | Version being rolled back from |
| `from_build_number` | INTEGER | Build rolled back from |
| `from_release_id` | BIGINT | Catalog ID (from) |
| `to_release_version` | VARCHAR(32) | Target version |
| `to_build_number` | INTEGER | Target build |
| `to_release_id` | BIGINT | Catalog ID (to) |
| `deployment_run_id` | BIGINT | Linked deployment run |
| `deployment_event_id` | BIGINT | Linked deployment center event |
| `pre_rollback_backup_filename` | VARCHAR(256) | Safety backup before rollback |
| `database_restore_filename` | VARCHAR(256) | Backup used for DB restore |
| `scheduler_snapshot` | JSONB | Scheduler state applied |
| `config_snapshot_path` | TEXT | Configuration snapshot path |
| `service_config_snapshot_path` | TEXT | Service config snapshot path |
| `target_bundle_dir` | TEXT | Backend bundle restored |
| `health_status` | JSONB | Post-rollback health probe results |
| `performed_by_user_id` | BIGINT | Administrator |
| `error_message` | TEXT | Failure detail |
| `created_at`, `updated_at`, `completed_at` | TIMESTAMPTZ | Lifecycle |

## Migration

`database/migrations/versions/0041_enterprise_rollback.py`
