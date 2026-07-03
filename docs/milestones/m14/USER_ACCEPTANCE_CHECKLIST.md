---
Title: User Acceptance Checklist — Production
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14F
Related Documents:
  - docs/milestones/m14/PRODUCTION_ACCEPTANCE_REPORT.md
  - docs/milestones/m14/ROLE_MATRIX_VALIDATION.md
---

# User Acceptance Checklist (M14F)

Complete **user acceptance testing (UAT)** before production handover. Mark **Pass / Fail / N/A** and attach evidence.

**Environment:** Production server or staging mirror with production-like data volume.

---

## A. Prerequisites

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| PRE-01 | M14A–E complete | Server, network, backup, clients commissioned | Milestone reports |
| PRE-02 | Test accounts | Main Admin, Admin, Salesperson, Stock Manager role users | User list |
| PRE-03 | Sample data | Brands, models, ≥10 inventory units, 1 location | Screenshots |
| PRE-04 | API acceptance | `GET /deployment/production-acceptance` reviewed | JSON export |

---

## B. Administrator (Main Admin)

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| ADM-01 | Login | Main Admin authenticates on desktop | Screenshot |
| ADM-02 | Users | Create, edit, disable user | User admin |
| ADM-03 | Settings | Modify company, backup, security settings | Settings |
| ADM-04 | Access roles | Create custom access role | Role ID |
| ADM-05 | Deployment | Deployment Center visible (if releases deployed) | Screenshot |
| ADM-06 | Integration keys | AI keys configurable | Integrations |
| ADM-07 | Full navigation | All modules accessible | Menu capture |

---

## C. Administrator (Admin role)

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| ADM-08 | Login | Admin user authenticates | Screenshot |
| ADM-09 | Inventory admin | Create, archive, restore items | Workflow notes |
| ADM-10 | Backup | Manual backup + verify | Backup history |
| ADM-11 | Restore preview | Preview restore without executing (or drill on staging) | Preview JSON |
| ADM-12 | Reports export | Export report CSV/PDF | File |
| ADM-13 | No user admin | Cannot access user management | Blocked screen |

---

## D. Salesperson

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| SAL-01 | Login | Salesperson authenticates | Screenshot |
| SAL-02 | Search serial | Global search finds unit | Search result |
| SAL-03 | Transfer stock | Move unit between locations | Transfer log |
| SAL-04 | View sales | Sales list readable | Screenshot |
| SAL-05 | No backup | Backup settings not accessible | Permission denied |
| SAL-06 | No user admin | Users module hidden | Navigation |
| SAL-07 | Mobile (optional) | Same flows on Android/iOS | Device photo |

---

## E. Stock Manager (custom role)

Create custom role per [ROLE_MATRIX_VALIDATION.md](ROLE_MATRIX_VALIDATION.md) Stock Manager template.

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| STK-01 | Role assigned | User has custom Stock Manager role | User profile |
| STK-02 | Receive inventory | Create / receive units | Inventory row |
| STK-03 | Edit stock | Stock edit and transfer | Audit entry |
| STK-04 | Catalogue read | Brands/models/locations visible | Screenshot |
| STK-05 | No sales create | Cannot create manual sale (if excluded) | Blocked action |
| STK-06 | No settings write | Cannot modify system settings | Blocked |

---

## F. Custom roles

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| CUS-01 | Create role | Main Admin creates role with subset of permissions | Role name |
| CUS-02 | Assign user | User effective permissions match role | `/auth/me` |
| CUS-03 | Denied permissions | User cannot access modules outside role | Navigation test |
| CUS-04 | Normalize | View permissions auto-included with writes | API or UI |

---

## G. Functional modules

| ID | Module | Test | Pass criteria |
|----|--------|------|---------------|
| FUN-01 | Inventory | Full lifecycle | received → available → sold |
| FUN-02 | Sales | Tally import or manual mark sold | Status SOLD; audit logged |
| FUN-03 | Catalogue | Brand + model CRUD | Saved in DB |
| FUN-04 | Reports | Run inventory/sales report | Data matches DB |
| FUN-05 | Notifications | Trigger + resolve notification | In-app alert |
| FUN-06 | Audit | Search audit by entity | Entry found |
| FUN-07 | Backup | Manual backup completes | Verified archive |
| FUN-08 | Restore | Staging restore drill | Post-verify OK |
| FUN-09 | AI | Enrich product model (if enabled) | Suggestion applied |
| FUN-10 | Tally | Sync imports voucher | Inventory updated |
| FUN-11 | Global Search | Serial + model search | Correct hits |
| FUN-12 | Offline | Mobile offline banner + cache | Airplane mode test |
| FUN-13 | Sync | Tally scheduler + Excel export | History row |
| FUN-14 | Auto update | Client version check | Server response only |
| FUN-15 | Rollback | Document Deployment Center rollback | Procedure reviewed |

---

## H. Cross-platform

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| XPL-01 | Desktop Windows | Core UAT on EXE client | Checklist refs |
| XPL-02 | Desktop macOS | Core UAT on DMG client (if used) | Checklist refs |
| XPL-03 | Android | Core UAT on APK | CLI checklist |
| XPL-04 | iOS | Core UAT on pilot device | CLI checklist |

---

## I. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Store owner / manager | | | |
| Main Administrator | | | |
| WEBSTUDIO engineer | | | |

**Overall UAT:** ☐ **Accepted** for production handover &nbsp; ☐ **Rejected** — defect list attached

---

## J. Defect log (if rejected)

| ID | Module | Description | Severity | Owner |
|----|--------|-------------|----------|-------|
| | | | | |
