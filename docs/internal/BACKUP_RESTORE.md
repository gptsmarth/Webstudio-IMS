# WEBSTUDIO IMS — Backup & Restore Developer Guide

Internal reference for the enterprise backup, restore, and disaster recovery stack.

## Backup format

Enterprise backups are `.tar.gz` archives with this layout:

```
manifest.json
database.sql
assets/brand-logos/
assets/product-images/
assets/company/
assets/uploads/
config/application.env.snapshot
config/settings-registry.json
config/asset-manifest.json
```

The PostgreSQL dump uses `--schema=webstudio --data-only`. Restore Center
accepts supported data-only archives with the same Alembic revision as the
destination. An app-version difference generates a warning. Use an isolated
installation at the matching revision to recover an older schema, then upgrade
it. A trusted legacy SQL or full dump requires separate administrator recovery.

Restore Center verifies archive integrity and recalculates the format 2.1
content checksum. New backups include a SHA-256 checksum for each managed file.
Use archives from a trusted source because checksums verify integrity without
establishing who created the backup.

The ordinary IMS database owner loads a restricted set of data-only `pg_dump`
statements in one transaction. It checks the destination revision on that
connection, preserves migration state, keeps foreign-key triggers enabled,
defers foreign-key checks for loading, and restores the original constraint
timing. Owned sequence positions are restored transactionally. For new backups,
the inventory, sales, user and product model counts come from the dump and are
checked before commit. The PostgreSQL 17+ timeout line remains compatible with
older destination servers.

The server stages and verifies files under the configured `WEBSTUDIO_DATA_ROOT/assets`.
It merges brand logos, product images, company assets and uploads into existing
or newly created folders. On a failed database load it reverts the files changed
by the attempt. PostgreSQL and the filesystem have separate commit mechanisms.
After an interrupted recovery, keep the service closed to staff, inspect the
verification result, and use the emergency backup to recover if needed.

### Manifest (`manifest.json`)

Written into every archive (readable before restore via `BackupEngine.read_manifest_from_archive` or tar extraction).

| Field | Description |
|-------|-------------|
| `format_version` | Manifest schema integer (currently `2`) |
| `backup_version` | Enterprise backup format version (`2.1`) |
| `database_dump_mode` | `data_only` (current) or `full` (legacy) |
| `app_version` | Application version at backup time |
| `schema_version` | Alembic migration version |
| `backup_type` | `full` / `incremental` (incremental falls back to full) |
| `trigger_type` | `manual`, `scheduled`, `emergency` |
| `created_by` / `creator` | Operator display name |
| `created_date` / `timestamp` | ISO-8601 UTC |
| `company_name` | Company profile name |
| `database_size_bytes` | PostgreSQL database size |
| `backup_size_bytes` | Compressed archive size |
| `inventory_count`, `sales_count`, `users_count`, `audit_log_count` | Record counts |
| `notification_count`, `product_image_count`, `serial_numbers_count` | Extended counts |
| `brands_count`, `locations_count`, `product_models_count` | Reference data counts |
| `managed_asset_file_count` | Application-managed files in archive |
| `checksum` | SHA-256 content checksum (database.sql + settings snapshot) |
| `checksum_algorithm` | `sha256` |
| `tally_configuration_version` | Hash of Tally settings |
| `gemini_configuration_version` | Hash of Gemini settings |
| `encrypted` | `false` until encryption is enabled |
| `encryption_algorithm` | `null` until encryption is enabled |
| `compression` | `gzip` |

Implementation: `services/backup_manifest.py`, `services/backup_engine.py`.

### Supported formats

| Format ID | Extension | Loader |
|-----------|-----------|--------|
| `tar_gz` | `.tar.gz` | `TarGzBackupLoader` |
| `wsb` | `.wsb` | `WsbBackupLoader` (optional `WEBSTUDIO-BACKUP` header + gzip tar payload) |
| `legacy_sql` | `.sql` | `LegacySqlBackupLoader` |

Format detection is automatic (`services/backup_format.py`). Internal and imported backups share the same restore pipeline.

## Restore flow

1. **Validate** — `POST /api/v1/settings/backups/validate`
2. **Preview** — `POST /api/v1/settings/backups/preview` (required before restore in UI)
3. **Emergency backup** — automatic for `entire_database` restores
4. **Restore** — `POST /api/v1/settings/backups/restore` (`confirmed: true`)
5. **Post-restore verification** — automatic table/count checks
6. **Rollback** — `POST /api/v1/settings/backups/rollback` if verification fails

Implementation: `services/restore_engine.py`.

## Verification pipeline

### Pre-restore validation

- Archive integrity (tar/gzip)
- Manifest presence
- Checksum (DB row or manifest content checksum)
- Compatibility report (app/schema/backup version, migration required)

### Admin integrity verification

`POST /api/v1/settings/backups/{filename}/verify`

Returns checksum, compression, manifest validation, corruption detection, overall health.

Implementation: `services/backup_verification.py`, `services/backup_admin_service.py`.

### Post-restore verification

Checks database connectivity, required tables, settings, users, inventory/sales/audit counts, Tally configuration, images (URL-based).

## Rollback process

1. Restore Center creates and verifies an emergency backup before a full-database restore (`trigger_type=emergency`).
2. Emergency filename stored on `restore_runs.emergency_backup_filename`.
3. If post-restore verification fails, API returns `rollback_recommended: true`.
4. Rollback reuses `execute_restore` against the emergency archive with `create_emergency_backup=False`.

## Extension points

| Area | Module | Status |
|------|--------|--------|
| Backup formats | `services/backup_format.py` | `tar_gz`, `wsb`, `legacy_sql` loaders via `BackupFormatLoader` |
| Encryption | `services/backup_encryption.py` | `NoOpBackupEncryption` default |
| Cloud storage | `services/backup_storage.py` | Stubs: `google_drive`, `onedrive`, `dropbox`, `network_share` |
| NAS / external | `services/backup_storage.py` | Local-path stubs |
| Mobile API | `GET/POST /api/v1/settings/backups/mobile/*` | Read/trigger only; no restore |
| Notifications | `services/backup_alert_service.py` | Gated by `backup_alerts_enabled` |

## Key API routes

| Route | Purpose |
|-------|---------|
| `POST /settings/backups` | Create backup |
| `POST /settings/backups/validate` | Compatibility + integrity |
| `POST /settings/backups/preview` | Restore preview |
| `POST /settings/backups/restore` | Execute restore |
| `POST /settings/backups/rollback` | Emergency rollback |
| `GET /settings/backups/admin/*` | Administration |
| `GET /settings/recovery/*` | Disaster recovery center |
| `GET /settings/backups/mobile/status` | Mobile status (future Flutter) |

## Portable disaster recovery

1. Create manual backup on the source machine.
2. Copy `.tar.gz` to USB, cloud, or external storage.
3. Install WEBSTUDIO IMS on the new machine and run migrations.
4. Open Restore Center → Import backup file → Restore.
5. Restart the backend when prompted.

No manual database editing or configuration file copying is required.

## Tests

- `apps/backend/tests/settings/test_backup_engine.py`
- `apps/backend/tests/settings/test_restore_engine.py`
- `apps/backend/tests/settings/test_backup_admin.py`
- `apps/backend/tests/settings/test_recovery.py`
- `apps/backend/tests/settings/test_disaster_recovery.py` — full business-state DR validation (requires `pg_dump` / `psql`)
