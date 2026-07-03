---
Title: Role Matrix Validation
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14F
Related Documents:
  - docs/milestones/m14/PRODUCTION_ACCEPTANCE_REPORT.md
  - apps/backend/src/webstudio_backend/core/permissions.py
---

# Role Matrix Validation (M14F)

Authoritative RBAC matrix for production acceptance. Source: `permissions.py` and `PermissionResolver`.

**Legend:** ✅ granted · ❌ denied · 🔧 custom (assignable) · — not applicable

---

## 1. System roles

| Capability | Main Admin | Admin | Salesperson | Service Account |
|------------|:----------:|:-----:|:-----------:|:---------------:|
| User management | ✅ | ❌ | ❌ | ❌ |
| Settings modify | ✅ | ❌ | 🔧 view only | ❌ |
| Inventory view | ✅ | ✅ | ✅ | ❌ |
| Inventory create/edit/archive | ✅ | ✅ | ❌ | ❌ |
| Inventory transfer | ✅ | ✅ | ✅ | ❌ |
| Stock edit (status) | ✅ | ✅ | ✅ | ❌ |
| Sales view | ✅ | ✅ | ✅ | ❌ |
| Sales create/cancel | ✅ | ✅ | ❌* | ❌ |
| Reports view/export | ✅ | ✅ | ❌ | ❌ |
| Catalogue CRUD | ✅ | ✅ | view + model edit | ❌ |
| Notifications manage | ✅ | ✅ | view | ❌ |
| Audit view/export | ✅ | ❌ | lifecycle only | ❌ |
| Backup / restore | ✅ | ✅ | ❌ | ❌ |
| Tally configure | ✅ | ❌ | ❌ | ❌ |
| Tally view/sync | ✅ | ✅ | ❌ | ❌ |
| Deployment / releases | ✅ | ❌ | ❌ | ❌ |
| Integration keys | ✅ | ❌ | ❌ | ❌ |
| Dashboard system status | ✅ | ✅ | ❌ | ❌ |

\*Salesperson has `sales:view` only; manual mark-as-sold is **Admin / Main Admin** per ADR-0011. Sales reflection via **Tally import**.

---

## 2. Stock Manager (recommended custom role)

Not a built-in `UserRole` — create via **Settings → Users → Access Roles**.

### Template permissions

```
inventory:view, create, edit, stock_edit, transfer, archive, restore, export
brands:view, edit
product_models:view, edit
locations:view, edit
dashboard:view, inventory_distribution, recent_inventory, recent_transfers
notifications:view
audit:lifecycle
auth:login
```

### Matrix

| Capability | Stock Manager template |
|------------|:----------------------:|
| Inventory full | ✅ |
| Sales | ❌ |
| Reports | ❌ |
| Backup | ❌ |
| User admin | ❌ |
| Tally | ❌ |
| Settings write | ❌ |

**Validation:** `STOCK_MANAGER_TEMPLATE` passes `validate_assignable_permissions()` (automated in M14F API).

---

## 3. Custom access roles

| Rule | Detail |
|------|--------|
| API | `GET/POST/PATCH /api/v1/access-roles` |
| Catalogue | `ASSIGNABLE_PERMISSIONS` (excludes user admin, settings:modify, tally:configure, workers) |
| Assignment | User `custom_access_role_id` overrides system role permissions |
| Normalization | `normalize_permission_set()` adds required `:view` dependencies |
| Denied in custom roles | `users:*`, `settings:modify`, `tally:configure`, `sync:worker`, `tally:worker` |

**UAT:** Create role with `reports:view` only → user sees reports, not inventory write.

---

## 4. Module → permission mapping

| Module | Permission prefix | Primary API |
|--------|-------------------|-------------|
| Inventory | `inventory:` | `/api/v1/inventory` |
| Sales | `sales:` | `/api/v1/sales` |
| Catalogue | `brands:`, `product_models:`, `locations:` | `/api/v1/brands`, etc. |
| Reports | `reports:` | `/api/v1/reports` |
| Notifications | `notifications:` | `/api/v1/notifications` |
| Audit | `audit:` | `/api/v1/audit_logs` |
| Backup | `backup:` | `/api/v1/settings/backups` |
| Restore | `restore:` | `/api/v1/settings/backups/restore` |
| Tally | `tally:` | `/api/v1/integrations/tally` |
| Dashboard | `dashboard:` | `/api/v1/dashboard` |
| Search | `inventory:view` (minimum) | `/api/v1/search` |

---

## 5. Dashboard widgets by role

| Widget | Main Admin | Admin | Salesperson |
|--------|:----------:|:-----:|:-----------:|
| Quick actions | ✅ | ✅ | ✅ |
| Inventory distribution | ✅ | ✅ | ✅ |
| Brand distribution | ✅ | ✅ | ❌ |
| Recent sales | ✅ | ✅ | ❌ |
| System status | ✅ | ✅ | ❌ |
| Tally status | ✅ | ✅ | ❌ |

Enforced by `user_has_dashboard_widget()` and desktop route guards.

---

## 6. Operations matrix (non-RBAC)

| Operation | Who | Validation |
|-----------|-----|------------|
| Auto update | All clients | Server `/client-updates/check` |
| Rollback | Main Admin + Deployment Center approval | `enterprise_rollback_engine` |
| Offline mode | Mobile clients | Flutter cache (no RBAC) |
| Global search | Users with `inventory:view` | API auth middleware |
| Excel sync | Admin settings | `excel_export_enabled` |

---

## 7. Automated validation

```http
GET /api/v1/deployment/production-acceptance
```

Response `role_matrix` array summarizes module access per profile.

```bash
pytest apps/backend/tests/auth/test_permissions.py
pytest apps/backend/tests/deployment/test_production_acceptance_validation.py
```

---

## 8. Production acceptance procedure

1. Create test users for each system role.
2. Create **Stock Manager** custom role from template §2.
3. Walk [USER_ACCEPTANCE_CHECKLIST.md](USER_ACCEPTANCE_CHECKLIST.md) sections B–G.
4. Record permission denials as **Pass** when expected per this matrix.
5. Sign [PRODUCTION_ACCEPTANCE_REPORT.md](PRODUCTION_ACCEPTANCE_REPORT.md).

---

## 9. References

| Document | Purpose |
|----------|---------|
| `core/permissions.py` | Canonical permission catalogue |
| `services/permission_resolver.py` | Effective permissions |
| `tests/auth/test_permissions.py` | Automated matrix tests |
| `tests/auth/test_custom_permissions.py` | Custom role normalization |
| ADR-0010 | Authentication strategy |
| ADR-0011 | Tally / mark-as-sold policy |
