---
Title: Employee Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
Audience: Sales staff, warehouse, floor employees
---

# Employee Guide

Daily use of WEBSTUDIO IMS for showroom staff. **No technical configuration required.**

---

## 1. Getting started

### Desktop (Windows / Mac)

1. Open **WEBSTUDIO Desktop** from Start Menu or Applications.
2. If disconnected, wait for **Connected** (auto-reconnects after server restart).
3. Log in with your username and password.

### Mobile (Android / iPhone)

1. Install **WEBSTUDIO IMS** APK (Android) or approved iOS build.
2. On first launch, select or enter server address (ask admin).
3. Log in.

---

## 2. Dashboard

After login you see:

- Inventory summary (available, sold, in transit)
- Recent activity
- Notifications (if your role allows)

Use the sidebar to open **Inventory**, **Sales**, **Catalogue**, or **Reports**.

---

## 3. Finding a laptop

1. Open **Inventory** or use **Search** (Ctrl+K on desktop).
2. Search by **serial number**, model, or brand.
3. Open item detail to see location, specs, and status.

| Status | Meaning |
|--------|---------|
| Available | Ready to sell |
| Sold | Already sold — do not re-sell |
| Reserved | Held for customer |
| In transit | Moving between locations |

---

## 4. Adding inventory

1. **Inventory** → **Add laptop** (if permitted).
2. Scan or enter serial number.
3. Select brand, model, colour, location.
4. Save — label/QR generated if enabled.

**AI assist:** If enabled, entering a model name may auto-fill specs from the web (admin configures API key).

---

## 5. Recording a sale

Sales from Tally import **automatically** when Tally sync runs. For manual sales:

1. Find the serial in Inventory.
2. **Mark as sold** (or Sales workspace).
3. Enter invoice number, customer, payment mode.

---

## 6. Tally sync (what you see)

If you have access to **Settings → Tally** or dashboard widgets:

| Field | Meaning |
|-------|---------|
| Last Sync | When server last imported from Tally |
| Last Invoice | Last printed invoice number imported |
| Imported Today | Sales added today from Tally |
| Sync Health | Healthy / Needs attention / Offline |

**You do not need to fix sync** — notify admin if Health stays Offline during business hours.

---

## 7. Notifications

Open **Notifications** for:

- Duplicate sale warnings
- Missing serial on Tally invoice
- Model mismatch (informational)
- Backup or system alerts (admins)

Mark as read or resolved per your process.

---

## 8. When something goes wrong

| Problem | What to do |
|---------|------------|
| Cannot log in | Check caps lock; ask admin to reset password |
| Disconnected | Wait 30s; check Wi‑Fi; ask admin if server is on |
| Serial not found | Verify serial; item may not be received yet |
| Sale already sold | Check Tally invoice — possible duplicate import |

See [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md) or call admin.

---

## 9. Good practices

- Always verify **serial number** on the physical laptop matches the system.
- Do not share your password.
- Log out on shared PCs when leaving the counter.
- Report damaged labels or wrong locations to admin.
