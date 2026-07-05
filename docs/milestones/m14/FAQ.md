---
Title: Frequently Asked Questions — WEBSTUDIO IMS
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14I
Audience: All showroom staff
Related Documents:
  - docs/milestones/m14/USER_MANUAL.md
  - docs/milestones/m14/QUICK_START_GUIDE.md
---

# Frequently Asked Questions (M14I)

Quick answers for showroom staff. For step-by-step instructions see the [User Manual](USER_MANUAL.md).

---

## Login

### I forgot my password. What do I do?

Ask your **administrator** to reset your password. You cannot reset it yourself unless recovery options were configured for Main Admin.

### Why was my account locked?

Too many failed login attempts. Wait for the lockout period (usually 15 minutes) or ask admin to unlock.

### Why did I get logged out automatically?

**Idle timeout** — the system logs you out after inactivity for security. Log in again.

### The app says "System not initialized." What does that mean?

First-time server setup is incomplete. Only **Main Admin** can finish the Setup Wizard — contact them or IT.

---

## Connection (Desktop & Mobile)

### The toolbar says Offline. What should I do?

1. Wait 30 seconds (auto-reconnect).
2. Check you are on **store Wi‑Fi** (same network as server).
3. Ask IT if the **server PC** is powered on.

### The server does not appear in the discovery list.

Enter the server manually: `http://<server-ip>:8000`. Get the IP from your administrator.

### It works on one PC but not another.

Clear the saved server URL and rediscover, or re-enter the correct IP. The broken PC may be on a different Wi‑Fi SSID without routing to the server.

### Does the app work without internet?

**Yes, on the local network** — WEBSTUDIO runs on your store LAN. You do not need public internet for inventory and sales. **AI enrichment** and some updates may need internet on the server.

### Can the server be on the ground floor and Tally on the first floor?

**Yes.** Desktop, mobile, and Tally sync only need the **same shop network** (`192.168.29.x`), not the same floor. The server connects to the Tally laptop by name (`TALLY-LAPTOP`), not by floor. Staff still use **`http://192.168.29.100:8000`** everywhere. If Tally sync fails, ask IT to check both devices are on **JioBharat** or **Asus Store** (not guest Wi‑Fi) and run **Settings → Tally → Test connection**.

---

## Search

### I searched a serial but found nothing.

- Check for typos (O vs 0, I vs 1).
- The laptop may not be **received** into inventory yet — ask warehouse.
- Item may be **archived** — admin can check.

### How do I search quickly on desktop?

Press **Ctrl+K** (Mac: **Cmd+K**), type serial or model, press Enter.

### Can I search by customer name?

Global search focuses on **inventory** (serial, brand, model). Customer names appear in **Sales** detail after a sale exists.

---

## Inventory

### What does each status mean?

| Status | Meaning |
|--------|---------|
| Available | Ready to sell |
| Sold | Already sold |
| Reserved | Held for a customer |
| In transit | Moving between locations |

### I found a laptop but it says Sold. Can we sell it again?

**No.** Verify with **Sales** and accounts — it may already be invoiced in Tally. Selling again causes duplicate issues.

### How do I add a new laptop?

Only staff with **receive/create** permission: **Inventory → Add laptop**. Salesperson role typically cannot add — ask warehouse or admin.

### How do I move stock to another floor?

Open item → **Transfer** → select new location. You need **transfer** permission (salesperson and stock roles usually have this).

### The serial on the laptop does not match the box.

**Trust the label on the device.** Enter the device serial. Report mismatched box labels to admin.

---

## Sales

### How do sales get into the system?

Most sales come from **Tally** automatically when accounts print invoices. Administrators can **mark as sold** manually in special cases.

### I sold a laptop in Tally but it still shows Available in IMS.

1. Check **Tally sync health** on dashboard (ask admin if Offline).
2. Sync may run every few minutes — wait and refresh.
3. Serial on Tally invoice must **match** inventory exactly.
4. Notify admin if still wrong after 30 minutes.

### Can salesperson mark items as sold?

Usually **no** — salesperson role is view-only for sales creation. Billing in Tally drives sold status.

---

## Catalogue

### What is Catalogue for?

**Brands**, **product models**, and **store locations** used when adding inventory. Tally import matches invoice lines to model names.

### I need a new model that is not in the list.

Ask **admin** or stock manager to add the model in **Catalogue → Product models** before receiving stock.

---

## Reports

### I cannot see Reports in the menu.

Your role may not include report permission. Ask admin if you need access.

### Export is slow or spinning.

Large date ranges take longer. Narrow the dates or ask admin to run during quiet hours.

---

## Notifications

### What is a "missing serial" notification?

Tally imported an invoice line with a serial **not in inventory**. Warehouse should receive the unit or admin investigates.

### What is a "model mismatch" notification?

Invoice model name differs from inventory model — verify with accounts. Often informational.

### Should I clear notifications?

Yes — mark as **read** or **resolved** after action or when admin confirms no action needed.

---

## Barcode

### My USB scanner does nothing.

1. Click inside the **serial number** field first.
2. Scanner must be in **keyboard wedge** mode (acts like typing).
3. Try Notepad — if characters appear there, scanner works; retry in WEBSTUDIO.

### Mobile camera scan does not open.

Allow **camera permission** in phone Settings → WEBSTUDIO IMS.

### Which barcodes work on mobile?

Code 128, Code 39, EAN, UPC, QR and common retail formats. Very damaged labels may need manual entry.

### Desktop vs mobile scanning?

- **Desktop:** USB keyboard-wedge scanner.
- **Mobile:** Built-in **camera** scanner.

---

## Dashboard

### Numbers on dashboard look wrong.

Dashboard refreshes from server data. If suspicious, run a search or ask admin to verify sync and backups.

### I do not see Tally on my dashboard.

Your role may hide Tally widgets. Ask admin — sync health is still their responsibility.

---

## Settings

### What can I change in Settings?

Most staff: **own password** only. Backup, users, Tally config, and integrations are **administrator** areas.

### Where do I change my password?

**Settings → Security** or profile menu, if your role allows.

---

## Desktop

### How do I update the desktop app?

When prompted, download from the **server** — not from a web browser search. IT or admin distributes updates.

### Keyboard shortcut cheat sheet?

| Key | Action |
|-----|--------|
| Ctrl+K / Cmd+K | Search |
| Esc | Close popup |

---

## Mobile

### Do I need the mobile app?

Optional — floor staff use it for quick lookup and camera scan. Counter staff often use desktop only.

### App says I need a newer version.

Install the APK or iOS build from your **administrator** — server requires a minimum client version.

### Does mobile work offline?

Limited. You can browse some cached data, but **adding or transferring stock requires connection**. Reconnect on store Wi‑Fi.

---

## Roles & permissions

### I cannot see a button my colleague has.

You have a different **role**. Ask admin to review permissions — see [ROLE_MATRIX_VALIDATION.md](ROLE_MATRIX_VALIDATION.md).

### What is Stock Manager?

A **custom role** for warehouse staff — receive, transfer, catalogue edit, no sales admin.

---

## Who to contact

| Issue | Contact |
|-------|---------|
| Password, roles | Administrator |
| Server offline, Wi‑Fi | IT |
| Tally sync, invoices | Administrator / Accounts |
| Training | Manager |
| Hardware scanner | IT |

---

## Still stuck?

1. [Quick Start Guide](QUICK_START_GUIDE.md)
2. [User Manual](USER_MANUAL.md) — full module reference
3. [Training Guide](TRAINING_GUIDE.md) — ask manager for refresher session
4. Administrator: [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md) § Troubleshooting
