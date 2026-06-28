---
Title: Tally Sync Strategy
Version: 1.2.0
Status: Frozen
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/SYSTEM_ARCHITECTURE.md, docs/product/PRODUCT_REQUIREMENTS.md, docs/database/DATABASE_DESIGN.md, docs/api/API_SPECIFICATION.md
---

# Tally Sync Strategy

> **Architecture status:** **Frozen** — these rules are the official synchronization behaviour for WEBSTUDIO IMS Version 1. The inventory matching strategy in §3 is **authoritative** and must not be overridden by product model names during sale reflection. Implementation of the Tally Synchronization module must follow this document exactly.

## 1. Source of Truth

| System | Role |
|--------|------|
| **Tally ERP 9** | Primary source of truth for **sales** — invoices are read from Tally |
| **WEBSTUDIO IMS (PostgreSQL)** | Authoritative source of truth for **inventory state** |

Sales are normally synchronized from Tally. The IMS **must** continue supporting manual **Mark as Sold** for **Main Admin** and **Admin** only — for exceptional situations when Tally sync is delayed or unavailable. Manual sales generate normal audit entries (`sale.reflect`, `inventory.transition`) with `sale_source = manual`.

**Billing boundary:** IMS **never** creates invoices, credit notes, or billing entries in Tally.

---

## 2. Invoice Processing Model

A Tally invoice is **never** treated as a single inventory record.

Every inventory-related line item is processed **independently**. A failure on one line must **never** stop processing of the remaining lines.

**Example — Invoice with four lines:**

| Line | Product | IMS action |
|------|---------|------------|
| 1 | Laptop A (serial) | Process independently |
| 2 | Laptop B (serial) | Process independently |
| 3 | Mouse | Evaluate — likely ignored (non-inventory) |
| 4 | Keyboard | Evaluate — likely ignored (non-inventory) |

---

## 3. Inventory Matching Strategy (Frozen)

This section defines the **authoritative inventory matching logic** for the Tally Synchronization Engine. It is considered **frozen** for Version 1 implementation.

### 3.1 Primary Matching Rule

The **Serial Number** is the **only authoritative identifier** used to determine whether an inventory item has been sold.

For every inventory-related line item received from Tally:

1. Extract the **Serial Number** from the invoice line.
2. Search **only** inventory items with status **`available`** using the Serial Number (exact match).
3. If found:
   - Mark the inventory item **`sold`**.
   - Create a `sale` record (`sale_source = tally`) with invoice number, voucher type, customer name, and sale date from the invoice.
   - Write the normal **Audit Log** entries (`inventory.transition`, `sale.reflect`; `source = TALLY_SYNC`).
4. **Product Model names must never determine whether an inventory item is sold.** A successful serial match in **`available`** inventory always results in a sale reflection — regardless of product model text on the invoice line.

**Reserved** items are **not** matched in Version 1 unless explicitly extended in a future ADR. Only **`available`** inventory is eligible for automatic Tally sale reflection.

### 3.2 Product Model Verification (Informational Only)

After a **successful Serial Number match** (§3.1), compare the Product Model from the invoice with the Product Model stored in IMS.

| Rule | Behaviour |
|------|-----------|
| Purpose | Verification and operator alerting only |
| Sale reflection | **Must never be blocked** by model comparison outcome |
| Timing | Runs **after** inventory is marked **sold** and sale/audit records are committed |
| Mismatch handling | See §3.4 — warning notification only |

Product model verification **must not** be used as a pre-condition for marking inventory as sold.

### 3.3 Model Name Normalization

Model names may legitimately differ between Tally and IMS. These are **normal variations** and must **not** generate notifications.

| IMS (stored) | Tally (invoice line) | Result |
|--------------|----------------------|--------|
| `ASUS Vivobook X1502ZA-EJ745WS` | `ASUS X1502ZA-EJ745WS` | Equivalent after normalization |
| `ASUS Vivobook X1502ZA-EJ745WS` | `X1502ZA-EJ745WS` | Equivalent after normalization |

The synchronization engine **shall normalize** model names before comparison wherever possible. Recommended normalization steps (implementation detail):

1. Trim leading/trailing whitespace.
2. Collapse internal whitespace to a single space.
3. Compare case-insensitively.
4. Strip common marketing prefixes/suffixes that differ between systems (e.g., `Vivobook`, `Inspiron`, `Pavilion`) when a shared **model number token** (e.g., `X1502ZA-EJ745WS`) is present on both sides.
5. Prefer **model number** equality when both sides contain a recognizable model number from the IMS `product_model.model_number` field.

**Minor naming differences after normalization must not generate notifications.**

### 3.4 Model Mismatch Warning

If the Serial Number matches in **`available`** inventory but the **normalized** Product Model from the invoice appears **genuinely different** from the Product Model stored in IMS:

| Example IMS model | Example invoice model | Action |
|-------------------|----------------------|--------|
| Dell Inspiron 3530 | HP Pavilion 15 | Mark **sold** (serial authoritative) + warning notification |

| Rule | Behaviour |
|------|-----------|
| Inventory | Item **still marked sold** — Serial Number is authoritative |
| Sale record | Created normally |
| Audit Log | Written normally |
| Notification | **`product_model_mismatch`** (Product Model Mismatch) — **informational only**; does **not** affect synchronization outcome |

**Notification payload (minimum):**

| Field | Source |
|-------|--------|
| Invoice Number | Tally invoice |
| Customer Name | Tally invoice |
| Serial Number | Invoice line |
| Inventory Product Model | IMS `product_model` (model name and/or model number) |
| Invoice Product Model | Raw model text from Tally invoice line |
| Detection Time | Server timestamp |
| Description | e.g., *"Serial matched and item marked sold, but invoice product model differs from IMS after normalization. Please verify billing data."* |

### 3.5 Matching Priority (Official Order)

| Priority | Rule | Effect |
|----------|------|--------|
| **1** | **Serial Number** (authoritative) | Determines whether inventory is marked **sold** |
| **2** | **Product Model Verification** (informational only) | May generate **`product_model_mismatch`** warning after sale; **never** blocks sale |

**Product Models must never override a successful Serial Number match.**

---

## 4. Duplicate Sale Detection

If the serial number is **not** found in **available** inventory:

1. Search inventory items with status **`sold`** for the same serial number.
2. If found:
   - **Do not** modify inventory.
   - **Do not** generate duplicate audit entries.
   - **Create a notification** — type **`duplicate_sale`** (Duplicate Sale Detected).

**Notification payload (minimum):**

| Field | Source |
|-------|--------|
| Invoice Number | Tally invoice |
| Voucher Type | Tally voucher type |
| Customer Name | Tally invoice |
| Serial Number | Invoice line |
| Product Model | If available from line or matched sold item |
| Detection Time | Server timestamp |
| Description | e.g., *"This serial number is already marked as SOLD in IMS. No changes were made. Please verify the invoice in Tally."* |

---

## 5. Missing Serial / Model Rules

After duplicate-sale check (§4), when serial is **not** in **`available`** inventory:

| Condition | Action |
|-----------|--------|
| **Product model exists in IMS** AND **serial does not exist** | Create notification — **`serial_number_missing`** (Serial Number Missing) |
| **Serial exists in IMS** (non-available, non-sold path) AND **product model from invoice not in catalog** | Create notification — **`product_model_missing`** (Product Model Missing) |
| **Neither serial nor model exists in IMS** | **Ignore** line — assume non-inventory product (mouse, keyboard, accessories, software, services). **No notification.** |

> **Distinction:** **`product_model_missing`** applies when the invoice references a serial that exists in IMS but the invoice product model is **not in the catalog** — evaluated on the **no available match** path. **`product_model_mismatch`** (§3.4) applies when serial **did** match **`available`** inventory and was sold, but normalized models **genuinely differ** — informational warning only.

---

## 6. Multiple Inventory Items per Invoice

The engine supports invoices containing multiple inventory items (e.g., Invoice 325 — Laptop A + Laptop B).

| Requirement | Rule |
|-------------|------|
| Processing | Each item processed independently |
| Status update | Each eligible item marked **sold** independently |
| Shared metadata | Same invoice number, sale date, and customer information from the invoice |
| Partial failure | If one item cannot be processed, remaining items **continue** |

---

## 7. Notification Center

### Categories (Version 1)

| Category | Enum | Trigger |
|----------|------|---------|
| Duplicate Sale | `duplicate_sale` | Serial already sold in IMS |
| Serial Number Missing | `serial_number_missing` | Model in IMS; serial not found in available inventory |
| Product Model Missing | `product_model_missing` | Serial in IMS (non-available path); invoice model not in catalog |
| Product Model Mismatch | `product_model_mismatch` | Serial matched available inventory and sold; normalized invoice model genuinely differs from IMS |
| Tally Sync Completed | `tally_sync_completed` | Invoice or sync cycle completed successfully |
| Synchronization Failure | `sync_failure` | Connection or company-level failure |
| Future System Notifications | — | Reserved for post-V1 system alerts |

### Lifecycle States

| State | Persistence |
|-------|-------------|
| **Unread** | `is_read = false`, `is_resolved = false` |
| **Read** | `is_read = true`, `is_resolved = false` |
| **Resolved** | `is_resolved = true`, `resolved_at` set — **retained permanently** for historical reference |

Notifications are **never deleted** in Version 1.

**Admin and Salesperson:** No self-service password recovery; Tally notifications visible to **Main Admin** and **Admin** via Notification Center and Tally Sync Dashboard.

---

## 8. Table Responsibilities

Two tables serve distinct purposes — **do not merge their roles**.

| Table | Purpose |
|-------|---------|
| **`tally_processed_invoices`** | Invoice-level **processing state** and **idempotency**. Authoritative record of whether an invoice is complete, partial, failed, or skipped. |
| **`tally_sync_logs`** | Synchronization **execution history**. One row per processing attempt — diagnostics only. |

Every synchronization run writes a `tally_sync_log` row and references the `tally_processed_invoice` record where applicable.

Line-level outcomes for partial retry are tracked in **`tally_processed_invoice_lines`** (see §9).

---

## 9. Invoice Processing Status

The `tally_processed_invoices` table stores `processing_status`:

| Status | Definition |
|--------|------------|
| **SUCCESS** | Every inventory-related line completed successfully. Inventory updates committed. Audit entries created where applicable. Invoice is **fully processed** — future syncs **skip** this invoice. |
| **PARTIAL_SUCCESS** | One or more inventory-related lines completed; one or more **failed** (technical error or interruption). Successful lines **remain committed**. Failed lines **remain eligible for retry**. Invoice is **not** fully processed. |
| **FAILED** | **No** inventory updates completed. Entire invoice **eligible for full retry**. |
| **SKIPPED** | Invoice already in **SUCCESS** state. No processing performed on this run. Recorded in sync log only — `tally_processed_invoices.processing_status` remains **SUCCESS**. |

### 9.1 Invoice Completion Rule

An invoice is marked **SUCCESS** only after **all** inventory-related line items have completed successfully.

**Never** set `processing_status = SUCCESS` before processing finishes.

Inventory-related lines are those with a serial or product model reference from Tally (excluding ignored accessory/service lines per §5).

### 9.2 Partial Retry

When `processing_status = PARTIAL_SUCCESS`:

| Rule | Behaviour |
|------|-----------|
| Retry scope | **Failed lines only** — identified via `tally_processed_invoice_lines.line_status = failed` |
| Completed lines | **Never** reprocessed — `line_status = completed` is immutable |
| Status transition | When all remaining failed lines succeed → promote to **SUCCESS** |
| Idempotency | Successful inventory updates from prior attempts are never duplicated |

### 9.3 Crash Recovery

The engine must tolerate unexpected interruptions (application crash, database restart, server shutdown, network interruption).

After restart:

| Prior `processing_status` | Behaviour |
|---------------------------|-----------|
| **SUCCESS** | Skip invoice — sync log records **SKIPPED** |
| **PARTIAL_SUCCESS** | Resume — retry **failed lines only** |
| **FAILED** | Retry entire invoice |
| **SKIPPED** (log outcome) | No change — invoice remains **SUCCESS** |

Synchronization must **never** create duplicate inventory updates, audit entries, or notifications for lines already marked **completed**.

### 9.4 Line-Level Transactions

Each inventory item within an invoice is processed in its **own transaction**.

| Rule | Behaviour |
|------|-----------|
| Isolation | One failed line **never** rolls back successfully processed lines from the same invoice |
| Commit | Each line commits independently on success |
| Invoice status | Derived **after** all lines in the current attempt finish — not wrapped in a single invoice transaction |

---

## 10. Tally Sync Log

Synchronization statistics belong in **`tally_sync_logs`** — **not** in the Audit Log.

One log row per **synchronization execution attempt** (including skipped invoices).

| Field | Description |
|-------|-------------|
| Sync Run ID | Unique identifier for this execution attempt (`sync_run_id`) |
| Invoice Number | Tally invoice / voucher number |
| Voucher GUID | Stable Tally unique identifier |
| Voucher Type | Tally voucher type |
| Start Time | Processing start |
| End Time | Processing end |
| Processing Duration | Elapsed time (ms) |
| Processing Status | `success`, `partial_success`, `failed`, `skipped` — outcome of **this run** |
| Number of Inventory Items | Inventory-related lines evaluated |
| Successfully Updated | Items marked sold |
| Already Sold | Duplicate-sale lines (notification created) |
| Missing Serial | `serial_number_missing` count |
| Missing Model | `product_model_missing` count |
| Model Mismatch | `product_model_mismatch` count (informational — sale still applied) |
| Ignored Items | Non-inventory lines skipped |
| Retry Count | Attempt number for this invoice |
| Error Details | Present when run `failed` |
| `tally_processed_invoice_id` | FK — links log to invoice state record |

**Run outcome semantics:**

| `processing_status` (log) | Meaning |
|---------------------------|---------|
| `success` | This run completed all remaining inventory-related lines |
| `partial_success` | This run completed some lines; failures remain |
| `failed` | This run produced zero inventory updates |
| `skipped` | Invoice already **SUCCESS** — no processing performed |

Line-level detail may additionally be recorded in `tally_integration_event`. The sync log is for **diagnostics and reconciliation only**.

---

## 11. Audit Log Separation

The **Audit Log** records **business events only**:

- Inventory sold (Tally or manual)
- Manual sale
- Location changed
- Inventory created
- User and configuration changes

**Do not** write synchronization statistics, poll counts, or line-outcome summaries to the Audit Log. Those belong in the Tally Sync Log.

Tally-driven sales use audit `source = TALLY_SYNC` where applicable.

---

## 12. Invoice Idempotency and Processing Algorithm

The synchronization engine is **idempotent**. Repeated polling (e.g., every 30 minutes) must **never** create duplicate inventory updates, audit entries, or notifications for completed lines.

### Per-cycle algorithm

```
FOR each invoice from Tally:
  LOAD or CREATE tally_processed_invoice by (company, voucher_guid)

  IF processing_status = SUCCESS:
    WRITE tally_sync_log (processing_status = skipped)
    CONTINUE

  IF processing_status = PARTIAL_SUCCESS:
    lines_to_process = failed lines only (tally_processed_invoice_lines)
  ELSE IF processing_status = FAILED or new:
    lines_to_process = all inventory-related lines

  FOR each line in lines_to_process (independent transaction each):
    EXTRACT serial from line
    IF serial in available inventory:
      MARK sold; CREATE sale; WRITE audit (§3.1)
      NORMALIZE and COMPARE product models (§3.2–§3.3)
      IF genuinely different → CREATE product_model_mismatch notification (§3.4)
      MARK line completed
    ELSE IF serial in sold inventory:
      CREATE duplicate_sale notification (§4); MARK line completed
    ELSE apply missing-serial/model rules (§5) or ignore
    UPDATE tally_processed_invoice_lines (completed | failed)

  DERIVE processing_status:
    IF all inventory-related lines completed → SUCCESS
    ELSE IF any line completed AND any failed → PARTIAL_SUCCESS
    ELSE IF zero inventory updates → FAILED

  WRITE tally_sync_log for this run (with sync_run_id, retry_count)
  UPDATE tally_processed_invoice.processing_status
```

### Examples

| Scenario | Result |
|----------|--------|
| Invoice 325 — all laptops sold | `processing_status = SUCCESS`; future runs **SKIPPED** |
| Invoice 326 — crash after 1 of 2 laptops sold | `PARTIAL_SUCCESS`; on restart retry failed line only |
| Invoice 327 — DB error before any sale | `FAILED`; full retry on next run |
| Invoice 325 re-seen after SUCCESS | Sync log `skipped`; no line processing |

**Line-level duplicate protection** (within a new or retrying invoice): serial already **sold** → Duplicate Sale notification; line marked **completed**; no inventory/audit change.

---

## 13. Multi-Company and Scheduling

| Concern | Rule |
|---------|------|
| Companies | WEBSTUDIO; ASUS Exclusive Store (initial) — independent state per company |
| Interval | Default **1800 seconds (30 minutes)** — configurable |
| Failure isolation | Company failure does not block other companies |
| Manual trigger | **Sync Now** — Admin and Main Admin |
| Worker access | Tally Sync Service → API only — never direct PostgreSQL |

---

## 14. Version 1 Exclusions

- Returns, refunds, credit notes, invoice cancellation
- Automatic inventory creation from Tally
- Fuzzy or partial **serial** matching
- Using product model name as a **pre-condition** for marking inventory sold
- Writes to Tally ERP 9

---

## References

| Document | Section |
|----------|---------|
| [SYSTEM_ARCHITECTURE.md](../../SYSTEM_ARCHITECTURE.md) | §14.3 Tally Integration |
| [PRODUCT_REQUIREMENTS.md](../../product/PRODUCT_REQUIREMENTS.md) | §8.6 Tally Synchronization |
| [DATABASE_DESIGN.md](../../database/DATABASE_DESIGN.md) | §4.10–4.10.2, §6.12–6.14 |
| [API_SPECIFICATION.md](../../api/API_SPECIFICATION.md) | §11.2, §15 |
