---
Title: Milestone 11 — Backup & Recovery Validation Report
Version: 1.0.0
Status: Complete
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related Documents: docs/milestones/m11/DATABASE_QA_REPORT.md
---

# Backup & Recovery Validation Report

## Backup formats

| Format | Extension | Magic | Status |
|--------|-----------|-------|--------|
| TAR.GZ | `.tar.gz` | gzip header | ✅ Default |
| WSB | `.wsb` | `WEBSTUDIO-BACKUP\x00` | ✅ Branded wrapper |

Manifest version: **2.1** (`backup_manifest.py`)

## Archive contents structure

```
backup archive
├── manifest.json
├── database.sql          # pg_dump --schema webstudio --data-only
├── config/
│   ├── settings-registry.json
│   ├── application.env.snapshot
│   └── asset-manifest.json
└── assets/
    ├── brand-logos/
    ├── product-images/
    ├── company/
    └── uploads/
```

## Entity coverage matrix

| Entity | In DB dump | In manifest stats | In contents list | Verified by tests |
|--------|------------|-------------------|------------------|-------------------|
| Inventory | ✅ | ✅ `inventory_count` | ✅ | Restore engine |
| Product models | ✅ | ✅ | ✅ | ✅ |
| Brands | ✅ | ✅ | ✅ | ✅ |
| Locations | ✅ | ✅ | ✅ | ✅ |
| Users | ✅ | ✅ | ✅ | ✅ |
| Roles / permissions | ✅ (users + settings) | ✅ `roles_permissions` | ✅ | Partial |
| Custom access roles | ✅ in dump | ⚠️ not in `BACKUP_DATABASE_TABLES` | ✅ logical | BACK-007 |
| Sales | ✅ | ✅ | ✅ | ✅ |
| Reports config | ✅ via settings | ✅ | ✅ | Settings scope restore |
| Notifications | ✅ | ✅ | ✅ | ✅ |
| Audit logs | ✅ | ✅ | ✅ | ✅ |
| Settings | ✅ | ✅ | ✅ | ✅ |
| Company information | ✅ + assets | ✅ | ✅ | ✅ |
| Product images | ✅ assets | ✅ | ✅ | ✅ |
| AI / Gemini config | ✅ settings hash | ✅ `gemini_configuration_version` | ✅ | ✅ |
| Integration config | ✅ | ✅ | ✅ | ✅ |
| Tally configuration | ✅ settings hash | ✅ `tally_configuration_version` | ✅ | ✅ |
| Integration API keys | ✅ | ✅ | ✅ | ✅ |
| Backup history | ✅ `backup_runs` | ✅ | ✅ | ✅ |
| Restore history | ✅ `restore_runs` | ✅ | ✅ | ✅ |
| Refresh tokens / sessions | ✅ | ✅ `session_data` | ✅ | ✅ |
| Login events | ✅ | ✅ `login_history` | ✅ | ✅ |

## Automated tests (all passing)

| Test file | Coverage |
|-----------|----------|
| `test_backup_format.py` | Format detection, validate API, WSB import pipeline |
| `test_restore_engine.py` | Validate, preview, settings scope restore |
| `test_backup_enterprise.py` | Enterprise backup admin flows |
| `test_backup_admin.py` | Backup CRUD, archive |
| `test_disaster_recovery.py` | Skipped (requires external config) |

## Workflows validated

| Workflow | Desktop | Mobile | Backend |
|----------|---------|--------|---------|
| Manual full backup | ✅ Settings panel | ✅ Backup screen | ✅ API |
| Internal scheduled backup | ✅ | View status | ✅ |
| Validate backup | ✅ | ✅ | ✅ |
| Preview restore | ✅ RestoreWizard | ✅ | ✅ |
| Execute restore (scoped) | ✅ | Admin only | ✅ |
| Import downloaded backup | ✅ | ✅ | ✅ WSB + TAR.GZ |
| Export / download backup | ✅ | ✅ | ✅ |
| Recovery center / disaster | ✅ | — | ⏭ Skipped |
| Retention / archive old backups | ✅ | — | ✅ |
| Rollback after failed restore | ✅ | — | Code review |

## Fresh installation restore (staging drill required)

**M11 automated validation:** Restore pipeline processes imported archives through `RestoreEngine` with integrity checks, manifest validation, FK verification, and asset restoration.

**Manual staging drill (recommended before M12):**

1. Install fresh backend + empty DB on clean host
2. Complete setup wizard
3. Import manually downloaded `.wsb` from production-like system
4. Verify all entities in matrix above are present
5. Log in, open inventory, sales, audit, Tally settings, product images

## Known gaps

| ID | Issue | Severity |
|----|-------|----------|
| BACK-007 | Custom roles not in backup table catalog | Medium |
| BACK-013 | Test env stub SQL unless `WEBSTUDIO_BACKUP_REAL_DUMP=1` | Low |
| SEC-002 | No upload size cap on import | Medium |

## Verdict

Backup format and restore engine are **production-ready**. Complete one **full round-trip restore on a fresh installation** in staging to sign off disaster recovery.
