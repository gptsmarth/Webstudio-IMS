---
Title: Operations Handover
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14J
---

# Operations Handover (M14J)

Transferred to **store IT and Main Admin** for ongoing production operations.

---

## Daily operations

| Task | Owner | Reference |
|------|-------|-----------|
| Server powered on | IT | [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md) |
| Tally PC running | Accounts | [TALLY_PRODUCTION_GUIDE.md](TALLY_PRODUCTION_GUIDE.md) |
| Backup verified | Admin | Settings → Backup |
| Sync health check | Admin | Dashboard |

---

## Weekly operations

| Task | Reference |
|------|-----------|
| Off-site backup copy | [BACKUP_MANUAL.md](BACKUP_MANUAL.md) |
| Disk space check | [MAINTENANCE_GUIDE.md](MAINTENANCE_GUIDE.md) |
| Network validation (if issues) | `validate-production-network.ps1` |

---

## Change management

| Change type | Procedure |
|-------------|-----------|
| Server upgrade | [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md) § Updates |
| Client upgrade | Deployment Center or installer |
| Rollback | Deployment Center → Rollback |
| Restore drill | [RESTORE_CHECKLIST.md](RESTORE_CHECKLIST.md) |

---

## Validation scripts

Location: `D:\WEBSTUDIO-IMS\infra\windows\`

| Script | Purpose |
|--------|---------|
| `validate-production-handover.ps1` | M14J final certification |
| `validate-production-certification.ps1` | M14G security/performance |
| `validate-production-network.ps1` | M14B networking |
| `validate-production-backup.ps1` | M14D backup |
| `validate-production-tally.ps1` | M14C Tally |
| `configure-firewall.ps1` | Firewall rules |

---

## Escalation

| Severity | Contact | SLA |
|----------|---------|-----|
| P1 — system down | WEBSTUDIO engineer + IT | Immediate |
| P2 — Tally sync failed | Admin + accounts | Same business day |
| P3 — single client offline | IT | Next business day |

---

## Handover acceptance

| Item | Delivered |
|------|-----------|
| Operations Manual | ✅ |
| Maintenance Guide | ✅ |
| Backup/DR guides | ✅ |
| Validation scripts | ✅ |
| Training completed | Operator sign-off |
