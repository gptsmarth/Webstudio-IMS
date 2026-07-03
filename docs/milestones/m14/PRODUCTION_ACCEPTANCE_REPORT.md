---
Title: Production Acceptance Report
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14F
Related Documents:
  - docs/milestones/m14/USER_ACCEPTANCE_CHECKLIST.md
  - docs/milestones/m14/ROLE_MATRIX_VALIDATION.md
  - docs/milestones/m11/README.md
---

# Production Acceptance Report (M14F)

## Executive Summary

Milestone **14F** executes **complete production acceptance** for WEBSTUDIO IMS — validating roles, functional modules, operations (backup, restore, sync, updates, rollback), and mobile offline behaviour against the implemented production codebase (M1–M13, M14A–E).

| Deliverable | Path |
|-------------|------|
| Production Acceptance Report | This document |
| User Acceptance Checklist | [USER_ACCEPTANCE_CHECKLIST.md](USER_ACCEPTANCE_CHECKLIST.md) |
| Role Matrix Validation | [ROLE_MATRIX_VALIDATION.md](ROLE_MATRIX_VALIDATION.md) |

**Verdict:** Production acceptance framework is **implemented and test-covered**. On-site UAT sign-off uses the user checklist.

---

## Acceptance validation matrix

### Roles

| Requirement | Check key | Validation |
|-------------|-----------|------------|
| Administrator | `role_administrator` | `main_admin` + `admin` in `PERMISSIONS_BY_ROLE` |
| Salesperson | `role_salesperson` | Matrix in `permissions.py`; tests in `test_permissions.py` |
| Stock Manager | `role_stock_manager` | Custom role template (inventory-heavy) |
| Custom Roles | `role_custom_access` | `ASSIGNABLE_PERMISSIONS` + `/api/v1/access-roles` |

### Functional modules

| Module | Check key | API / implementation |
|--------|-----------|-------------------|
| Inventory | `module_inventory` | `/api/v1/inventory` |
| Sales | `module_sales` | `/api/v1/sales` |
| Catalogue | `module_catalogue` | brands, product_models, locations |
| Reports | `module_reports` | `/api/v1/reports` |
| Notifications | `module_notifications` | `/api/v1/notifications` |
| Audit | `module_audit` | `/api/v1/audit_logs` |
| Backup | `module_backup` | `/api/v1/settings/backups` |
| Restore | `module_restore` | restore_engine + rollback |
| AI | `module_ai` | `resolve_ai_config` + capabilities |
| Tally | `module_tally` | `/api/v1/integrations/tally` |
| Global Search | `module_global_search` | `/api/v1/search` |
| Offline Mode | `module_offline_mode` | Flutter `core/offline/` |
| Synchronization | `module_synchronization` | Tally sync + Excel export |
| Auto Update | `module_auto_update` | `/api/v1/client-updates` |
| Rollback | `module_rollback` | `enterprise_rollback_engine` |

---

## API

```http
GET /api/v1/deployment/production-acceptance
```

Requires network administrator permission. Returns checks, role matrix summary, UAT checklist items, and recommendations.

---

## Prerequisites (M14A–E)

| Milestone | Gate |
|-----------|------|
| 14A | Server installed; setup wizard complete |
| 14B | LAN validation passed |
| 14C | Tally production validation (if Tally enabled) |
| 14D | Backup validation passed |
| 14E | Client deployment guides distributed |

---

## Automated test evidence

```
pytest apps/backend/tests/deployment/test_production_acceptance_validation.py — 3 passed
pytest apps/backend/tests/auth/test_permissions.py — role matrix
```

Prior QA: [m11/README.md](../m11/README.md) (desktop, backend, Flutter reports).

---

## UAT execution

Complete [USER_ACCEPTANCE_CHECKLIST.md](USER_ACCEPTANCE_CHECKLIST.md) on production or staging mirror with real staff accounts.

Minimum sign-off:

- One user per system role (Main Admin, Admin, Salesperson)
- One custom role (Stock Manager template)
- End-to-end sale reflection (Tally or manual)
- Backup verify + optional restore drill
- Mobile offline drill

---

## Sign-off

| Criterion | Status |
|-----------|--------|
| Role matrix documented | ✅ |
| All 15 functional/ops checks in API | ✅ |
| User acceptance checklist | ✅ |
| Role matrix validation doc | ✅ |
| Unit tests passing | ✅ |

**M14F complete. STOP.**
