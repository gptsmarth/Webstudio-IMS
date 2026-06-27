---
Title: ADR-0011 — Tally Integration Strategy
Version: 1.0
Status: Accepted
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/PROJECT_BIBLE.md, docs/product/PRODUCT_REQUIREMENTS.md, docs/SYSTEM_ARCHITECTURE.md, docs/database/DATABASE_DESIGN.md, docs/api/API_SPECIFICATION.md
---

# ADR-0011: Tally Integration Strategy

| Attribute | Value |
|-----------|-------|
| **ADR ID** | ADR-0011 |
| **Version** | 1.0 |
| **Status** | Accepted |
| **Date** | 2026-06-27 |

---

## Purpose

Record the binding architectural decisions for **Tally ERP 9 integration** in WEBSTUDIO IMS Version 1.

This ADR establishes:

- The billing vs inventory boundary between Tally and IMS
- How sales are reflected in inventory from Tally invoices
- Multi-company synchronization behaviour
- Invoice line matching rules and operator notifications
- Manual mark-as-sold fallback and duplicate sale protection
- Explicit exclusions for Version 1

All implementation (Tally Sync worker, Backend API, database schema, UI dashboard, and notification flows) must conform to this ADR and the governing specifications it references.

---

## Decision

WEBSTUDIO IMS Version 1 adopts the following Tally integration strategy.

### System boundaries

| Decision | Detail |
|----------|--------|
| **Tally is the Billing System** | Tally ERP 9 remains the sole system of record for invoices, receipts, accounting, and tax. WEBSTUDIO IMS **never** creates invoices or billing entries in Tally. |
| **IMS is the Inventory System** | WEBSTUDIO IMS is the sole system of record for laptop inventory state, serial numbers, locations, and movement history. |
| **Read-only integration** | IMS **reads** sales invoices from Tally. The integration direction is **Tally → IMS** only. No write operations to Tally. |
| **API-only mutation** | Tally Sync worker calls Backend REST endpoints. It **never** accesses PostgreSQL directly. |

### Transport and protocol

| Decision | Detail |
|----------|--------|
| **XML over HTTP** | Tally Sync communicates with Tally ERP 9 via Tally's native **HTTP/XML** interface on the office LAN. |
| **Untrusted input** | All Tally XML is treated as untrusted until parsed with `defusedxml` and validated against expected voucher structure. |
| **Isolated worker** | Tally Sync runs as a separate Windows Service (`apps/server` Tally worker) — same isolation model as Excel Sync. |

### Synchronization schedule

| Decision | Detail |
|----------|--------|
| **Automatic interval** | Tally Sync polls on a configurable interval stored in `system_settings`. |
| **Default interval** | **30 minutes** (`tally_sync_interval_seconds = 1800`). |
| **Manual trigger** | **Sync Now** — available to **Admin** and **Main Admin** via `POST /api/v1/integrations/tally/sync/trigger`. |
| **Future configuration** | Interval adjustable from System Settings (Main Admin). |

### Multi-company support

| Decision | Detail |
|----------|--------|
| **Multiple Tally companies** | Integration supports multiple Tally companies in one deployment. |
| **Initial companies** | **WEBSTUDIO** (multi-brand store); **ASUS Exclusive Store**. |
| **Independent sync state** | Each company has its own `tally_company_sync` row storing: `last_successful_sync_time`, `last_processed_voucher_identifier`. |
| **Failure isolation** | A synchronization failure for one company **must never** stop synchronization of another company. Processing continues per company independently. |

### Invoice line processing

Every invoice line from Tally is evaluated independently using **exact** matching only.

| Condition | Action |
|-----------|--------|
| **Serial number matches IMS** AND **Product Model matches IMS** | Mark inventory **Sold**; create `sale` record (`sale_source = tally`); write audit log |
| **Product Model exists in IMS** BUT **Serial not found** | Create **Serial Not Found** notification; no inventory mutation |
| **Serial exists in IMS** BUT **Product Model does not match** | Create **Model Mismatch** notification; no inventory mutation |
| **Neither Serial nor Product Model exist in IMS** | **Ignore** line — assume accessory or non-laptop product; **no notification** |

| Rule | Detail |
|------|--------|
| **Exact serial matching only** | No fuzzy matching, partial matching, or normalization beyond documented field extraction. |
| **Product Model verification** | Match requires both serial number **and** product model identity (brand + model number as mapped from Tally line to IMS `product_model`). |
| **Ignore accessory invoices** | Lines with no IMS serial and no IMS model are silently ignored — not errors, not notifications. |

### Notifications

| Decision | Detail |
|----------|--------|
| **Notification Center** | Tally integration alerts surface in the **Notification Center** and Tally Synchronization Dashboard pending count. |
| **Notification types** | `serial_not_found`, `model_mismatch`, `duplicate_sale`, `sync_failure` |
| **No notification for ignored lines** | Accessory / non-IMS invoice lines do not generate notifications. |
| **Persistence** | Notifications stored in `notifications` table; resolved by Admin/Main Admin — not deleted V1. |

### Tally Synchronization Dashboard

Admin and Main Admin access a dashboard displaying:

- Connection status
- Configured companies
- Last successful sync (per company)
- Next scheduled sync
- Pending notifications count
- Last error
- **Sync Now** button

API: `GET /api/v1/integrations/tally/dashboard`.

### Manual mark-as-sold

| Decision | Detail |
|----------|--------|
| **Who** | **Admin** and **Main Admin** only — **Salesperson excluded** |
| **When** | Tally sync unavailable, delayed, or operator needs immediate inventory update |
| **Required field** | **Invoice Number** (links to Tally billing reference) |
| **Optional fields** | Customer Name, Payment Mode, Sale Date |
| **Effect** | Creates `sale` (`sale_source = manual`); marks inventory Sold; audit log |
| **API** | `POST /api/v1/sales/reflect` |

### Duplicate sale protection

| Decision | Detail |
|----------|--------|
| **Same transaction** | If Tally sync imports an invoice already recorded manually (same invoice/voucher identifier + serial), **do not** create a duplicate sale. |
| **Idempotency keys** | Tally: `(tally_company_name, tally_voucher_number, inventory_item_id)`; Manual: `(invoice_number, inventory_item_id)` |
| **Cross-source** | Manual sale and subsequent Tally import for same invoice + serial = idempotent no-op; optional **Duplicate Sale** notification for operator awareness |
| **Terminal state** | Sold is terminal V1 — no duplicate sale records per inventory item |

### Version 1 exclusions

The following are **explicitly out of scope**:

| Exclusion | Rationale |
|-----------|-----------|
| **Returns** | Requires reverse lifecycle — Version 2+ |
| **Refunds** | Billing domain — Tally only |
| **Credit notes** | Billing domain — Tally only |
| **Invoice cancellation** | Billing domain — Tally only |
| **Automatic inventory creation from Tally** | Inventory is registered in IMS first; Tally reflects sales only |
| **Fuzzy serial matching** | Error-prone in retail; exact match required |

---

## Context

WEBSTUDIO IMS replaces manual Excel inventory updates for a laptop retail business operating an ASUS Exclusive Store and a WEBSTUDIO multi-brand store within one building. Staff bill customers in **Tally ERP 9** — a process that will not change. After each sale, inventory must reflect **Sold** status without manual Excel edits.

### Business constraints

- Tally ERP 9 is entrenched as the billing and accounting system (Project Bible N4, PRD BC-01).
- The business bills through **two Tally companies**: WEBSTUDIO and ASUS Exclusive Store.
- Only **laptops** with registered serial numbers are managed in IMS — accessories and non-tracked products are billed in Tally but not inventoried in IMS.
- Retail staff include Salespersons who must not manually override sold state without Admin oversight.

### Technical constraints

- Tally exposes sales data via **HTTP/XML** on the LAN — not a modern REST API.
- Tally Sync worker is an API client only — PostgreSQL mutations pass through Backend services (SaleService) with RBAC and audit.
- Implementation remains **blocked on Tally POC** until production Tally instance validates XML extraction of serial numbers and model identifiers (SYSTEM_ARCHITECTURE §14.3.1).

### Problem addressed

Prior documentation described Tally integration as "mechanism TBD" with ambiguous serial mapping and Salesperson manual sale fallback. The business requires:

1. Automatic sale reflection on a predictable schedule
2. Clear handling when Tally lines do not match IMS records
3. Operator visibility via dashboard and notifications — not silent failures
4. A controlled manual path when sync is delayed
5. Protection against duplicate sales when manual and automatic paths converge

---

## Alternatives Considered

### IMS creates invoices in Tally

**Rejected.** Violates billing boundary. Tally is the system of record for invoices, tax, and accounting. IMS would duplicate billing logic and create reconciliation risk.

### Bidirectional sync (Tally ↔ IMS)

**Rejected.** Inventory registration belongs in IMS. Allowing Tally to drive stock creation would bypass Product Model lifecycle, serial uniqueness validation, and audit controls.

### Push/webhook from Tally to IMS

**Deferred.** Tally ERP 9 primary integration pattern is HTTP/XML request/response polling. Push requires additional Tally configuration and is not assumed available V1. Polling on configurable interval is sufficient for 30-minute target latency.

### Single-company Tally integration

**Rejected.** Business operates two Tally companies (WEBSTUDIO, ASUS Exclusive Store). Separate sync state per company is required.

### Fuzzy or partial serial matching

**Rejected.** Fuzzy matching risks marking the wrong laptop sold — unacceptable in serial-number-first retail. Exact match only; mismatches generate notifications for human review.

### Serial-only matching (no product model verification)

**Rejected.** Serial could theoretically be mis-entered in Tally with wrong model on invoice line. Requiring both serial **and** product model match reduces false-positive sale reflection.

### Notify on every unmatched line including accessories

**Rejected.** Accessory-heavy invoices would flood Notification Center with noise. Lines where neither serial nor model exist in IMS are intentionally ignored.

### Salesperson manual mark-as-sold

**Rejected.** Manual sold state is a privileged operation requiring invoice number accountability. Admin and Main Admin only.

### Process returns/refunds via Tally sync V1

**Rejected.** Returns require inventory lifecycle reversal (Sold → Available/Returned) — not defined in Version 1. Deferred to Version 2+.

### Direct PostgreSQL writes from Tally Sync worker

**Rejected.** Violates Backend authority (Project Bible N2). All mutations through SaleService with idempotency, audit, and RBAC.

---

## Consequences

### Positive

- **Clear billing boundary** — no ambiguity about which system owns invoices vs inventory.
- **Predictable sync** — 30-minute default with Sync Now for operational control.
- **Multi-company safe** — isolated failure domains per Tally company.
- **Operator visibility** — dashboard and Notification Center replace silent Excel drift.
- **Duplicate protection** — manual and Tally paths converge safely on same invoice + serial.
- **Reduced false positives** — dual serial + model match before marking Sold.
- **Accessory noise eliminated** — ignored lines stay silent.

### Negative / trade-offs

- **POC dependency** — implementation blocked until Tally XML field mapping validated on production instance.
- **No real-time sync** — 30-minute default means inventory may lag billing; mitigated by Sync Now and manual mark-as-sold.
- **Manual reconciliation load** — Serial Not Found and Model Mismatch notifications require Admin action.
- **No return path V1** — returned laptops after sale require manual process outside IMS until Version 2+.
- **Exact match strictness** — minor Tally data entry errors (typo in serial) require notification workflow rather than automatic correction.

### Compliance with governing documents

This ADR aligns with and is traceable to:

- [PRODUCT_REQUIREMENTS.md](../docs/product/PRODUCT_REQUIREMENTS.md) — §8.4, §8.6, FR-TLY-*, FR-NOT-*, FR-SLS-*, BR-32–BR-37
- [SYSTEM_ARCHITECTURE.md](../docs/SYSTEM_ARCHITECTURE.md) — §6.3, §14.3–§14.7
- [DATABASE_DESIGN.md](../docs/database/DATABASE_DESIGN.md) — §4.8 Sale, §4.11–§4.13, §10.2
- [API_SPECIFICATION.md](../docs/api/API_SPECIFICATION.md) — §11 Sales, §15 Tally Integration

**Supersedes:** Informal Tally planning previously referenced as ADR-0007 in architecture readiness tables. ADR-0011 is the binding integration strategy document.

---

## Implementation Notes

### Components

| Component | Responsibility |
|-----------|----------------|
| **Tally Sync Windows Service** | Poll Tally XML; iterate companies; parse invoices; call Backend per line |
| **`packages/integrations/tally/`** | XML client, parser, company iterator — hexagonal adapter |
| **SaleService** | Line matching logic; mark Sold; idempotency; notification creation |
| **TallyCompanySync repository** | Per-company cursor updates |
| **Notification repository** | Persist and resolve Tally alerts |

### Database (migration `0009_integrations`)

| Table | Purpose |
|-------|---------|
| `tally_company_syncs` | Per-company sync cursor and error state |
| `sales` | Immutable sale records — `invoice_number`, `payment_mode`, `sale_source` |
| `tally_integration_events` | Poll and line processing log |
| `notifications` | Operator alerts |
| `system_settings` | `tally_sync_interval_seconds` (default 1800), `tally_host`, `tally_port`, `tally_enabled` |

Seed: WEBSTUDIO and ASUS Exclusive Store rows in `tally_company_syncs`.

### Backend API (key endpoints)

| Endpoint | Caller | Purpose |
|----------|--------|---------|
| `POST /api/v1/integrations/tally/sales/process-line` | Tally Sync worker | Evaluate one invoice line |
| `POST /api/v1/integrations/tally/sync/trigger` | Admin/Main Admin | Sync Now |
| `GET /api/v1/integrations/tally/dashboard` | Admin/Main Admin | Dashboard data |
| `GET /api/v1/integrations/tally/notifications` | Admin/Main Admin | Notification Center |
| `POST /api/v1/sales/reflect` | Admin/Main Admin | Manual mark-as-sold |

### Tally Sync worker flow

1. Read enabled companies from `tally_company_syncs`
2. For each company independently:
   - Request invoices since `last_processed_voucher_identifier` via XML/HTTP
   - Parse with `defusedxml`
   - For each invoice line → `POST .../sales/process-line`
   - On company success → update `last_successful_sync_time` and voucher cursor
   - On company failure → `sync_failure` notification; **continue next company**
3. Schedule next poll via APScheduler from `tally_sync_interval_seconds`

### Security

- [ ] Tally XML parsed with `defusedxml` — no XXE
- [ ] Tally Sync uses service account JWT — scoped `tally:worker` permission only
- [ ] No Tally credentials in source control — `tally_host`/`tally_port` in settings or env
- [ ] All sale mutations audited — `sale.reflect` action

### POC gate (before production)

Complete SYSTEM_ARCHITECTURE §14.3.1 checklist:

- Tally HTTP/XML reachable from server
- Sales voucher types identified
- Serial and model number reliably extracted from voucher lines
- Duplicate voucher re-submission idempotent
- XML fixtures in `packages/testing/fixtures/tally/`

### Out of scope (do not implement V1)

- Returns, refunds, credit notes, invoice cancellation sync
- Automatic `inventory_item` creation from Tally
- Fuzzy serial matching
- Write operations to Tally
- Salesperson manual mark-as-sold

---

## References

| Document | Path |
|----------|------|
| Product Requirements | [docs/product/PRODUCT_REQUIREMENTS.md](../docs/product/PRODUCT_REQUIREMENTS.md) |
| System Architecture | [docs/SYSTEM_ARCHITECTURE.md](../docs/SYSTEM_ARCHITECTURE.md) |
| Database Design | [docs/database/DATABASE_DESIGN.md](../docs/database/DATABASE_DESIGN.md) |
| API Specification | [docs/api/API_SPECIFICATION.md](../docs/api/API_SPECIFICATION.md) |
| ADR-0010 Authentication | [adr/ADR-0010-authentication-and-initialization.md](ADR-0010-authentication-and-initialization.md) |
| Tally Integration Package | [packages/integrations/tally/](../packages/integrations/tally/) |

---

> **Immutability:** This ADR is **Accepted**. Changes to these decisions require a new ADR that supersedes ADR-0011 — do not silently amend accepted decisions in implementation.

*WEBSTUDIO IMS Team — 2026*
