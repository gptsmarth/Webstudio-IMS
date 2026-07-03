---
Title: Administrator Handover
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14J
---

# Administrator Handover (M14J)

Handover pack for **Main Admin** and delegated administrators.

---

## Your responsibilities

| Area | Action |
|------|--------|
| Users & roles | Create staff accounts; assign roles |
| Company profile | Settings → General |
| Tally | Settings → Tally — host, company, sync |
| Backups | Schedule + verify + off-site copies |
| AI keys | Settings → Integrations (optional) |
| Client updates | Deployment Center after WEBSTUDIO releases |
| UAT sign-off | [USER_ACCEPTANCE_CHECKLIST.md](USER_ACCEPTANCE_CHECKLIST.md) |

---

## Essential documents

| Document | Use |
|----------|-----|
| [ADMINISTRATOR_MANUAL.md](ADMINISTRATOR_MANUAL.md) | Setup reference |
| [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md) | Daily ops |
| [MAINTENANCE_GUIDE.md](MAINTENANCE_GUIDE.md) | Schedules |
| [ROLE_MATRIX_VALIDATION.md](ROLE_MATRIX_VALIDATION.md) | Permissions |
| [DISASTER_RECOVERY_GUIDE.md](DISASTER_RECOVERY_GUIDE.md) | Emergency |

---

## First-week checklist

| Day | Task |
|-----|------|
| 1 | Verify all staff log in; run handover validation API |
| 2 | Confirm Tally sync imports test invoice |
| 3 | Manual backup + verify checksum |
| 4 | Distribute mobile APK to floor staff |
| 5 | Complete UAT checklist sign-off |
| 7 | Go-live review — [GO_LIVE_REPORT.md](GO_LIVE_REPORT.md) |

---

## Credentials to secure

| Secret | Storage |
|--------|---------|
| Main Admin password | Password manager |
| Recovery key | Offline safe |
| JWT_SECRET | Server `.env` only |
| AI API keys | Settings → Integrations |
| Integration keys | Settings → Integration Keys |

---

## Training staff

| Audience | Guide |
|----------|-------|
| All staff | [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) |
| Sales | [TRAINING_GUIDE.md](TRAINING_GUIDE.md) Session 1 |
| Warehouse | Session 2 |
| FAQ | [FAQ.md](FAQ.md) |

---

## Acceptance

| Item | Accepted |
|------|:--------:|
| Administrator Manual reviewed | ☐ |
| Backup schedule configured | ☐ |
| Recovery key stored securely | ☐ |
| Staff training scheduled | ☐ |
| WEBSTUDIO engineer contact saved | ☐ |

**Main Admin signature:** _________________ **Date:** _________
