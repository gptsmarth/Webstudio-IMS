---
Title: Milestone 10J — Desktop Feature Parity
Version: 0.1.0
Status: Ready for Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/mobile/MILESTONE_10I_DESKTOP_FEATURE_PARITY_REPORT.md
---

# Desktop Feature Parity Report — Milestone 10J

Module-by-module comparison after Milestone 10J. Legend: ✅ Parity | ⚠️ Partial | ❌ Intentionally excluded

---

## 1. Catalogue

| Desktop feature | Mobile | Notes |
|-----------------|--------|-------|
| Brands create/edit/archive/restore | ✅ | Bottom-sheet forms + popup actions |
| Product models full CRUD | ✅ | Create/edit sheet with specs, prices, notes, status |
| Selling / cost price | ✅ | Fields in model form + `updateSellingPrice` API |
| Specifications | ✅ | Display + AI spec fetch in form |
| AI refresh specs | ✅ | Trigger from model form |
| AI product image refresh | ✅ | Catalogue menu + image sheet |
| Warranty / notes | ✅ | Editable in model form when permitted |
| Archive / restore model | ✅ | Popup menu actions |
| Locations CRUD + capacity | ✅ | Edit sheet includes capacity + outlet |
| Location archive/restore | ✅ | Permission-gated |

---

## 2. Sales

| Desktop feature | Mobile | Notes |
|-----------------|--------|-------|
| Sales list + filters | ✅ | Enhanced filter sheet from 10D |
| Sale detail | ✅ | Invoice, customer, payment, device info |
| Sales timeline | ✅ | Created / sold dates |
| Audit timeline | ✅ | `auditRepository.listForInventoryItem` |
| PDF export | ✅ | Sales toolbar → Reports export API |
| Excel export | ✅ | Same path, `format=xlsx` |
| Share / download report | ✅ | `FileTransferService` bottom sheet |
| Sales history | ✅ | Via list + detail |
| Search | ✅ | Toolbar search + global search orchestrator |

---

## 3. Settings

| Desktop feature | Mobile | Notes |
|-----------------|--------|-------|
| Company name | ✅ | Write panel `PATCH settings/general` |
| Branding read | ✅ | Settings screen |
| Theme | ✅ | App theme mode (device) |
| Notifications read | ✅ | Notifications module |
| Server connection | ✅ | Connection screen + persisted URL |
| Version / About | ✅ | Settings screen |
| AI provider config | ⚠️ | AI enrichment toggle; provider keys backend-only |
| Integration API keys | ⚠️ | **Read-only list** on mobile (security policy) |
| Security settings | ⚠️ | Read display; granular security PATCH deferred |
| Tally host/port | ✅ | Write panel |
| Restore database | ❌ | Desktop-only |
| Disaster recovery | ❌ | Desktop-only |
| Server installation | ❌ | Desktop-only |

---

## 4. Product images

| Feature | Mobile |
|---------|--------|
| Camera | ✅ |
| Gallery | ✅ |
| AI fetch / retry | ✅ |
| Replace (upload) | ✅ |
| Delete image | ✅ | `PATCH product_image_url: null` |
| Fullscreen / zoom | ✅ | `InteractiveViewer` |
| Loading placeholder | ✅ |
| Error + retry | ✅ |
| Multi-image architecture | ⚠️ | Single URL today; sheet API future-proofed |

---

## 5. Barcode

| Feature | Mobile |
|---------|--------|
| Manufacturer symbologies only | ✅ |
| Internal QR | ❌ | **Intentionally excluded** |
| Model / serial / part auto-detect | ✅ | `BarcodeFieldResolver` |
| Continuous scan | ✅ |
| Duplicate highlight | ✅ | Snackbar + heavy haptic |
| Scan history strip | ✅ |
| Flashlight / camera switch | ✅ |
| Pause / resume | ✅ |
| Sound toggle | ✅ | `BarcodeScanPreferences` |
| Haptic toggle | ✅ | Persisted in SharedPreferences |
| Existing inventory detection | ⚠️ | Serial duplicate on create; scan navigates to item |

---

## 6. Global search

| Source | Mobile |
|--------|--------|
| Inventory / brands / models / locations | ✅ | `GET /api/v1/search` |
| Sales | ✅ | Orchestrator + `sales:view` |
| Audit logs | ✅ | Orchestrator + `audit:view` |
| Notifications | ✅ | Orchestrator + `notifications:view` |
| Users | ✅ | Orchestrator + `users:view` |
| Reports | ⚠️ | Navigate to Reports module |
| Tally | ⚠️ | Navigate to Tally screen |
| Customers / invoices (distinct) | ⚠️ | **Backend limitation** — sales search covers invoices |
| Serial / model / part / barcode | ✅ | Unified search + inventory hierarchy |

---

## 7. Executive dashboard

| Widget | Mobile |
|--------|--------|
| Available inventory | ✅ |
| Sold stock (aggregate) | ✅ |
| Top brands distribution | ✅ |
| Recent activity | ✅ |
| Tally status | ✅ |
| Notifications summary | ✅ |
| Today's sales / revenue | ⚠️ | Requires dedicated dashboard API; snapshot KPIs used |
| AI provider status | ⚠️ | Available via Settings test endpoint |
| Server / backup status | ⚠️ | Read-only fragments in Settings |
| Sales trend chart | ⚠️ | Distribution bars; no time-series chart widget |

---

## 8. Inventory Add Laptop wizard

| Step | Mobile |
|------|--------|
| Choose model | ✅ |
| AI specification fetch | ✅ |
| AI product image fetch | ✅ |
| Review specifications | ✅ |
| Model barcode scan | ✅ |
| Serial barcode scan | ✅ |
| Duplicate validation | ✅ |
| Review summary | ✅ |
| Finish / create | ✅ |

---

## 9. Tablet experience

| Feature | Mobile |
|---------|--------|
| NavigationRail shell | ✅ | ≥840px (10I) |
| Sales master-detail | ✅ | `AdaptiveMasterDetail` ≥900px |
| Inventory master-detail | ⚠️ | Bottom sheet on phone; split deferred |
| Catalogue master-detail | ⚠️ | Single column; deferred |
| Landscape optimization | ✅ | Responsive layouts |

---

## Parity summary

| Module | 10I | 10J |
|--------|-----|-----|
| Inventory | ⚠️ | ✅ (wizard + audit) |
| Catalogue | ⚠️ | ✅ |
| Sales | ⚠️ | ✅ |
| Settings | ⚠️ | ✅ (within mobile scope) |
| Reports | ✅ | ✅ |
| Users | ⚠️ | ⚠️ (admin actions; no create form) |
| Global search | ⚠️ | ✅ (within API limits) |
| Dashboard | ⚠️ | ✅ (within API limits) |
