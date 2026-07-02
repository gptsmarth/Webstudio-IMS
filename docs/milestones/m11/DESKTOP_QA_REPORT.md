---
Title: Milestone 11 — Desktop QA Report
Version: 1.0.0
Status: Complete
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related Documents: docs/milestones/m11/KNOWN_ISSUES_REPORT.md
---

# Desktop QA Report

Validation of the Electron desktop application (`apps/desktop`). **No UI redesign performed.**

## Screen inventory

### Pre-workspace

| View | Component | Validated |
|------|-----------|-----------|
| Boot splash | `SplashScreen` | Code review |
| Connection | `ConnectionPage` | Code + setup tests |
| Setup wizard | `SetupWizardPage` | Code + setupGuard tests |
| Login | `LoginPage` | Code review |

### Workspace routes (10)

| Route | Page | Permission | Status |
|-------|------|------------|--------|
| `dashboard` | `DashboardPage` | `dashboard:view` | ✅ |
| `stock` | `StockPage` | `inventory:view` | ✅ |
| `inventory` | `InventoryPage` | `inventory:create` | ✅ |
| `sales` | `SalesPage` | `sales:view` | ✅ |
| `catalogue` | `CataloguePage` | `brands:view` | ✅ |
| `notifications` | `NotificationsPage` | `notifications:view` | ✅ |
| `reports` | `ReportsPage` | `reports:view` | ✅ |
| `users` | `UsersPage` | `users:view` | ✅ |
| `audit` | `AuditPage` | `audit:view` | ⚠️ Export permission gap |
| `settings` | `SettingsPage` | `settings:view` | ⚠️ Typecheck error |

## Dialog & workflow checklist

| Workflow | Status | Notes |
|----------|--------|-------|
| Add laptop wizard | ✅ | `AddLaptopWizard` |
| Add inventory batch | ✅ | `AddInventoryDialog` |
| Transfer location | ✅ | Stock + drawer |
| Mark sold | ✅ | `MarkSoldDialog` |
| Edit price / model | ✅ | Permission-gated |
| Sales detail + export | ✅ | Export requires `sales:export` |
| Catalogue CRUD | ✅ | Brands, locations |
| Reports preview → export | ✅ | Preview-first enforced |
| Users CRUD + custom roles | ✅ | Full admin center |
| Backup / restore / recovery | ✅ | Settings panels |
| Tally config + sync | ⚠️ | Via Settings; RBAC mismatch |
| Global search (Cmd/Ctrl+K) | ⚠️ | Silent failure on error |
| Audit export | ⚠️ | Missing `audit:export` gate |

## Electron security

| Control | Value | Status |
|---------|-------|--------|
| `contextIsolation` | `true` | ✅ |
| `nodeIntegration` | `false` | ✅ |
| `sandbox` | `true` | ✅ |
| `webSecurity` | `true` | ✅ |
| Preload | `contextBridge` only | ✅ |

File: `apps/desktop/electron/main.ts`

## API integration

- **Central client:** `RetryingApiClient` — retry, 401 refresh, setup guard
- **Gap:** `ReportService` export and `AuthenticationService` security export use raw `fetch` (DESK-002)
- **Gap:** `TallyService` / `GlobalSearchService` soft-fail without UI error (DESK-005, DESK-006)

## Automated tests

| Metric | Result |
|--------|--------|
| Test files | 18 |
| Tests passed | 87 / 90 |
| Failed | 3 (navigation, stockModelCard, users — stale expectations) |

**Coverage gap:** No desktop E2E (login → inventory → backup). Milestone 11 relied on unit tests + manual checklist.

## Manual smoke checklist (recommended before M12)

- [ ] All 10 routes × main_admin, admin, salesperson
- [ ] Inventory receive → transfer → mark sold
- [ ] Report preview → Excel/PDF export after token age > 15 min
- [ ] Backup create → download → validate → restore preview on staging
- [ ] Audit export with view-only permission (expect block)
- [ ] Dark/light mode toggle in settings
- [ ] Global search with backend offline (expect error, not empty)

## Issues

| ID | Severity | Fixed | Deferred |
|----|----------|-------|----------|
| DESK-001 | High | No | — |
| DESK-002 | High | No | — |
| DESK-003 | High | No | — |
| DESK-004–010 | Medium/Low | — | Yes |

See [KNOWN_ISSUES_REPORT.md](./KNOWN_ISSUES_REPORT.md).
