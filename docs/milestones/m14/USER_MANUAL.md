---
Title: User Manual — WEBSTUDIO IMS
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14I
Audience: Showroom staff — sales, warehouse, floor
Related Documents:
  - docs/milestones/m14/QUICK_START_GUIDE.md
  - docs/milestones/m14/TRAINING_GUIDE.md
  - docs/milestones/m14/FAQ.md
  - docs/milestones/m14/ADMINISTRATOR_MANUAL.md
---

# User Manual (M14I)

Complete reference for daily use of **WEBSTUDIO IMS** on **desktop** (Windows/macOS) and **mobile** (Android/iOS). No technical configuration is required for most staff — ask your administrator for login credentials and permissions.

| Companion | Purpose |
|-----------|---------|
| [Quick Start Guide](QUICK_START_GUIDE.md) | First-day essentials (15 minutes) |
| [Training Guide](TRAINING_GUIDE.md) | Role-based training sessions |
| [FAQ](FAQ.md) | Common questions |

---

## 1. Login

### 1.1 Before you log in

1. Open **WEBSTUDIO Desktop** or the **WEBSTUDIO IMS** mobile app.
2. Wait for **Connected** / **Online** (toolbar or connection screen).
3. If disconnected, check Wi‑Fi and ask IT if the server is running.

### 1.2 Sign in

1. Enter **username** and **password** from your administrator.
2. Tap or click **Log in**.
3. On first login you may be asked to change your password.

### 1.3 Session and security

| Topic | Behaviour |
|-------|-----------|
| Idle timeout | Automatic logout after period set by admin (often 15 minutes) |
| Remember me | Optional if enabled by policy |
| Wrong password | After several failures, account locks temporarily |
| Shared PC | Log out when leaving the counter |
| Password | Never share; ask admin for reset |

### 1.4 What you see after login

Modules in the sidebar depend on your **role**. A salesperson sees Inventory and Sales; an administrator also sees Settings and Reports.

---

## 2. Dashboard

The **Dashboard** is your home screen after login.

### 2.1 Typical widgets

| Widget | Content |
|--------|---------|
| Inventory summary | Counts by status (available, sold, in transit) |
| Recent inventory | Latest items added or changed |
| Recent transfers | Stock moved between locations |
| Tally sync health | Last sync time (if you have access) |
| Notifications | Unread alerts |

### 2.2 Quick actions

- Use **Search** (see § 8) from the dashboard to find a serial instantly.
- Open **Inventory** or **Sales** from the sidebar.
- Tap a notification to jump to the related item (when applicable).

**Note:** System status and deployment tools appear only for administrators.

---

## 3. Search

Search is the fastest way to find a laptop.

### 3.1 Global search (desktop)

| Action | How |
|--------|-----|
| Open search | **Ctrl+K** (Windows) or **Cmd+K** (Mac) |
| Close | **Esc** |
| Search by | Serial number, brand, model, part number |

Results show matching inventory items. Click a result to open **item detail**.

### 3.2 Search in Inventory

Open **Inventory** and use the search box at the top of the list. Filters narrow by status, location, brand, or model.

### 3.3 Search on mobile

Use the search field on the Inventory screen, or scan a barcode (see § 9) to populate search.

### 3.4 Tips

- Serial numbers are case-insensitive.
- Partial model names work (e.g. `MacBook Pro 14`).
- If nothing is found, the item may not be **received** into inventory yet.

---

## 4. Inventory

Inventory tracks every laptop from **receive** to **sold**.

### 4.1 Item statuses

| Status | Meaning | Staff action |
|--------|---------|--------------|
| **Available** | Ready to sell | Normal sales flow |
| **Sold** | Already sold | Do not re-sell — verify invoice |
| **Reserved** | Held for customer | Check with manager |
| **In transit** | Moving between locations | Complete transfer at destination |

### 4.2 View item detail

1. Search or browse to the item.
2. Open detail to see: serial, brand, model, colour, location, specs, status, sale history.

Always verify the **physical serial** on the laptop matches the screen.

### 4.3 Add / receive inventory (if permitted)

1. **Inventory** → **Add laptop**.
2. Enter or scan **serial number**.
3. Select **brand**, **model**, **colour**, **location**.
4. Enter specs manually, or use **Fetch specs** if AI enrichment is enabled.
5. **Save**.

### 4.4 Transfer stock

Move a unit between store locations (e.g. warehouse → display floor):

1. Open item detail.
2. **Transfer** → choose destination location.
3. Confirm — status may show **In transit** until received at destination.

Salesperson and warehouse roles typically have transfer permission.

### 4.5 Mark as sold (administrators)

Most sales arrive from **Tally sync** automatically. Administrators can **mark as sold** manually:

1. Open available item.
2. **Mark as sold** — enter invoice number, customer, payment mode.
3. Save.

Salesperson role usually has **view only** for sales; Tally import handles sold status for billing.

### 4.6 Archive and restore (administrators)

Wrong entry or returned stock may be **archived** by administrators. Archived items are hidden from normal search unless filters include archived.

---

## 5. Sales

The **Sales** module shows completed sales linked to inventory.

### 5.1 Sales list

- Sort and filter by date, invoice number, salesperson.
- Open a sale to see: serial, model, invoice, customer, payment mode, sold date.

### 5.2 How sales get into the system

| Source | When |
|--------|------|
| **Tally import** | Automatic when Tally sync runs (primary path) |
| **Manual mark-as-sold** | Administrator action on inventory item |

### 5.3 Tally sync (what staff see)

If your role shows Tally on the dashboard or Settings:

| Field | Meaning |
|-------|---------|
| Last sync | When server last imported from Tally |
| Sync health | Healthy / Needs attention / Offline |
| Imported today | Sales added today from Tally |

**Notify your administrator** if sync stays Offline during business hours. You do not need to fix server configuration.

---

## 6. Catalogue

**Catalogue** maintains reference data used by inventory.

### 6.1 Sections

| Section | Contains |
|---------|----------|
| **Brands** | Manufacturer names (e.g. Apple, Dell) |
| **Product models** | Model names and default specs |
| **Locations** | Store areas (warehouse, ground floor, first floor) |

### 6.2 Who can edit

| Role | Typical access |
|------|----------------|
| Main Admin / Admin | Full create, edit, archive |
| Stock Manager (custom) | Brands, models, locations |
| Salesperson | View only (browse when adding items) |

### 6.3 Why catalogue matters

- Tally import matches invoice lines to **product models** by name.
- Missing models cause sync warnings — ask admin to add the model.
- Locations drive transfer and distribution reports.

---

## 7. Reports

**Reports** export business data for managers and accountants.

### 7.1 Available reports (role-dependent)

| Report type | Typical use |
|-------------|-------------|
| Inventory | Stock on hand by location, status, brand |
| Sales | Sales by date range, salesperson |
| Transfers | Movement between locations |
| Audit | Who changed what (administrators) |

### 7.2 Export

1. Open **Reports**.
2. Choose report type and date range.
3. Apply filters.
4. **Export** to CSV, XLSX, or PDF (formats depend on report).

Large exports may take a few seconds — wait for the download to complete.

---

## 8. Notifications

**Notifications** alert staff to events that need attention.

### 8.1 Common notification types

| Type | Meaning | Action |
|------|---------|--------|
| Tally — missing serial | Invoice line serial not in inventory | Receive item or notify admin |
| Tally — model mismatch | Line model differs from inventory | Verify with accounts |
| Duplicate sale | Voucher already imported | No action — expected dedup |
| Backup / system | Server alerts | Administrators only |
| Inventory lifecycle | Item archived, transferred | Informational |

### 8.2 Managing notifications

1. Open **Notifications** from the sidebar.
2. Read unread items.
3. Mark as **read** or **resolved** per store process.
4. Tap a notification to open related inventory or settings when linked.

---

## 9. Barcode

WEBSTUDIO IMS supports barcodes in two ways depending on platform.

### 9.1 Desktop — keyboard-wedge scanner

USB barcode scanners that act as a **keyboard** (HID wedge) work in any text field:

1. Click in the **serial number** field (Add laptop or search).
2. Scan the barcode — characters appear as typed input.
3. Press Enter or continue the form.

No special driver is required. The scanner sends keystrokes like typing.

### 9.2 Mobile — camera scanner

On Android and iOS:

1. Open **Inventory** → **Add laptop** or search.
2. Tap the **scan** icon.
3. Allow **camera** permission when prompted.
4. Point at barcode — supported formats include Code 128, Code 39, EAN, UPC, QR.
5. Scanned value fills serial or model field based on barcode content.

### 9.3 Scan preferences (mobile)

In scanner settings you can toggle **sound** and **haptic** feedback on scan.

### 9.4 Good practices

- Scan the **serial label** on the device, not the box only.
- If scan fails, type the serial manually.
- Damaged labels — type serial and report to admin for re-labelling.

---

## 10. Settings (staff view)

Most **Settings** sections are for administrators. Staff may see limited items.

| Section | Staff access |
|---------|--------------|
| General (company name) | View only |
| Security (own password) | Change own password if permitted |
| Tally status | View sync health (some roles) |
| Integrations / Backup / Users | Administrators only |

To change your password: **Settings → Security** or profile menu → **Change password** (if available).

Administrators: see [ADMINISTRATOR_MANUAL.md](ADMINISTRATOR_MANUAL.md).

---

## 11. Desktop client

**WEBSTUDIO Desktop** is the primary client for counter and back-office PCs.

### 11.1 Requirements

| | Windows | macOS |
|---|---------|-------|
| OS | Windows 10/11 | macOS 12+ |
| Network | Same LAN as server | Same LAN as server |
| RAM | 4 GB minimum | 4 GB minimum |

### 11.2 Connecting

| Method | Steps |
|--------|-------|
| Auto-discovery | Launch app → select server from list |
| Manual | Enter `http://<server-ip>:8000` → Test → Save |

Toolbar shows **Online** / **Offline**. App reconnects automatically (~15 seconds).

### 11.3 Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+K / Cmd+K | Global search |
| Esc | Close dialog or drawer |

### 11.4 Updates

When the server requires a newer client, the app prompts you to download the update from the **server** (not the internet). Install when IT or admin instructs.

**Reference:** [DESKTOP_DEPLOYMENT_GUIDE.md](DESKTOP_DEPLOYMENT_GUIDE.md)

---

## 12. Mobile client

**WEBSTUDIO IMS** mobile app for floor staff on Android and iOS.

### 12.1 Installation

- **Android:** Install APK from administrator (sideload).
- **iOS:** Install via TestFlight or enterprise distribution from administrator.

### 12.2 First launch

1. Connection screen — app searches LAN or asks for server URL.
2. Enter `http://<server-ip>:8000` if discovery fails.
3. Log in with staff credentials.

### 12.3 Mobile features

| Screen | Capability |
|--------|------------|
| Dashboard | Summary metrics |
| Inventory | Browse, search, detail, transfer (if permitted) |
| Sales | List and detail |
| Notifications | Alerts |
| Barcode | Camera scan |
| Settings | Connection, limited config |

### 12.4 Offline behaviour

- **Reads** may use limited cache.
- **Writes** (add, transfer, sell) require live server connection.
- App reconnects when returning to foreground on same Wi‑Fi.

### 12.5 Mandatory update

If server enforces a minimum mobile version, the app blocks until you install the new APK/build from admin.

**Reference:** [MOBILE_DEPLOYMENT_GUIDE.md](MOBILE_DEPLOYMENT_GUIDE.md)

---

## 13. Role summary

What you can do depends on your role. Ask admin if a button is missing.

| Task | Salesperson | Stock Manager | Admin |
|------|:-----------:|:-------------:|:-----:|
| Search / view inventory | ✅ | ✅ | ✅ |
| Transfer stock | ✅ | ✅ | ✅ |
| Add / receive inventory | ❌ | ✅ | ✅ |
| View sales | ✅ | ❌ | ✅ |
| Manual mark-as-sold | ❌ | ❌ | ✅ |
| Reports export | ❌ | ❌ | ✅ |
| Catalogue edit | View | ✅ | ✅ |
| Settings / backup | ❌ | ❌ | ✅ |

Full matrix: [ROLE_MATRIX_VALIDATION.md](ROLE_MATRIX_VALIDATION.md)

---

## 14. Good practices

- Verify **serial on device** matches system before handover to customer.
- Do not sell a unit showing **Sold** status.
- Log out on shared PCs.
- Report **Offline** sync or connection issues to admin promptly.
- Use **Search** instead of scrolling long lists.

---

## 15. Getting help

| Issue | Contact |
|-------|---------|
| Login / password | Administrator |
| Missing module | Administrator (role change) |
| Server offline | IT / administrator |
| Tally sync | Administrator / accounts |
| Training | Manager — [Training Guide](TRAINING_GUIDE.md) |
| Quick answers | [FAQ](FAQ.md) |
