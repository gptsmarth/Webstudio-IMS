# Milestone 7 — User Management & Role Administration

## Summary

Milestone 7 delivers a Main Administrator workspace for managing human user accounts: searchable/sortable user table, detail drawer, create/edit dialogs, password reset workflow, role changes, enable/disable actions, and a read-only permission viewer backed by backend role definitions.

## Delivered

### 1. Backend extensions
- `UserSummary.created_at` exposed for list/table sorting
- `UserDetail.permissions` populated from `permissions_for_role()`
- `GET /api/v1/users/role-permissions` — human roles only (`main_admin`, `admin`, `salesperson`)
- List filters: `created_from`, `created_to`, `sort_field`, `sort_direction`
- Safety: `SelfMainAdminDisableError` when a Main Admin attempts to disable their own account

### 2. Desktop User Administration module
- `UsersPage` — replaces placeholder; gated by `users:manage` permission from session
- `useUsersWorkspace` — paginated list, filters, drawer detail, audit feed, mutations
- `UserService` — full API client for all user management endpoints
- Components under `components/users/`:
  - `UsersTable`, `UsersToolbar`, `UsersFiltersPanel`
  - `UserDetailDrawer` — basic info, role, permissions, login/activity, audit events
  - `UserFormDialog` — create + edit
  - `ResetPasswordDialog` — generate temp password, strength meter, confirmation
  - `ChangeRoleDialog` — role picker + live permission preview
  - `ConfirmUserActionDialog` — disable/enable confirmation
  - `PermissionViewer` — read-only effective permissions per role
  - `UserRowActionsMenu` — row actions with safety tooltips

### 3. Auth session
- `AuthSession` stores `id` and `permissions[]` from `/auth/me` after login
- `canManageUsers()` checks `users:manage` — no hardcoded role checks in the module

### 4. Safety rules (UI + API)
- No delete action — disable only
- Cannot disable logged-in Main Administrator (self)
- Cannot disable or demote the last active Main Administrator
- Archive action reserved (future-ready columns for email / location)

### 5. Tests
- `apps/desktop/tests/users.test.ts` — permissions gate, safety helpers, password strength, permission grouping
- `apps/backend/tests/auth/test_user_management.py` — role-permissions endpoint, self-disable guard

## Verification

```bash
# Desktop
cd apps/desktop && npm run typecheck && npm run lint && npm run test && npm run build

# Backend
cd apps/backend && pytest tests/auth/test_user_management.py -q
```

## Stop for review

Milestone 7 is implementation-complete pending your review of the Users workspace in the desktop app (Main Admin login required).
