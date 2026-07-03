---
Title: Training Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14I
Audience: Trainers, managers, WEBSTUDIO implementers
Related Documents:
  - docs/milestones/m14/USER_MANUAL.md
  - docs/milestones/m14/QUICK_START_GUIDE.md
  - docs/milestones/m14/USER_ACCEPTANCE_CHECKLIST.md
---

# Training Guide (M14I)

Structured training plan for showroom staff. Each session includes objectives, duration, exercises, and pass criteria.

**Prerequisites:** Server commissioned (M14A–E), test accounts created, sample inventory loaded.

---

## Training overview

| Session | Audience | Duration | Focus |
|---------|----------|----------|-------|
| 1 | Sales staff | 60 min | Login, search, dashboard, sales view |
| 2 | Warehouse / stock | 90 min | Receive, transfer, barcode, catalogue |
| 3 | Supervisors / admins | 120 min | Reports, notifications, Tally visibility, roles |
| 4 | Mobile floor staff | 45 min | Mobile app, camera barcode, reconnect |
| Refresher | All staff | 30 min | Quick Start + FAQ review |

---

## Session 1 — Sales staff (60 minutes)

### Objectives

- Log in and interpret connection status
- Find any laptop by serial or model in under 10 seconds
- Read item status and location correctly
- View sales history
- Know when to escalate to admin

### Agenda

| Time | Topic | Activity |
|------|-------|----------|
| 0:00 | Welcome + [Quick Start](QUICK_START_GUIDE.md) | Demo login on desktop |
| 0:10 | Dashboard tour | Identify available vs sold counts |
| 0:20 | Global search | Each trainee: Ctrl+K → find 3 assigned serials |
| 0:35 | Item detail | Status, location, specs, sale link |
| 0:45 | Sales module | Find sale by invoice number |
| 0:50 | Notifications | Read Tally alert (demo) |
| 0:55 | Escalation | Offline sync, sold conflict — who to call |
| 1:00 | Q&A | [FAQ](FAQ.md) |

### Hands-on exercises

1. **Exercise A:** Trainer gives serial on a sticky note — trainee finds item and states status aloud.
2. **Exercise B:** Trainer shows **Sold** item — trainee explains why it cannot be re-sold.
3. **Exercise C:** Trainee uses search with partial model name (`Dell XPS`).

### Pass criteria

| # | Criterion |
|---|-----------|
| 1 | Logs in without assistance |
| 2 | Finds assigned serial via Ctrl+K in < 15 seconds |
| 3 | Correctly states Available vs Sold |
| 4 | Opens Sales list and finds one invoice |
| 5 | Names admin contact for Offline status |

Maps to UAT: SAL-01 through SAL-06 in [USER_ACCEPTANCE_CHECKLIST.md](USER_ACCEPTANCE_CHECKLIST.md).

---

## Session 2 — Warehouse / stock (90 minutes)

### Objectives

- Receive new inventory with correct catalogue data
- Transfer stock between locations
- Use barcode scanner (desktop wedge + mobile camera)
- Understand catalogue (brands, models, locations)

### Agenda

| Time | Topic | Activity |
|------|-------|----------|
| 0:00 | Review Session 1 search skills | 5-min recap |
| 0:10 | Catalogue tour | Brands → Models → Locations |
| 0:25 | Add laptop workflow | Demo full receive |
| 0:40 | Hands-on receive | Each trainee receives 1 test unit |
| 0:55 | Transfer workflow | Warehouse → display location |
| 1:05 | Barcode desktop | USB scanner into serial field |
| 1:15 | Barcode mobile | Camera scan on test device |
| 1:25 | AI fetch specs (optional) | Demo if enabled |
| 1:30 | Q&A | |

### Hands-on exercises

1. **Exercise D:** Receive unit with serial `TRAIN-001` — brand, model, Ground Floor location.
2. **Exercise E:** Transfer `TRAIN-001` to First Floor — verify **In transit** then **Available**.
3. **Exercise F:** Scan barcode on physical laptop (or sample label).

### Pass criteria

| # | Criterion |
|---|-----------|
| 1 | Creates inventory row with correct serial and location |
| 2 | Completes transfer without duplicate entry |
| 3 | Uses scanner OR types serial accurately |
| 4 | Explains when to add new model in catalogue (admin) |

Maps to UAT: STK-01 through STK-05.

---

## Session 3 — Supervisors / administrators (120 minutes)

### Objectives

- Navigate Settings (read-only vs write sections)
- Run and export a report
- Manage notifications workflow
- Explain Tally sync to floor staff
- Understand role boundaries (salesperson vs admin)

### Agenda

| Time | Topic | Activity |
|------|-------|----------|
| 0:00 | Role matrix overview | [ROLE_MATRIX_VALIDATION.md](ROLE_MATRIX_VALIDATION.md) |
| 0:15 | Settings workspace | General, Security, Tally (view) |
| 0:30 | Manual mark-as-sold | Demo on test unit |
| 0:45 | Reports | Inventory + Sales export CSV |
| 1:00 | Notifications | Resolve Tally missing-serial demo |
| 1:15 | Tally dashboard | Last sync, health, imported today |
| 1:30 | Desktop vs mobile admin | What mobile cannot do |
| 1:45 | User admin overview | Create user (Main Admin demo) |
| 2:00 | Q&A + [Administrator Manual](ADMINISTRATOR_MANUAL.md) pointer |

### Hands-on exercises

1. **Exercise G:** Export sales report for last 7 days.
2. **Exercise H:** Mark test unit sold with invoice `TRAIN-INV-01`.
3. **Exercise I:** Log in as salesperson on second PC — confirm backup menu hidden.

### Pass criteria

| # | Criterion |
|---|-----------|
| 1 | Exports one report successfully |
| 2 | Describes Tally vs manual sale paths |
| 3 | Resolves or assigns one notification |
| 4 | Knows difference Main Admin vs Admin |

Maps to UAT: ADM-01 through ADM-13.

---

## Session 4 — Mobile floor staff (45 minutes)

### Objectives

- Install and connect mobile app
- Search and view inventory on phone
- Use camera barcode scanner
- Handle reconnect after Wi‑Fi drop

### Agenda

| Time | Topic | Activity |
|------|-------|----------|
| 0:00 | Install APK / iOS build | Admin distributes |
| 0:10 | Server connection | Manual URL if discovery fails |
| 0:15 | Login + dashboard | |
| 0:25 | Inventory search + detail | |
| 0:32 | Camera barcode scan | |
| 0:38 | Offline / reconnect demo | Airplane mode toggle |
| 0:45 | Q&A | |

### Pass criteria

| # | Criterion |
|---|-----------|
| 1 | Connects and logs in on own device |
| 2 | Finds serial via search |
| 3 | Successful camera scan OR explains permission fix |
| 4 | App recovers after brief disconnect |

Maps to UAT: CLI-20 through CLI-22, SAL-07.

---

## Refresher session (30 minutes)

Use after upgrades or staff turnover.

1. [Quick Start Guide](QUICK_START_GUIDE.md) walkthrough (10 min)
2. Live search drill — 5 serials (10 min)
3. [FAQ](FAQ.md) top 10 questions (10 min)

---

## Training materials checklist

| Material | Location |
|----------|----------|
| User Manual | [USER_MANUAL.md](USER_MANUAL.md) |
| Quick Start | [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) |
| FAQ | [FAQ.md](FAQ.md) |
| Role matrix | [ROLE_MATRIX_VALIDATION.md](ROLE_MATRIX_VALIDATION.md) |
| UAT sign-off | [USER_ACCEPTANCE_CHECKLIST.md](USER_ACCEPTANCE_CHECKLIST.md) |
| Test serial labels | Print 10 barcodes for exercises |
| Test accounts | salesperson, stock_manager, admin |

---

## Sign-off template

| Trainee | Role | Session | Date | Trainer | Pass |
|---------|------|---------|------|---------|:----:|
| | | 1 / 2 / 3 / 4 | | | ☐ |

Store completed forms with UAT evidence for M14 handover.

---

## Trainer notes

- Never use production customer data in classroom exercises — use `TRAIN-*` serials.
- Delete or archive training inventory after session.
- If Tally sync is Offline during training, explain it is an admin/IT issue — proceed with manual search exercises.
- Desktop keyboard shortcut **Ctrl+K** is the highest-impact skill — drill it repeatedly.
