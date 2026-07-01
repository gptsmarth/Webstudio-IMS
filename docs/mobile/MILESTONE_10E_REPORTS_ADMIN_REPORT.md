---
Title: Milestone 10E — Reports & Administration
Version: 0.1.0
Status: Ready for Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/mobile/MILESTONE_10D_SALES_CATALOGUE_REPORT.md
---

# Milestone 10E — Reports & Administration

## Summary

Milestone 10E delivers mobile Reports and Administration surfaces that consume the same backend APIs as desktop — no duplicated business logic. Reports support inventory, sales, audit, and tally (notification) previews with server pagination. Administration covers notifications, users, settings status, backup/recovery, tally status, and AI provider health.

---

## Deliverables

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Reports — Inventory | ✅ | `ReportType.inventory` → `GET /api/v1/reports/inventory` |
| Reports — Sales | ✅ | `ReportType.sales` → `GET /api/v1/reports/sales` |
| Reports — Audit | ✅ | `ReportType.audit` → `GET /api/v1/reports/audit` |
| Reports — Tally | ✅ | `ReportType.tally` → `GET /api/v1/reports/notifications?notification_category=tally_sync` |
| Notifications | ✅ | List, search, severity filter, mark read, archive |
| Users | ✅ | Paginated list, search, detail sheet |
| Settings | ✅ | API server, theme, administration status summary |
| Backup status | ✅ | `BackupScreen` + settings workspace `backup` |
| Recovery status | ✅ | `GET /api/v1/settings/recovery/center` |
| Tally status | ✅ | `TallyScreen` — status + dashboard sync log |
| AI provider status | ✅ | From `GET /api/v1/settings` → `integrations.ai_provider_health` |
| Tests | ✅ | `admin_models_test.dart` (18 total app tests) |

---

## Reports

Mirrors desktop Report Center preview workflow:

1. Select report type (Inventory / Sales / Audit / Tally)
2. Enter search term (optional)
3. Tap **Preview** → server fetch with pagination (50/page)
4. Paginate results

Uses the same preview endpoints as desktop `ReportService.preview()`. Export (`GET /api/v1/reports/export`) is deferred to a future milestone (mobile file download UX).

**Permissions:** `reports:view` (backend enforced)

---

## Notifications

- `GET /api/v1/notifications?is_resolved=false`
- Client-side search and severity filters (desktop parity)
- `PATCH /api/v1/notifications/{id}/read`
- `PATCH /api/v1/notifications/{id}/resolve`

**Permissions:** `notifications:view`, `notifications:manage` for actions

---

## Users administration

- `GET /api/v1/users` — paginated list (25/page), search
- `GET /api/v1/users/{id}` — detail sheet with permissions, sessions, login events

**Permissions:** `users:view` (backend enforced)

---

## Settings & status panels

**Settings screen** (`GET /api/v1/settings`):
- Company name and app version
- Backup status summary → navigates to Backup screen
- Recovery status summary → navigates to Backup screen
- Tally status summary → navigates to Tally screen
- AI provider status (Gemini health from `integrations.ai_provider_health`)

**Backup screen:**
- Backup settings from workspace (`backup.health_status`, schedule, folder)
- Recovery center (`GET /api/v1/settings/recovery/center`)
- Backup admin dashboard (`GET /api/v1/settings/backups/admin/dashboard`)

**Tally screen:**
- Status summary (`GET /api/v1/integrations/tally/status`)
- Connection details from settings workspace
- Recent synchronizations from `GET /api/v1/integrations/tally/dashboard`

---

## File map

```
lib/features/reports/
  domain/report_models.dart
  data/report_repository.dart
  presentation/reports_controller.dart
  presentation/reports_screen.dart

lib/features/notifications/
  domain/notification_models.dart
  data/notification_repository.dart
  presentation/notifications_controller.dart
  presentation/notifications_screen.dart

lib/features/users/
  domain/user_models.dart
  data/user_repository.dart
  presentation/users_controller.dart
  presentation/users_screen.dart

lib/features/settings/
  domain/settings_models.dart
  data/settings_repository.dart
  presentation/settings_screen.dart

lib/features/backup/presentation/backup_screen.dart
lib/features/tally/presentation/tally_screen.dart

test/features/admin/admin_models_test.dart
```

---

## Verification

```bash
cd apps/mobile_flutter
bash scripts/lint_and_test.sh
# flutter analyze — clean
# flutter test — 18/18 passing
```

**Manual smoke test checklist:**

1. More → Reports → preview each report type
2. More → Notifications → search, mark read, archive
3. More → Users → search, open user detail
4. More → Settings → verify status tiles load
5. More → Backup → backup + recovery + dashboard cards
6. More → Tally → status and recent sync list

---

## Known gaps (future milestones)

| Item | Notes |
|------|-------|
| Report export (XLSX/PDF) | Desktop `reports:export` — needs mobile download/share |
| Full settings edit panels | Mobile shows read-only status; desktop has full PATCH forms |
| User create/edit/actions | Mobile is view-only for users |
| Backup restore wizard | Desktop multi-step restore flow |
| Tally sync trigger/retry | Desktop action buttons |
| Security dashboard | Desktop `GET /api/v1/security/dashboard` |

---

## Desktop impact

**None.** Mobile consumes existing `/api/v1/*` endpoints only. No duplicated server logic.
