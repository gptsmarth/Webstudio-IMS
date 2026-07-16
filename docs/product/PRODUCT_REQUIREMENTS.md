---
Title: WEBSTUDIO IMS — Product Requirements Document
Version: 1.8
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/PROJECT_BIBLE.md, docs/business/README.md, docs/integrations/README.md, specs/product/README.md
---

# WEBSTUDIO IMS — Product Requirements Document (PRD)

| Attribute | Value |
|-----------|-------|
| **Document ID** | PRD-001 |
| **Product Name** | WEBSTUDIO IMS (WEBSTUDIO Inventory Management System) |
| **Version** | 1.8 |
| **Status** | Active — audit log as sole inventory history |
| **Product Type** | Internal Commercial Inventory Management Software |
| **Deployment** | On-Premise Server |
| **Target Release** | Version 1.0 — Laptops Only |
| **Governing Document** | [PROJECT_BIBLE.md](../PROJECT_BIBLE.md) |

> **Authority:** This PRD is the primary business specification for WEBSTUDIO IMS Version 1. Every architectural decision, database design, API contract, UI screen, and implementation must trace back to a requirement in this document or be explicitly marked **TBD** pending PRD amendment.
>
> Where this document conflicts with [PROJECT_BIBLE.md](../PROJECT_BIBLE.md), the Project Bible takes precedence until this PRD is formally revised.

---

## Version History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.8 | 2026-06-27 | WEBSTUDIO IMS Team | **Tally matching strategy frozen:** Serial Number authoritative for sale reflection; product model verification informational only; model normalization; Product Model Mismatch notification. |
| 1.7 | 2026-06-27 | WEBSTUDIO IMS Team | Removed InventoryMovement module and `inventory_movements` table. Location changes update `current_location_id` only; audit log is the sole source of truth for location, status, and lifecycle history. |
| 1.6 | 2026-06-27 | WEBSTUDIO IMS Team | Finalized Tally ERP 9 synchronization: read-only invoices; multi-company sync state; invoice line matching workflow; Tally Sync Dashboard; Notification Center; manual mark-as-sold (Admin/Main Admin only); duplicate sale protection. |
| 1.5 | 2026-06-27 | WEBSTUDIO IMS Team | Server initialization and client onboarding: `system_initialized` setting; first-time setup wizard; client server discovery and manual configuration; login gated on setup status; Main Admin-only user management; clients never create users or store business data. |
| 1.4 | 2026-06-27 | WEBSTUDIO IMS Team | Authentication & audit strategy: Salesperson may move inventory; operational ownership fields (`created_by_user_id`, `updated_by_user_id`) on business entities; enriched audit log requirements; excluded action-specific user fields (`sold_by`, `reserved_by`, `approved_by`). |
| 1.3 | 2026-06-27 | WEBSTUDIO IMS Team | Synchronized with Sprint 1D implementation: `current_location_id`; `Reserved` inventory status; structured ProductModel specs; serial number editable by authorized users; conditional inventory delete; excluded configuration/row_version fields. |
| 1.2 | 2026-06-27 | WEBSTUDIO IMS Team | Product Model lifecycle (Active/Archived). Mandatory Color on inventory items. Expanded search (Color, combined filters). Explicit exclusion of Purchase Date, Purchase Cost, and Remarks from V1. |
| 1.1 | 2026-06-27 | WEBSTUDIO IMS Team | Final review. Added inventory lifecycle, entity definition, presentation rules, data relationships, dashboard requirements, barcode scanner behavior, and expanded search requirements. |
| 1.0 | 2026-06-27 | WEBSTUDIO IMS Team | Initial official PRD. Defines Version 1 scope, workflows, functional and non-functional requirements, roles, business rules, and success criteria. |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Business Objectives](#3-business-objectives)
4. [Product Goals](#4-product-goals)
5. [Stakeholders](#5-stakeholders)
6. [User Personas](#6-user-personas)
7. [Existing Workflow](#7-existing-workflow)
8. [Proposed Workflow](#8-proposed-workflow)
    - [8.6 Tally Synchronization](#86-tally-synchronization)
    - [8.6.1 Invoice Line Processing](#861-invoice-line-processing)
    - [8.6.2 Manual Mark as Sold](#862-manual-mark-as-sold)
    - [8.7 Server Installation & First-Time Setup](#87-server-installation--first-time-setup)
    - [8.8 Client Installation & Server Connection](#88-client-installation--server-connection)
    - [8.9 Post-Connection Login Flow](#89-post-connection-login-flow)
9. [Inventory Lifecycle](#9-inventory-lifecycle)
10. [Inventory Entity Definition](#10-inventory-entity-definition)
11. [Inventory Presentation Rules](#11-inventory-presentation-rules)
12. [Data Relationships](#12-data-relationships)
    - [12.2 Product Model Lifecycle](#122-product-model-lifecycle)
13. [Dashboard Requirements](#13-dashboard-requirements)
14. [Barcode Scanner Business Behaviour](#14-barcode-scanner-business-behaviour)
15. [Functional Requirements](#15-functional-requirements)
16. [Non-Functional Requirements](#16-non-functional-requirements)
17. [User Roles and Permissions](#17-user-roles-and-permissions)
18. [Business Rules](#18-business-rules)
19. [Constraints](#19-constraints)
20. [Success Criteria](#20-success-criteria)
21. [Out of Scope](#21-out-of-scope)
22. [Risks](#22-risks)
23. [Assumptions](#23-assumptions)
24. [Future Roadmap](#24-future-roadmap)
25. [Requirement Traceability](#25-requirement-traceability)
26. [References](#26-references)

---

## 1. Executive Summary

WEBSTUDIO IMS is an on-premise inventory management system being built for a laptop retail business operating an ASUS Exclusive Store, a WEBSTUDIO Multi-brand Store, and a Warehouse/Godown — all within one building on a shared Wi-Fi network.

Today, laptop inventory is maintained manually in Excel. After each sale billed in Tally ERP 9, staff manually update Excel — marking rows sold, entering customer details, and recording invoice information. This process is slow, error-prone, and produces inventory drift between physical stock, Excel, and Tally.

WEBSTUDIO IMS eliminates manual inventory tracking by providing a centralized, searchable, auditable inventory system backed by PostgreSQL (accessed exclusively through the Backend API), while preserving Tally ERP 9 as the billing system and maintaining Excel as a synchronized representation for business continuity.

**Version 1 scope:** Individual laptop tracking by serial number across three locations, with model-grouped inventory presentation, per-unit Color tracking, operational dashboard, product-specification- and color-aware search, Excel synchronization, Tally billing integration, barcode scanner support for serial entry, user management, movement history, reports, and audit logging — delivered on Windows Desktop, macOS Desktop, Android, and a Dedicated Server PC.

**Core philosophy:** WEBSTUDIO IMS is **inventory-first**, **serial-number-first**, and **search-first**. Every design and requirement decision must serve accurate individual laptop tracking, instant lookup, and minimal employee training — not feature breadth. Simplicity takes precedence over feature overload.

**Version 1 explicitly excludes:** Billing, accounting, CRM, warranty, service center, accessories, printers, cloud deployment, and multi-city branches.

---

## 2. Problem Statement

### 2.1 Current State

The business tracks every laptop as a row in an Excel spreadsheet. Each row contains Brand, Model Number, Serial Number, product specifications, Color, and Current Location. When a laptop is sold:

1. Billing is completed in **Tally ERP 9**.
2. An employee **manually finds the row** in Excel.
3. The row is **manually marked as sold**.
4. **Customer details** are manually entered.
5. **Invoice information** is manually recorded.

Inventory movement between the ASUS Exclusive Store, WEBSTUDIO Multi-brand Store, and Warehouse/Godown is tracked manually in Excel with no systematic audit trail.

### 2.2 Core Problems

| Problem | Business Impact |
|---------|-----------------|
| **Manual post-sale updates** | Delay between billing and inventory update; sold laptops appear available |
| **No single source of truth** | Excel, physical stock, and Tally diverge over time |
| **Manual location tracking** | Transfers between store and godown are missed or recorded late |
| **No audit trail** | Disputes and shrinkage cannot be investigated reliably |
| **Slow lookup** | Finding a laptop by serial number in Excel is cumbersome under customer pressure |
| **No role-based access** | Excel offers no meaningful permission control |
| **Duplicate entry risk** | Manual processes create duplicate or inconsistent records |

### 2.3 Why Now

The business has outgrown spreadsheet-based inventory management. Continued manual tracking creates compounding accuracy risk as volume grows. The business does not want to replace Tally — it wants inventory management that works alongside existing billing operations.

---

## 3. Business Objectives

| ID | Objective | Measurement |
|----|-----------|-------------|
| BO-01 | Eliminate manual Excel inventory maintenance as the primary tracking method | Manual Excel updates reduced to review/sync verification only |
| BO-02 | Achieve real-time inventory visibility across all three locations | Staff can see current stock by location without opening Excel |
| BO-03 | Ensure every laptop is individually tracked by serial number | 100% of in-stock laptops registered with unique serial numbers |
| BO-04 | Reflect Tally billing events in inventory automatically | Sales in Tally update inventory without manual Excel edits |
| BO-05 | Maintain Excel as a synchronized business-readable export | Excel reflects PostgreSQL inventory on a defined schedule |
| BO-06 | Reduce inventory lookup time on the shop floor | Serial number search perceived as instant — target **TBD** |
| BO-07 | Enable secure, role-based access for staff | Each user operates within defined permissions |
| BO-08 | Preserve Tally ERP 9 as the billing system | Zero billing functionality built into WEBSTUDIO IMS |
| BO-09 | Build a platform foundation for future modules | Architecture supports warranty, service center, and multi-branch without redesign |

---

## 4. Product Goals

WEBSTUDIO IMS Version 1 must:

| # | Goal |
|---|------|
| PG-01 | Track every laptop individually using **Serial Number** as the unique identity |
| PG-02 | Synchronize inventory state with **Excel** as a derived representation |
| PG-03 | Read billing/sales information from **Tally ERP 9** to update inventory |
| PG-04 | Provide **live inventory visibility** across ASUS Exclusive Store, WEBSTUDIO Multi-brand Store, and Warehouse/Godown |
| PG-05 | Support **secure user management** with role-based permissions |
| PG-06 | Deliver applications on **Windows Desktop**, **macOS Desktop**, and **Android** |
| PG-07 | Operate on a **Dedicated Server PC** on the local network |
| PG-08 | Treat **search** as a primary feature — fast serial number and model lookup |
| PG-09 | Deliver a **premium SaaS-quality** user experience with Light and Dark themes |
| PG-10 | Require **minimal training** for retail staff |
| PG-11 | Ensure every inventory change is **auditable** |
| PG-12 | Enforce **PostgreSQL as the single source of truth**, accessed only via Backend API |
| PG-13 | Present inventory **grouped by Model Number** with individual serial units expandable beneath | See [Section 11](#11-inventory-presentation-rules) |
| PG-14 | Provide an **operational dashboard** for immediate stock visibility — not analytics | See [Section 13](#13-dashboard-requirements) |
| PG-15 | Support **product-specification-aware search** across processor, GPU, RAM, and storage (via Product Model fields) | See [Section 15.7](#157-search) |

### 4.1 Core Product Principles

These principles govern every Version 1 requirement. They align with [PROJECT_BIBLE.md](../PROJECT_BIBLE.md) and take precedence over convenience during implementation.

| Principle | Meaning | Application |
|-----------|---------|-------------|
| **Inventory-first** | The product exists to manage physical laptop inventory — nothing else | Reject features that do not improve inventory accuracy, visibility, or control |
| **Serial-number-first** | Every physical laptop is one record identified by one unique serial number | All operations — search, movement, sale — target individual units, not model aggregates |
| **Search-first** | Search is the primary daily interaction, not a secondary utility | Search remains on every primary screen; search performance is never deprioritized |
| **Minimal training** | Retail staff must be productive with brief onboarding | Workflows mirror existing mental models; plain language; no unnecessary steps |
| **Simplicity over feature overload** | Fewer capabilities done well beat many capabilities done poorly | Defer Version 2 features rather than complicate Version 1 |

---

## 5. Stakeholders

| Stakeholder | Role | Interest |
|-------------|------|----------|
| **Business Owner** | Final authority on scope and priorities | Accurate inventory, operational continuity, ROI |
| **Main Admin** | System administrator | Full system control, user management, configuration |
| **Store Managers / Admins** | Day-to-day inventory oversight | Location-level visibility, movement approval, reports |
| **Salespersons** | Front-line retail staff | Fast search, simple sale reflection, minimal steps |
| **Warehouse Staff** | Godown operations | Receiving, transfers, stock verification |
| **WEBSTUDIO IMS Team** | Product and engineering | Delivering Version 1 per this PRD and Project Bible |
| **Future: Service Center Staff** | **TBD** | Not in Version 1 |

---

## 6. User Personas

### 6.1 Main Admin

| Attribute | Detail |
|-----------|--------|
| **Role** | Primary system administrator — typically business owner or designated IT lead |
| **Technical comfort** | Moderate to high |
| **Primary tasks** | User management, system settings, integration configuration, audit review, backup oversight |
| **Goals** | System reliability, data integrity, controlled access, minimal downtime |
| **Frustrations** | Manual reconciliation, untraceable changes, staff using workarounds |
| **Success measure** | Inventory matches physical stock; system runs without daily intervention |

### 6.2 Admin

| Attribute | Detail |
|-----------|--------|
| **Role** | Store or operations manager with elevated inventory permissions |
| **Technical comfort** | Low to moderate |
| **Primary tasks** | Add inventory, approve movements, run reports, manage location-level stock, oversee salesperson activity |
| **Goals** | Accurate location stock, fast answers to "do we have this model?", clean handoffs between store and godown |
| **Frustrations** | Delayed updates after sales, uncertainty about godown stock, Excel version conflicts |
| **Success measure** | Can trust inventory counts during customer interactions |

### 6.3 Salesperson

| Attribute | Detail |
|-----------|--------|
| **Role** | Front-line retail employee at ASUS Exclusive Store or WEBSTUDIO Multi-brand Store |
| **Technical comfort** | Low |
| **Primary tasks** | Search inventory by serial/model, verify availability, initiate sale reflection after Tally billing, request transfers |
| **Goals** | Answer customer questions in seconds; never sell a laptop already sold; minimal data entry |
| **Frustrations** | Slow Excel search, unclear stock status, duplicate manual entry in Tally and Excel |
| **Success measure** | Finds any laptop in seconds; sale reflected without opening Excel |

### 6.4 Future Users (TBD)

| Persona | Status |
|---------|--------|
| Warehouse-only operator | **TBD** — may share Admin/Salesperson permissions initially |
| Service center technician | **TBD** — Version 2+ |
| Multi-branch manager | **TBD** — Version 2+ |
| Read-only auditor | **TBD** |

---

## 7. Existing Workflow

### 7.1 Inventory Receipt (New Stock)

| Step | Actor | Action | Tool |
|------|-------|--------|------|
| 1 | Warehouse/Admin staff | Receive laptops from supplier | Physical |
| 2 | Admin | Add new row to Excel with Brand, Model Number, Serial Number, Color, specifications, Current Location | Excel |
| 3 | Admin | Assign location (Store or Godown) | Excel |

**Pain points:** Manual data entry; typo risk on serial numbers; no validation of duplicate serials.

### 7.2 Inventory Movement (Location Transfer)

| Step | Actor | Action | Tool |
|------|-------|--------|------|
| 1 | Staff | Physically move laptop between locations | Physical |
| 2 | Admin/Staff | Manually update Current Location in Excel row | Excel |

**Pain points:** Movement often recorded late or forgotten; no timestamp or actor recorded; no approval workflow.

### 7.3 Inventory Search

| Step | Actor | Action | Tool |
|------|-------|--------|------|
| 1 | Salesperson | Open Excel file | Excel |
| 2 | Salesperson | Scroll or filter to find serial number or model | Excel |

**Pain points:** Slow under customer pressure; filter errors; file may be locked by another user; no unified view across locations without manual filtering.

### 7.4 Sales Process

| Step | Actor | Action | Tool |
|------|-------|--------|------|
| 1 | Salesperson | Customer selects laptop | — |
| 2 | Salesperson | Verify availability in Excel | Excel |
| 3 | Salesperson | Complete billing in Tally ERP 9 | Tally |
| 4 | Salesperson/Admin | Find Excel row for sold laptop | Excel |
| 5 | Salesperson/Admin | Mark row as sold; enter customer details and invoice information | Excel |

**Pain points:** Gap between Tally sale and Excel update; sold laptop may appear available during gap; duplicate effort; customer and invoice data duplicated outside Tally.

### 7.5 Reporting and Export

| Step | Actor | Action | Tool |
|------|-------|--------|------|
| 1 | Admin/Owner | Manually filter and copy Excel data for reports | Excel |

**Pain points:** No standardized reports; time-consuming; error-prone.

### 7.6 Manual Work Summary

- Every new laptop: manual Excel row creation
- Every sale: manual Excel row update after Tally
- Every transfer: manual location field edit
- Every lookup: manual Excel search
- Every report: manual Excel manipulation

### 7.7 Risks of Current Process

| Risk | Severity |
|------|----------|
| Selling a laptop already sold in Tally but not yet marked in Excel | **High** |
| Duplicate serial numbers in Excel | **High** |
| Lost or corrupted Excel file | **High** |
| Untraceable inventory changes | **Medium** |
| Staff bypassing Excel during busy periods | **Medium** |
| Concurrent edit conflicts in Excel | **Medium** |
| No backup or version control discipline | **Medium** |

---

## 8. Proposed Workflow

The following workflows describe the target state for Version 1. Integration timing, triggers, and UI details marked **TBD** will be defined in functional and integration specifications.

### 8.1 Inventory Addition

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | Admin/Warehouse staff | Opens Add Inventory in WEBSTUDIO IMS (Desktop or Android) |
| 2 | Staff | Enters Brand, Model Number, Serial Number, **Color**, Current Location (Product Model carries specifications) |
| 3 | System | Validates serial number uniqueness via Backend API |
| 4 | System | Persists record in PostgreSQL via Backend API with lifecycle state **Received** or **Available** (**TBD** — default on add) |
| 5 | Staff | May scan serial number via barcode scanner — field auto-focused on open | See [Section 14](#14-barcode-scanner-business-behaviour) |
| 6 | System | Creates audit log entry |
| 7 | System | Queues Excel synchronization (**schedule TBD**) |

**Business rule:** Serial number must be globally unique. Model number may repeat across units. New units enter at **Received** or **Available** per business policy (**TBD**).

### 8.2 Inventory Movement

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | Admin/Staff | Initiates movement: select laptop (by serial search), select destination location |
| 2 | System | Validates laptop exists, is movable, and destination is valid (see [Section 9.3](#93-allowed-transitions--version-1)) |
| 3 | System | Creates audit log entry with actor, timestamp, source location, destination location, and optional reason |
| 4 | System | Updates `current_location_id` in PostgreSQL via Backend API |
| 5 | System | Queues Excel synchronization |

**Business rule:** Every laptop has exactly one current location at any time.

### 8.3 Inventory Search

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | Any authorized user | Enters serial number, model number, brand, color, product-specification terms (processor, GPU, RAM, storage via Product Model), location, or status — alone or in combination |
| 2 | System | Returns matching laptops with current location, product specifications (from Product Model), color, status, and serial number |
| 3 | User | Views detail, expands model group, or initiates action (movement, sale reflection) |

**Design priority:** Search is accessible from every primary screen. Search must feel instant — see [Performance Goals in PROJECT_BIBLE](../PROJECT_BIBLE.md#15-performance-goals).

### 8.4 Sales (Tally-Driven)

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | Salesperson | Customer selects laptop; salesperson verifies availability via search |
| 2 | Salesperson | Completes billing in **Tally ERP 9** (unchanged) |
| 3 | System | Tally Sync reads invoices from Tally — **IMS never creates invoices in Tally** |
| 4 | System | Processes each invoice line per [§8.6.1](#861-invoice-line-processing) |
| 5 | System | On exact **serial number** match in **`available`** inventory — marks inventory **Sold**, creates sale record, writes audit log; then verifies product model (informational — see §8.6.1) |
| 6 | System | Queues Excel synchronization |

> **Critical:** Tally remains the **billing system**. WEBSTUDIO IMS is the **inventory system**. IMS **reads** invoices from Tally only. IMS **never** creates invoices, credit notes, or billing entries inside Tally.

Manual mark-as-sold when Tally sync is delayed or unavailable: [§8.6.2](#862-manual-mark-as-sold) — **Admin and Main Admin only**.

### 8.5 Excel Synchronization

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | System | On schedule or trigger (**TBD**), exports current inventory state from PostgreSQL via Backend API |
| 2 | System | Writes synchronized representation to Excel file (**format TBD** — must preserve business-recognizable columns) |
| 3 | System | Logs sync result (success, failure, record count, timestamp) |

**Direction:** PostgreSQL → Excel (authoritative to derived). Excel must not drive inventory state.

### 8.6 Tally Synchronization

> **Architecture status:** **Frozen** — see [docs/integrations/tally-erp9/sync-strategy.md](../integrations/tally-erp9/sync-strategy.md).

**Direction:** Tally → WEBSTUDIO IMS (read invoices; reflect sales in inventory). Tally is the **primary source of truth for sales**. WEBSTUDIO IMS **does not write** billing data to Tally.

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | System | On configurable interval (default **30 minutes**), Tally Sync reads new/changed invoices from Tally ERP 9 |
| 2 | System | Processes each configured **Tally company** independently — failure in one company does not stop others |
| 3 | System | For each invoice, checks **invoice-level idempotency** (Tally voucher GUID) — skips already-processed invoices entirely |
| 4 | System | For each **new** invoice, processes every line **independently** per [§8.6.1](#861-invoice-line-processing) |
| 5 | System | Writes **Tally Sync Log** per invoice (statistics and overall result) — not Audit Log |
| 6 | System | Updates per-company sync state: `last_successful_sync_time`, `last_processed_voucher_identifier` |
| 7 | System | Creates [notifications](#notification-center-tally) where required |
| 8 | Admin / Main Admin | May trigger **Sync Now** from Tally Synchronization Dashboard |
| 9 | Admin / Main Admin | Reviews dashboard: connection status, companies, last sync, sync log, pending notifications, last error |

#### Multi-Company Support

| Tally Company (initial) | Notes |
|-------------------------|-------|
| **WEBSTUDIO** | Multi-brand store billing company |
| **ASUS Exclusive Store** | ASUS exclusive store billing company |

Each company maintains **independent** synchronization state. A failure synchronizing one company must **never** block synchronization of another.

#### Tally Synchronization Dashboard

| Element | Description |
|---------|-------------|
| **Connection Status** | Reachability of Tally ERP 9 from server |
| **Configured Companies** | List of Tally companies under sync |
| **Last Successful Sync** | Per company and aggregate |
| **Next Scheduled Sync** | Based on configured interval |
| **Pending Notifications** | Count of unresolved Tally-related notifications |
| **Last Error** | Most recent integration error (if any) |
| **Sync Now** | Manual trigger — Admin and Main Admin |

#### Notification Center (Tally)

Tally-related notifications appear in the **Notification Center** with lifecycle states: **Unread**, **Read**, **Resolved** (resolved records retained permanently).

| Notification Type | Enum | Trigger |
|-------------------|------|---------|
| **Duplicate Sale Detected** | `duplicate_sale` | Serial already **sold** in IMS when Tally line processed |
| **Serial Number Missing** | `serial_number_missing` | Product model exists in IMS; serial from line not found |
| **Product Model Missing** | `product_model_missing` | Serial exists in IMS (non-available path); invoice product model not in catalog |
| **Product Model Mismatch** | `product_model_mismatch` | Serial matched available inventory and sold; normalized invoice model genuinely differs from IMS |
| **Tally Sync Completed** | `tally_sync_completed` | Invoice or sync cycle completed successfully |
| **Synchronization Failure** | `sync_failure` | Company-level or connection-level sync failure |

**Duplicate Sale notification** includes at minimum: invoice number, voucher type, customer name, serial number, product model (if available), detection time, and descriptive message.

**Do not** generate notifications for ignored accessory/non-laptop invoice lines (see §8.6.1).

#### Tally Sync Log

Synchronization execution history is recorded in **`tally_sync_logs`** (one row per attempt): sync run ID, invoice number, voucher GUID, start/end time, processing duration, processing status, item counts, retry count, error details. References `tally_processed_invoice` where applicable. **Not** stored in the Audit Log.

Invoice state is tracked separately in **`tally_processed_invoices`** with processing status SUCCESS / PARTIAL_SUCCESS / FAILED.

#### Version 1 Exclusions (Tally)

The following are **out of scope** for Version 1 Tally integration:

- Returns, refunds, credit notes, invoice cancellation
- Automatic inventory creation from Tally
- Fuzzy or partial serial matching — **exact serial match only**

### 8.6.1 Invoice Line Processing

Every invoice line from a **new** (not yet processed) Tally invoice is evaluated **independently**. A failure on one line must **never** stop processing of remaining lines.

**Matching priority:** (1) **Serial Number** — authoritative; (2) **Product Model** — verification only after sale. Product model names **must never** prevent marking inventory sold when serial matches **`available`** inventory.

For every serial number extracted from the line:

| Step | Condition | System Action |
|------|-----------|---------------|
| 1 | Serial found in **`available`** inventory | Mark **Sold**; create `sale` (`sale_source = tally`); write **Audit Log** — **regardless of product model text** |
| 1a | After step 1 — normalized invoice model **genuinely differs** from IMS | **`product_model_mismatch`** notification (informational); sale **not** reversed |
| 2 | Serial found in **`sold`** inventory | **Duplicate Sale Detected** notification; **no** inventory change; **no** audit entry |
| 3 | Product model **exists** in IMS; serial **not found** | **Serial Number Missing** notification |
| 4 | Serial **exists** in IMS (non-available); invoice product model **not in catalog** | **Product Model Missing** notification |
| 5 | **Neither** serial nor product model in IMS | **Ignore** — accessory, software, service; **no notification** |

**Model normalization:** Minor naming differences between Tally and IMS (e.g., `ASUS Vivobook X1502ZA-EJ745WS` vs `X1502ZA-EJ745WS`) are normal and **must not** generate notifications. See [sync-strategy.md §3.3](../integrations/tally-erp9/sync-strategy.md).

Multiple inventory items on one invoice share invoice number, sale date, and customer information; each line is processed independently.

### 8.6.2 Invoice Processing Status and Retry

Each invoice is tracked in `tally_processed_invoices` with `processing_status`:

| Status | Behaviour |
|--------|-----------|
| **SUCCESS** | All inventory-related lines complete — future syncs skip (log: SKIPPED) |
| **PARTIAL_SUCCESS** | Some lines completed; failed lines retried — invoice **not** fully processed |
| **FAILED** | No inventory updates — full invoice retry |
| **SKIPPED** | Log-only — invoice already SUCCESS |

**Completion rule:** Never mark SUCCESS until all inventory-related lines finish.

**Partial retry:** On PARTIAL_SUCCESS, only failed lines are reprocessed. Completed lines are never processed again.

**Crash recovery:** After interruption, SUCCESS invoices skip; PARTIAL_SUCCESS resumes failed lines; FAILED retries entire invoice.

### 8.6.3 Line-Level Transactions

Each inventory item is processed in an **independent transaction**. One failed line never rolls back successfully processed lines from the same invoice.

### 8.6.4 Manual Mark as Sold

When Tally synchronization is unavailable or delayed, **Admin** and **Main Admin** may manually mark inventory as **Sold**. **Salesperson cannot** manually mark as sold.

| Field | Required | Notes |
|-------|----------|-------|
| **Invoice Number** | Yes | Links manual sale to Tally billing reference |
| **Customer Name** | No | Reference copy only — Tally remains billing authority |
| **Payment Mode** | No | e.g., Cash, UPI, Card — reference only |
| **Sale Date** | No | Defaults to current date/time if omitted |

System creates sale record (`sale_source = manual`), updates inventory to **Sold**, and writes audit log. If Tally sync later processes an invoice containing the same serial already sold, duplicate detection applies (§8.6.1 step 2).

### 8.7 Server Installation & First-Time Setup

Applies to the **Dedicated Server PC** only. The server is installed once per business deployment.

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | Installer / Main Admin (future) | Installs PostgreSQL, Backend API, and sync workers per deployment runbook |
| 2 | System | Runs database migrations; seeds reference data (brands, locations) and `system_initialized = false` |
| 3 | System | Backend checks `system_initialized` — **not** whether a Main Admin user exists |
| 4 | First connected client | If `system_initialized = false`, launches **First-Time Setup Wizard** |
| 5 | Operator | Enters Company Name, Main Admin Name, Username, Password, Confirm Password |
| 6 | System | Validates input; stores password only as **bcrypt** hash |
| 7 | System | Creates Main Admin user; sets `system_initialized = true` and persists `company_name` |
| 8 | System | Setup wizard does not appear again unless database is intentionally reinitialized |

### 8.8 Client Installation & Server Connection

Applies to **Desktop and Android clients**. Client installations **never create users**.

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | Staff | Installs client application (.msi, .dmg, or .apk) |
| 2 | Client | On first launch, attempts **automatic server discovery** on the LAN |
| 3a | Client | If **one** server is found — displays server information; asks for confirmation |
| 3b | Client | If **multiple** servers are found — presents selection list |
| 3c | Client | If discovery **fails** — automatically switches to **Manual Server Configuration** |
| 4 | Staff (manual path) | Enters Server HTTPS URL; uses **Test Connection**; **Save Configuration** |
| 5 | Client | Persists server URL locally only — no business data stored on device |

**Future:** Discovery may use mDNS / Bonjour or equivalent LAN protocol — **TBD**.

### 8.9 Post-Connection Login Flow

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | Client | Calls Backend `GET /api/v1/setup/status` |
| 2a | System | If `system_initialized = true` — client shows **Login** screen |
| 2b | System | If `system_initialized = false` — client launches **First-Time Setup Wizard** (see §8.7) |
| 3 | User | Authenticates with username and password against Backend only |
| 4 | System | Issues tokens; user proceeds to authorized inventory operations |

### 8.10 User Management

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | Main Admin | Creates user accounts |
| 2 | Main Admin | Disables user accounts |
| 3 | Main Admin | Resets user passwords |
| 4 | Main Admin | Assigns role: Main Admin, Admin, or Salesperson |
| 5 | System | Enforces role permissions on all operations via Backend API |

**Rule:** Only **Main Admin** may perform user management. Clients never create or store user accounts locally.

### 8.11 Exports and Reports

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | Admin/Main Admin | Selects report type or export format (**types TBD**) |
| 2 | System | Generates report from PostgreSQL via Backend API |
| 3 | User | Downloads or views export |

---

## 9. Inventory Lifecycle

Every laptop in WEBSTUDIO IMS exists in exactly one lifecycle state at any time. Lifecycle state is a business concept — not a UI label alone — and will become the foundation for backend validation and database design in downstream specifications.

### 9.1 Version 1 States (Mandatory)

| State | Meaning | Typical Trigger | Who Can Set |
|-------|---------|-----------------|-------------|
| **Received** | Laptop registered in the system but not yet available for sale — e.g., pending verification, labeling, or godown intake processing | New stock entered via Add Inventory; initial receipt at godown | Admin, Main Admin |
| **Available** | Laptop is in active inventory and may be sold or moved | Receipt confirmed; returned to sellable stock (**Future**) | Admin, Main Admin |
| **Reserved** | Laptop held for a customer but not yet billed | Customer hold placed on available stock | Admin, Main Admin |
| **Sold** | Laptop has been billed and is no longer available inventory | Tally sync (System); manual mark-as-sold (Admin, Main Admin) | System (Tally sync), Admin, Main Admin |

**Default flow for new stock:** Received → Available (when Admin confirms unit is ready for sale).

**Sale flow:** Available → Sold.

### 9.2 Future States (Not Version 1)

| State | Meaning | Planned Version |
|-------|---------|-----------------|
| **Returned** | Laptop returned after sale; re-entry to inventory workflow | **Future** — TBD |
| **Under Service** | Laptop with service center for repair or warranty work | **Future** — Version 2+ |
| **Disposed** | Laptop written off, damaged beyond sale, or removed from active inventory permanently | **Future** — TBD |

### 9.3 Allowed Transitions — Version 1

| From | To | Allowed | Actor | Condition |
|------|-----|---------|-------|-----------|
| — | Received | ✓ | Admin, Main Admin | New inventory addition |
| Received | Available | ✓ | Admin, Main Admin | Unit verified ready for sale |
| Available | Reserved | ✓ | Admin, Main Admin | Customer hold |
| Reserved | Available | ✓ | Admin, Main Admin | Hold released |
| Received | Sold | — | — | **Not allowed** — must pass through Available |
| Available | Sold | ✓ | System (Tally sync), Admin, Main Admin | Tally invoice match or manual mark-as-sold |
| Reserved | Sold | ✓ | System (Tally sync), Admin, Main Admin | Tally invoice match or manual mark-as-sold |
| Available | Received | — | — | **Not allowed** — use movement, not state reversal |
| Sold | Available | — | — | **Future** — Returns (Version 2+) |
| Sold | Any | — | — | Sold is terminal in Version 1 |

### 9.4 Lifecycle Rules

| ID | Rule |
|----|------|
| LC-01 | Every laptop has exactly one current lifecycle state |
| LC-02 | Lifecycle state changes are recorded in audit history |
| LC-03 | Movement between locations does not change lifecycle state — only current location changes |
| LC-04 | Sold laptops cannot be moved between locations in Version 1 |
| LC-05 | Lifecycle transitions are enforced in the Backend API — not by clients |

---

## 10. Inventory Entity Definition

### 10.1 What One Inventory Record Represents

**One inventory record represents one physical laptop.**

WEBSTUDIO IMS does not track abstract quantities. It tracks individual machines. When the business says "we have five ASUS Vivobook XYZ laptops," the system holds five distinct inventory records — each with its own serial number — not one record with quantity five.

### 10.2 Required Attributes Per Inventory Record

Each laptop inventory record must maintain:

| Attribute | Cardinality | Business Rule |
|-----------|-------------|---------------|
| **Serial Number** | Exactly one; globally unique | Primary identity — see BR-01; editable by authorized users with uniqueness enforced |
| **Model Number** | Exactly one; may repeat across records | Product SKU — groups units for presentation; links to Product Model |
| **Brand** | Exactly one | Required; links to brand reference via Product Model |
| **Product Specifications** | Via Product Model | CPU, GPU, RAM, storage — structured on Product Model, not duplicated per unit |
| **Color** | Exactly one | Per-unit chassis/finish color — **not** a Product Model attribute; see [§10.4](#104-color-attribute) |
| **Current Location** | Exactly one | Stored as `current_location_id`; updated on transfer — no separate movement table |
| **Current Status** | Exactly one | Lifecycle state — see [Section 9](#9-inventory-lifecycle) |
| **Audit History** | Complete; append-only | Sole source of truth for every create, update, location change, and status change |

Optional attributes (customer details, invoice reference on sold units) are defined in FR-INV-09 and FR-SLS-02.

### 10.3 Why Serial Number — Not Model Number — Is Primary

| Factor | Serial Number | Model Number |
|--------|---------------|--------------|
| **Uniqueness** | Globally unique — one per physical machine | Repeats across many machines |
| **Sale tracking** | Identifies the exact unit sold | Identifies product type only |
| **Audit** | Enables per-unit traceability | Cannot distinguish individual units |
| **Movement** | Tracks where this specific machine is | Cannot track individual machine location |
| **Tally alignment** | Maps to the specific item billed | Insufficient for serial-tracked retail |

Model Number is essential for **grouping, search, and stock counts**. Serial Number is essential for **identity, sale, movement, and audit**. Both are required. Serial Number is the authoritative identifier when any operation targets a single laptop.

### 10.4 Color Attribute

**Color is a mandatory attribute of each individual inventory unit** — not of Product Model.

| Rule | Detail |
|------|--------|
| **Scope** | One color per serial-numbered laptop |
| **Why per-unit** | The same model number may be stocked in multiple colors (e.g., Black, Silver, Blue, White, Grey) |
| **Examples** | Black, Silver, Blue, White, Grey — business may add values; not hardcoded |
| **Search** | Color must be fully searchable and filterable (FR-SRH-13) |
| **Excel export** | Included in synchronized spreadsheet (FR-XLS-03) |

Color is captured at inventory registration and may be updated by authorized roles with audit.

### 10.5 Version 1 Excluded Inventory Fields

The following fields are **intentionally excluded from Version 1** to keep the product focused on inventory management:

| Field | Status |
|-------|--------|
| **Purchase Date** | **Excluded V1** — may be introduced in a future version |
| **Purchase Cost** | **Excluded V1** — may be introduced in a future version |
| **Remarks** | **Excluded V1** — may be introduced in a future version |

Do not design database columns, API fields, or UI inputs for these attributes in Version 1.

### 10.6 Operational Ownership Fields

Version 1 business entities store **operational ownership** only — who created and last updated each record. The backend sets these automatically from the authenticated user; clients do not supply them.

| Field | Purpose |
|-------|---------|
| `created_by_user_id` | User who created the record |
| `updated_by_user_id` | User who last modified the record |

**Applies to:** Brand, Location, Product Model, Inventory Item, and other mutable business tables as defined in DATABASE_DESIGN.

**Implementation order:** Ownership columns are added in migration `0008_ownership_columns` after `0007_users_authentication` — see [DATABASE_DESIGN §16.5](../database/DATABASE_DESIGN.md#165-implementation-order-recommended).

**Excluded Version 1 action-specific fields** (use Audit Log instead):

| Field | Status |
|-------|--------|
| `sold_by_user_id` | **Excluded** — sale actor captured in `sale.recorded_by_user_id` (manual) or audit; not on inventory item |
| `reserved_by_user_id` | **Excluded** |
| `approved_by_user_id` | **Excluded** |

**Design principle:** Business entities hold current state (`current_location_id`, lifecycle status) and operational ownership (`created_by`, `updated_by`). The Audit Log is the sole persistent history for every significant action — location transfers, lifecycle transitions, and field-level changes — with no separate movement table.

---

## 11. Inventory Presentation Rules

These rules define how inventory information must be organized for users. They are **business presentation requirements** — not UI design specifications. UI/UX design must satisfy these rules in downstream design documents.

### 11.1 Primary Grouping: Model Number

The inventory list must be **primarily grouped by Model Number** (within Brand). Users browsing stock think in product lines first — "how many Vivobook XYZ do we have?" — not in serial number order.

**Example structure:**

```
ASUS Vivobook XYZ
  Available Units: 5
  [Expand]
    Serial Number: SN-001  |  Color: Black  |  Specs: i7 / 16GB / 512GB SSD / RTX 4060  |  Location: ASUS Exclusive Store
    Serial Number: SN-002  |  Color: Silver |  Specs: i7 / 16GB / 1TB SSD / RTX 4060   |  Location: Warehouse / Godown
    Serial Number: SN-003  |  Color: Blue   |  Specs: i5 / 8GB / 512GB SSD              |  Location: WEBSTUDIO Multi-brand Store
    ...
```

### 11.2 Presentation Requirements

| ID | Rule |
|----|------|
| PR-01 | Inventory list is grouped by **Brand**, then **Model Number** |
| PR-02 | Each model group displays **count of available units** prominently |
| PR-03 | Individual serial numbers are visible on **expand** — not hidden, but not default clutter |
| PR-04 | Each expanded serial row shows **Color**, **Product Specifications** (from Product Model), and **Current Location** at minimum |
| PR-05 | Each expanded serial row shows **Current Status** (Received, Available, Reserved, Sold) |
| PR-06 | Sold units may appear in model group with distinct status indicator or in separate sold view — **TBD** with business owner |
| PR-07 | Group counts reflect **Available** status units unless user explicitly filters otherwise |
| PR-08 | Search results may bypass grouping and show flat serial list when search specificity warrants it |

### 11.3 Rationale

Retail staff ask "do we have this model?" before "what is the serial number?" Model-first presentation matches the sales conversation. Serial-level detail remains one expand away for verification, movement, and sale confirmation.

---

## 12. Data Relationships

This section defines conceptual business relationships between domain entities. It is **not** a database schema. It clarifies how business objects relate before architecture and database design begin.

### 12.1 Inventory Domain

```
Brand
  └── has many → Product Models (model number within brand)
        └── has many → Inventory Units (one physical laptop each)
              └── may have one → Sales Record (when Sold)
              └── has many → Audit Log Entries (all changes — location, status, lifecycle, field updates)
```

| Relationship | Description |
|--------------|-------------|
| **Brand → Product Model** | Every product model belongs to one brand. A brand has many product models. |
| **Product Model → Inventory Unit** | Many laptops share a product model. Units differ by serial number and color; specifications live on the Product Model. |
| **Brand → Inventory Unit** | Every laptop belongs to one brand (via product model). |
| **Inventory Unit → Sales Record** | When sold, a laptop has one associated sales record with customer and invoice reference. |
| **Inventory Unit → Audit Log** | Every mutation on the unit — including location transfers — produces an audit entry; audit log is the sole history store. |

### 12.2 Product Model Lifecycle

Product Models have a lifecycle distinct from inventory unit lifecycle.

#### States

| State | Meaning |
|-------|---------|
| **Active** | Available for new inventory registration and visible in normal Admin workflows |
| **Archived** | Retired from active use — hidden from inventory creation and Salesperson default views |

#### Rules

| ID | Rule |
|----|------|
| PM-01 | Main Admin may **Archive** an Active Product Model |
| PM-02 | Main Admin may **Restore** an Archived Product Model to Active |
| PM-03 | Archived Product Models remain linked to existing inventory, sales, and audit history |
| PM-04 | Archived Product Models are **hidden from inventory creation** model selectors |
| PM-05 | Archived Product Models are **hidden from Salesperson views by default** (Admin/Main Admin may include via filter) |
| PM-06 | **Permanent deletion** removes the Product Model and cascades deletion of its Inventory Items. Sale records, reports, and audit history remain via denormalized sale snapshots |
| PM-07 | Deleting a Product Model must not delete Sale rows; historical identity is retained in `snapshot_*` fields even after inventory units are removed |

### 12.3 Operational Domain

```
User
  └── performs → Inventory Addition
  └── performs → Location Transfer (updates current_location_id; history in Audit Log)
  └── performs → Status Change
  └── triggers (via action) → Audit Log Entry
```

| Relationship | Description |
|--------------|-------------|
| **User → Location Transfer** | Every location change records the acting user in audit log. |
| **User → Audit Log** | Every auditable action records the acting user. |
| **Location Transfer → Audit Log** | Location change produces an audit entry with from/to locations — no separate movement record. |
| **Status Change → Audit Log** | Lifecycle transition produces an audit entry. |
| **Status Change → Sales Record** | Transition to Sold creates or links a sales record. |

### 12.4 Reference Domain

```
Location
  └── has many → Inventory Units (at current location)

Brand (reference list)
  └── has many → Product Models
        └── referenced by → Inventory Units
```

### 12.5 Integration Domain (Conceptual)

```
Tally ERP 9 (external)
  └── billing event → triggers → Status Change (Available → Sold) in WEBSTUDIO IMS

Excel (external, derived)
  └── receives export ← synchronized from → WEBSTUDIO IMS inventory state
```

**Rule:** WEBSTUDIO IMS owns inventory relationships. Tally owns billing. Excel holds a derived copy — never a peer relationship.

---

## 13. Dashboard Requirements

The dashboard is the **default landing view** after login. It is an **operational inventory dashboard** — not a business analytics or BI dashboard. Its purpose is to help employees start working immediately.

### 13.1 Dashboard Components — Version 1 (Mandatory)

| ID | Component | Business Purpose |
|----|-----------|------------------|
| DR-01 | **Total Available Stock** | Count of laptops in Available status across all locations |
| DR-02 | **Total Sold Stock** | Count of laptops in Sold status — period filter **TBD** (all time vs. today vs. month) |
| DR-03 | **Brand Summary** | Available unit count broken down by brand |
| DR-04 | **Location Summary** | Available unit count broken down by location |
| DR-05 | **Quick Search** | Prominent search entry — same search capability as global search |
| DR-06 | **Recently Updated Inventory** | List of most recently added, moved, or status-changed laptops — count **TBD** |

### 13.2 Dashboard Rules

| ID | Rule |
|----|------|
| DR-R01 | Dashboard loads without requiring navigation — it is the starting point |
| DR-R02 | Dashboard figures reflect live PostgreSQL data via Backend API |
| DR-R03 | Dashboard contains **no advanced charts, trend graphs, or BI analytics** in Version 1 |
| DR-R04 | Dashboard search uses the same search engine as global search — see [Section 15.7](#157-search) |
| DR-R05 | Clicking a dashboard summary item navigates to filtered inventory list — detail behavior **TBD** in UI spec |
| DR-R06 | Salesperson sees dashboard components appropriate to role — write access not required to view counts |

### 13.3 Explicitly Excluded from Dashboard (Version 1)

- Revenue or billing analytics (Tally domain)
- Profit margins or accounting summaries
- Customer analytics or CRM metrics
- Predictive forecasting or AI insights
- Customizable widget layouts (**Future** — TBD)

---

## 14. Barcode Scanner Business Behaviour

This section defines business expectations for barcode scanner use. It is **not** a hardware specification. Hardware compatibility details are **TBD** in research documentation.

### 14.1 Core Behaviour

| ID | Rule |
|----|------|
| BC-01 | Barcode scanners are treated as **keyboard input devices** (keyboard wedge mode) — no special driver required for Version 1 |
| BC-02 | Both **wired USB** and **wireless** barcode scanners are supported without changing the inventory workflow |
| BC-03 | Scanning populates the **Serial Number** field — the scanner reads the serial number barcode |

### 14.2 Add Inventory Workflow

| Step | Expected Behaviour |
|------|-------------------|
| 1 | When Add Inventory is opened, cursor **automatically focuses** the Serial Number field |
| 2 | User scans barcode → serial number **immediately populates** the field |
| 3 | If configured by Main Admin, scanner **Enter key automatically submits** the serial field and advances to next field (**TBD** — configurable) |
| 4 | User completes remaining fields: Brand, Model Number, **Color**, Location (Product Model selected or created with specifications) |
| 5 | System validates serial uniqueness and saves |

### 14.3 Search Workflow

| Step | Expected Behaviour |
|------|-------------------|
| 1 | When search is focused, scanning populates search with serial number |
| 2 | System executes search immediately on scan complete (Enter or auto-submit **TBD**) |
| 3 | Matching laptop detail is displayed |

### 14.4 Business Rules

| ID | Rule |
|----|------|
| BC-04 | Barcode scanning does not bypass Backend API validation |
| BC-05 | Duplicate serial scan on add shows clear error — same as manual entry |
| BC-06 | Scanner behaviour is identical on Windows Desktop and macOS Desktop — Android **TBD** |
| BC-07 | If barcode is unreadable, manual serial entry remains available — scanner is optional convenience |

---

## 15. Functional Requirements

Requirements use the prefix **FR-** for traceability. **Mandatory** requirements must be delivered in Version 1. **Future** requirements are noted explicitly.

### 15.0 Server Setup & Client Onboarding

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-INIT-01 | Backend shall determine initialization from `system_initialized` in `system_settings` — **not** from Main Admin user existence | Mandatory | See BR-28 |
| FR-INIT-02 | Fresh deployment shall seed `system_initialized = false` and shall **not** seed a Main Admin user | Mandatory | Reference data only in migrations |
| FR-INIT-03 | When `system_initialized = false`, system shall expose First-Time Setup Wizard collecting Company Name, Main Admin Name, Username, Password, Confirm Password | Mandatory | Any connected client after server install |
| FR-INIT-04 | Setup shall store passwords only as bcrypt hashes on the server | Mandatory | See BR-30 |
| FR-INIT-05 | Successful setup shall create Main Admin, set `system_initialized = true`, and persist `company_name` | Mandatory | Wizard must not reappear unless DB reinitialized |
| FR-INIT-06 | Backend shall expose `GET /api/v1/setup/status` returning initialization state | Mandatory | Callable without authentication when not initialized |
| FR-INIT-07 | Backend shall expose `POST /api/v1/setup/initialize` accepting setup wizard payload when `system_initialized = false` | Mandatory | Rejected with conflict when already initialized |
| FR-CLIENT-01 | Client installations shall **never** create users | Mandatory | See BR-29 |
| FR-CLIENT-02 | Client first launch shall attempt automatic server discovery on LAN | Mandatory | |
| FR-CLIENT-03 | Client shall confirm single discovered server or let user select among multiple | Mandatory | |
| FR-CLIENT-04 | Client shall fall back to Manual Server Configuration (HTTPS URL, Test Connection, Save) when discovery fails | Mandatory | |
| FR-CLIENT-05 | After server connection, client shall call setup status before showing Login or Setup Wizard | Mandatory | See §8.9 |
| FR-CLIENT-06 | Clients shall not persist business data locally in Version 1 | Mandatory | Server URL, tokens, theme, layout only — see BR-31 |
| FR-CLIENT-07 | Automatic server discovery may use mDNS / Bonjour or equivalent | Future | Workflow defined V1; protocol **TBD** |

### 15.1 Authentication

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-AUTH-01 | System shall require authentication before any inventory operation | Mandatory | Via Backend API |
| FR-AUTH-02 | System shall support secure login for all platforms (Windows, macOS, Android) | Mandatory | Username/password; login blocked until `system_initialized = true` |
| FR-AUTH-03 | System shall terminate inactive sessions after configurable timeout | Mandatory | Default **TBD** |
| FR-AUTH-04 | System shall lock account after configurable failed login attempts | Mandatory | Threshold **TBD** |
| FR-AUTH-05 | System shall support password change by user and reset by Main Admin | Mandatory | |
| FR-AUTH-06 | System shall support multi-factor authentication | Future | Version 2+ **TBD** |

### 15.2 User Management

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-USER-01 | Main Admin shall create, disable, reset passwords for, and assign roles to user accounts | Mandatory | Only Main Admin — see §8.10 |
| FR-USER-02 | Main Admin shall assign one role per user: Main Admin, Admin, or Salesperson | Mandatory | |
| FR-USER-03 | System shall prevent deactivation of the last Main Admin account | Mandatory | |
| FR-USER-04 | System shall record user management actions in audit log | Mandatory | |
| FR-USER-05 | Main Admin shall view list of all users with role and status | Mandatory | |
| FR-USER-06 | Admin shall view list of users at their location | Future | **TBD** — location-scoped admin |

### 15.3 Inventory Management

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-INV-01 | System shall register laptops with Brand, Model Number, Serial Number, **Color**, and Current Location — specifications via linked Product Model | Mandatory | One record = one physical laptop — see [Section 10](#10-inventory-entity-definition) |
| FR-INV-02 | System shall treat Serial Number as the globally unique identifier for each laptop; authorized users may edit serial numbers with uniqueness always enforced | Mandatory | See BR-01 |
| FR-INV-03 | System shall allow Model Number to repeat across multiple laptops | Mandatory | See BR-02 |
| FR-INV-04 | System shall enforce exactly one current location per laptop (`current_location_id`) | Mandatory | See BR-03; location change history in audit log |
| FR-INV-05 | System shall support lifecycle states: **Received**, **Available**, **Reserved**, **Sold** in Version 1 | Mandatory | See [Section 9](#9-inventory-lifecycle) |
| FR-INV-06 | System shall allow editing of laptop attributes (including serial number) by authorized roles | Mandatory | Permission matrix in [Section 17](#17-user-roles-and-permissions) |
| FR-INV-07 | System shall allow permanent deletion of an inventory record only when status is not **Sold** and no sale or audit references exist | Mandatory | See DATABASE_DESIGN §4.6 |
| FR-INV-08 | System shall restrict Version 1 inventory to **laptops only** | Mandatory | See BR-10 |
| FR-INV-09 | System shall store sale-related fields: customer details and invoice reference (**field list TBD**) | Mandatory | Currently manual in Excel |
| FR-INV-10 | System shall display inventory grouped by Brand and Model Number with expandable serial units | Mandatory | See [Section 11](#11-inventory-presentation-rules), PR-01–PR-08 |
| FR-INV-11 | System shall display available unit count per model group | Mandatory | See PR-02 |
| FR-INV-12 | System shall support bulk import of inventory (**format and limits TBD**) | Future | May be required for migration |
| FR-INV-13 | System shall enforce allowed lifecycle transitions per [Section 9.3](#93-allowed-transitions--version-1) | Mandatory | Backend API enforcement |

### 15.4 Brand Management

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-BRD-01 | System shall maintain a configurable list of brands | Mandatory | Avoid hardcoded brand list |
| FR-BRD-02 | Admin and Main Admin shall add, edit, and deactivate brands | Mandatory | |
| FR-BRD-03 | System shall prevent deactivation of brands linked to active inventory | Mandatory | |
| FR-BRD-04 | Brand shall be a required field on inventory records | Mandatory | |

### 15.4.1 Product Model Management

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-PM-01 | System shall maintain Product Models as distinct entities within a Brand (model number + brand) with structured specification fields: model name, CPU, GPU (optional), RAM, and storage | Mandatory | See [§12.2](#122-product-model-lifecycle) |
| FR-PM-02 | Product Models shall have lifecycle states: **Active** and **Archived** | Mandatory | PM-01–PM-07 |
| FR-PM-03 | Main Admin shall Archive and Restore Product Models | Mandatory | |
| FR-PM-04 | System shall prevent selection of Archived Product Models during inventory creation | Mandatory | PM-04 |
| FR-PM-05 | System shall hide Archived Product Models from Salesperson default inventory views | Mandatory | PM-05; Admin filter **TBD** |
| FR-PM-06 | System shall permanently delete a Product Model and cascade-delete its Inventory Items while preserving Sale snapshots and audit history | Mandatory | PM-06, PM-07 |
| FR-PM-07 | Archived Product Models shall remain visible for historical inventory, sales, and audit context | Mandatory | |

### 15.5 Location Management

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-LOC-01 | System shall preconfigure three locations: ASUS Exclusive Store, WEBSTUDIO Multi-brand Store, Warehouse/Godown | Mandatory | Additional locations configurable |
| FR-LOC-02 | Main Admin shall add, edit, and deactivate locations | Mandatory | |
| FR-LOC-03 | System shall prevent deactivation of locations with active inventory | Mandatory | |
| FR-LOC-04 | Location shall be a required field on every inventory record | Mandatory | |

### 15.6 Inventory Movement

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-MOV-01 | Authorized users shall initiate transfer of a laptop from one location to another | Mandatory | Targets individual serial number |
| FR-MOV-02 | System shall record source location, destination location, actor, timestamp, and optional reason in audit log | Mandatory | Single source of truth for location change history — see FR-AUD-08 |
| FR-MOV-03 | System shall update `current_location_id` upon successful movement | Mandatory | Does not change lifecycle state — see LC-03 |
| FR-MOV-04 | System shall display inventory history per laptop (location changes and lifecycle events) via audit log or serial lifecycle API | Mandatory | No separate movement table |
| FR-MOV-05 | System shall support movement approval workflow | Future | **TBD** — may be required for godown transfers |
| FR-MOV-06 | System shall prevent movement of sold laptops | Mandatory | See LC-04 |

### 15.7 Search

Search is a **primary feature** of WEBSTUDIO IMS. Search must remain accessible from every primary screen including the dashboard. Search must feel extremely fast — correctness first, then speed.

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-SRH-01 | System shall provide global search accessible from all primary screens including dashboard | Mandatory | Search-first philosophy |
| FR-SRH-02 | System shall search by Serial Number with exact and partial match | Mandatory | Highest priority search field |
| FR-SRH-03 | System shall search by Model Number and Brand | Mandatory | Supports model-first browsing |
| FR-SRH-04 | System shall search by Current Location and lifecycle Status | Mandatory | |
| FR-SRH-05 | System shall search Product Model specification fields: Processor (CPU), Graphics Card (GPU), RAM, and Storage | Mandatory | Product-specification-aware search via Product Model join |
| FR-SRH-06 | Search for partial specification terms shall return all matching laptops — e.g., `4060` returns all units whose Product Model GPU matches; `i7` returns all Intel Core i7 units; `16GB` returns all 16GB RAM units | Mandatory | Case-insensitive **TBD** |
| FR-SRH-07 | System shall support **combined search criteria** — Brand, Model Number, Serial Number, specification terms (CPU/GPU/RAM/Storage via Product Model), Color, Location, and Status may be applied together | Mandatory | Multi-filter search |
| FR-SRH-08 | System shall return results within perceived instant response time | Mandatory | Numeric target **TBD** |
| FR-SRH-09 | System shall support barcode scanner input for serial number search | Mandatory | See [Section 14](#14-barcode-scanner-business-behaviour) |
| FR-SRH-10 | Search shall be keyboard-accessible on desktop platforms | Mandatory | See Design Principles in Project Bible |
| FR-SRH-11 | Search results for specific serial number shall show unit detail directly | Mandatory | |
| FR-SRH-12 | Search results for model or specification terms may show grouped or flat list — **TBD** in UI spec | Mandatory | See PR-08 |
| FR-SRH-13 | System shall search and filter by **Color** with exact and partial match | Mandatory | See [§10.4](#104-color-attribute) |

### 15.8 Sales History

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-SLS-01 | System shall record sales history when inventory status changes to Sold | Mandatory | Tally sync or manual mark-as-sold |
| FR-SLS-02 | Sales history shall include serial number, sale date/time, actor (manual only), invoice number, customer name (optional), payment mode (optional), sale source (`tally` or `manual`) | Mandatory | Invoice number required for manual sales |
| FR-SLS-03 | Authorized users shall view sales history with filter by date range, location, brand | Mandatory | |
| FR-SLS-04 | Admin and Main Admin shall manually mark inventory as Sold when Tally sync is unavailable or delayed | Mandatory | See §8.6.2 — Salesperson **excluded** |
| FR-SLS-05 | System shall not generate invoices or billing documents | Mandatory | Tally owns billing — IMS read-only |
| FR-SLS-06 | Manual and Tally sales for the same invoice and serial shall not create duplicate sale records | Mandatory | See §8.6.1 duplicate protection |

### 15.9 Excel Synchronization

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-XLS-01 | System shall synchronize inventory from PostgreSQL to Excel on a defined schedule | Mandatory | Schedule **TBD** |
| FR-XLS-02 | System shall support manual trigger of Excel sync by Main Admin | Mandatory | |
| FR-XLS-03 | Excel output shall include columns: Brand, Model Number, Serial Number, **Color**, Product Specifications (CPU, GPU, RAM, Storage from Product Model), Current Location, Status | Mandatory | Per [§10.4](#104-color-attribute) |
| FR-XLS-04 | System shall log every sync attempt with timestamp, outcome, and record count | Mandatory | |
| FR-XLS-05 | System shall surface sync failures to Main Admin | Mandatory | |
| FR-XLS-06 | Excel sync shall never write inventory changes back to PostgreSQL | Mandatory | See BR-08 |
| FR-XLS-07 | Excel sync shall operate through Backend API — never direct database access | Mandatory | Project Bible N2 |

### 15.10 Tally Integration

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-TLY-01 | System shall read invoices from Tally ERP 9 on a configurable automatic interval (default **30 minutes**) | Mandatory | IMS never writes to Tally |
| FR-TLY-02 | System shall support multiple Tally companies with independent sync state per company | Mandatory | Initial: WEBSTUDIO, ASUS Exclusive Store |
| FR-TLY-03 | Each company shall store `last_successful_sync_time` and `last_processed_voucher_identifier` | Mandatory | See DATABASE_DESIGN §4.14 |
| FR-TLY-04 | Failure synchronizing one Tally company shall not stop synchronization of other companies | Mandatory | Per-company isolation |
| FR-TLY-05 | System shall process each invoice line independently per §8.6.1 — one line failure never stops others | Mandatory | Serial-authoritative matching in **`available`** inventory only |
| FR-TLY-06 | On serial found in **available** inventory, system shall mark Sold, create sale record, and write audit log — **regardless of product model text on invoice** | Mandatory | `sale_source = tally`; serial is authoritative |
| FR-TLY-06a | After successful serial match, system shall compare normalized invoice product model with IMS product model for verification only | Mandatory | Must **never** block sale reflection |
| FR-TLY-06b | When normalized models genuinely differ after sale, system shall create **Product Model Mismatch** notification without reversing sale | Mandatory | `product_model_mismatch`; informational only |
| FR-TLY-07 | System shall ignore invoice lines where neither serial nor product model exist in IMS | Mandatory | No notification for accessories |
| FR-TLY-08 | System shall create notifications per §8.6 Notification Center | Mandatory | Duplicate Sale, Serial Number Missing, Product Model Missing, **Product Model Mismatch**, Tally Sync Completed, Sync Failure |
| FR-TLY-09 | System shall maintain Tally Sync Log per execution attempt — separate from Audit Log and invoice state | Mandatory | See §8.6 |
| FR-TLY-16 | System shall track invoice processing status SUCCESS / PARTIAL_SUCCESS / FAILED on `tally_processed_invoices` | Mandatory | SKIPPED is log-only |
| FR-TLY-17 | Duplicate sold serial shall create notification without inventory or audit mutation; line marked completed | Mandatory | Line-level |
| FR-TLY-18 | SUCCESS only when all inventory-related lines complete — never before processing finishes | Mandatory | See §8.6.2 |
| FR-TLY-19 | PARTIAL_SUCCESS shall retry failed lines only; completed lines never reprocessed | Mandatory | See §8.6.2 |
| FR-TLY-20 | Engine shall recover after crash/restart without duplicate inventory updates | Mandatory | See §8.6.2 |
| FR-TLY-21 | Each inventory line processed in independent transaction — no invoice-wide rollback | Mandatory | See §8.6.3 |
| FR-TLY-10 | Admin and Main Admin shall trigger **Sync Now** for Tally synchronization | Mandatory | |
| FR-TLY-11 | System shall provide Tally Synchronization Dashboard with connection status, configured companies, last successful sync, next scheduled sync, pending notifications, last error, and Sync Now | Mandatory | See §8.6 |
| FR-TLY-12 | System shall not replace or replicate Tally billing functionality | Mandatory | See BR-05 |
| FR-TLY-13 | Tally integration shall operate through Backend API — never direct database access | Mandatory | Project Bible N2 |
| FR-TLY-14 | System shall treat Tally-imported invoice matching an existing manual sale as the same transaction — no duplicate sale | Mandatory | See FR-SLS-06 |
| FR-TLY-15 | Version 1 shall exclude returns, refunds, credit notes, invoice cancellation, and automatic inventory creation from Tally | Mandatory | See §8.6 exclusions |

### 15.10.1 Notifications (Tally)

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-NOT-01 | Notification Center shall include Tally integration notifications | Mandatory | |
| FR-NOT-02 | System shall create Serial Number Missing notification when model exists but serial not found | Mandatory | `serial_number_missing` |
| FR-NOT-03 | System shall create Product Model Missing notification when serial exists (non-available path) but invoice model not in catalog | Mandatory | `product_model_missing` |
| FR-NOT-03a | System shall create Product Model Mismatch notification when serial matched and sold but normalized models genuinely differ | Mandatory | `product_model_mismatch`; informational; sale not reversed |
| FR-NOT-04 | System shall create Duplicate Sale Detected notification when serial already sold — no duplicate sale or audit | Mandatory | Includes invoice, voucher type, customer, serial |
| FR-NOT-05 | System shall create Synchronization Failure notification on company or connection failures | Mandatory | |
| FR-NOT-06 | System shall not create notifications for ignored non-laptop/accessory invoice lines | Mandatory | See FR-TLY-07 |
| FR-NOT-07 | Notifications shall support Unread, Read, and Resolved lifecycle states | Mandatory | Resolved retained permanently |
| FR-NOT-08 | System shall create Tally Sync Completed notification when appropriate | Mandatory | Informational |

### 15.11 Reports and Export

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-RPT-01 | System shall provide inventory summary report by location | Mandatory | |
| FR-RPT-02 | System shall provide sold inventory report by date range | Mandatory | |
| FR-RPT-03 | System shall provide movement history report sourced from audit log | Mandatory | Location changes and related audit entries |
| FR-RPT-04 | System shall export reports to Excel and PDF (**TBD**) | Mandatory | Minimum: Excel |
| FR-RPT-05 | System shall provide stock count report (available units by brand/model/location) | Mandatory | |
| FR-RPT-06 | Custom report builder | Future | Version 2+ |

### 15.12 Dashboard

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-DSH-01 | System shall display operational dashboard as default view after login | Mandatory | See [Section 13](#13-dashboard-requirements) |
| FR-DSH-02 | Dashboard shall show Total Available Stock count | Mandatory | DR-01 |
| FR-DSH-03 | Dashboard shall show Total Sold Stock count | Mandatory | DR-02 |
| FR-DSH-04 | Dashboard shall show Brand Summary with available unit counts | Mandatory | DR-03 |
| FR-DSH-05 | Dashboard shall show Location Summary with available unit counts | Mandatory | DR-04 |
| FR-DSH-06 | Dashboard shall include Quick Search with full search capability | Mandatory | DR-05 |
| FR-DSH-07 | Dashboard shall show Recently Updated Inventory list | Mandatory | DR-06 |
| FR-DSH-08 | Dashboard shall not include advanced analytics or BI charts in Version 1 | Mandatory | DR-R03 |

### 15.13 System Settings

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-SET-01 | Main Admin shall configure Excel sync schedule | Mandatory | |
| FR-SET-02 | Main Admin shall configure Tally integration connection parameters and sync interval | Mandatory | Default interval 30 minutes |
| FR-SET-03 | Main Admin shall configure session timeout and lockout thresholds | Mandatory | |
| FR-SET-04 | Main Admin shall configure application display name and business details | Mandatory | Fields **TBD** |
| FR-SET-05 | System shall support Light and Dark theme default per user or global | Mandatory | |
| FR-SET-06 | Main Admin and Admin shall view system health, integration status, and Tally Synchronization Dashboard | Mandatory | See FR-TLY-11 |
| FR-SET-07 | Main Admin shall configure barcode scanner auto-submit behaviour on Enter | Mandatory | See BC-03 — default **TBD** |

### 15.14 Audit Logs

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-AUD-01 | System shall record audit entry for every inventory create, update, status change, and movement | Mandatory | |
| FR-AUD-02 | System shall record audit entry for user management actions | Mandatory | |
| FR-AUD-03 | System shall record audit entry for settings changes | Mandatory | |
| FR-AUD-04 | Audit entry shall include: user ID, user name (optional snapshot), user role, action performed, entity type, entity ID, timestamp, previous values (where applicable), new values (where applicable), device/platform (optional), IP address (optional), reason (optional) | Mandatory | See [§10.6](#106-operational-ownership-fields) |
| FR-AUD-05 | Main Admin shall search and filter audit logs | Mandatory | |
| FR-AUD-06 | Audit logs shall be immutable — no edit or delete | Mandatory | |
| FR-AUD-07 | Audit log retention period | Mandatory | Duration **TBD** |
| FR-AUD-08 | Location-change audit entries shall record from location, to location, actor (authenticated user), and timestamp; optional reason — audit log is the sole persistent history for movements | Mandatory | Replaces separate `inventory_movements` table |
| FR-AUD-09 | Business entities shall store `created_by_user_id` and `updated_by_user_id`, set automatically by the backend from the authenticated user | Mandatory | See [§10.6](#106-operational-ownership-fields) |

### 15.15 Barcode Scanner

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-BCD-01 | System shall accept serial number input from keyboard-wedge barcode scanners | Mandatory | See [Section 14](#14-barcode-scanner-business-behaviour) |
| FR-BCD-02 | Add Inventory shall auto-focus Serial Number field on open | Mandatory | BC-02 |
| FR-BCD-03 | Scanned serial number shall populate Serial Number field immediately | Mandatory | |
| FR-BCD-04 | System shall support wired and wireless scanners without workflow change | Mandatory | BC-02 |
| FR-BCD-05 | Configurable auto-submit on scanner Enter key after serial scan | Mandatory | BC-03, FR-SET-07 |
| FR-BCD-06 | Search shall accept barcode scanner input for serial lookup | Mandatory | FR-SRH-09 |
| FR-BCD-07 | Manual serial entry shall remain available when scanner unavailable | Mandatory | BC-07 |

---

## 16. Non-Functional Requirements

### 16.1 Performance

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| NFR-PERF-01 | Serial number and product-specification search shall feel instant to the user on desktop | Mandatory | Numeric target **TBD** |
| NFR-PERF-02 | UI interactions shall not block during network requests — loading states required | Mandatory | |
| NFR-PERF-03 | Application startup shall reach usable state quickly | Mandatory | Target **TBD** |
| NFR-PERF-04 | Excel and Tally sync shall complete within acceptable window | Mandatory | Window **TBD** |
| NFR-PERF-05 | Correctness shall take precedence over speed for all inventory mutations | Mandatory | Project Bible |

### 16.2 Security

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| NFR-SEC-01 | All client-server communication shall be encrypted on the local network | Mandatory | Protocol **TBD** |
| NFR-SEC-02 | Passwords shall be stored using industry-standard hashing | Mandatory | Algorithm **TBD** in ADR |
| NFR-SEC-03 | Authorization shall be enforced on every Backend API operation | Mandatory | |
| NFR-SEC-04 | No credentials shall be stored in source code or client binaries | Mandatory | |
| NFR-SEC-05 | Role permissions shall follow least privilege | Mandatory | [Section 17](#17-user-roles-and-permissions) |
| NFR-SEC-06 | Security architecture shall be documented before release | Mandatory | [security docs](../security/README.md) |

### 16.3 Reliability

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| NFR-REL-01 | System shall recover gracefully from transient network failures between clients and server | Mandatory | |
| NFR-REL-02 | Failed sync operations shall not corrupt inventory state | Mandatory | |
| NFR-REL-03 | System shall provide clear error messages on failure — no silent failures | Mandatory | |
| NFR-REL-04 | Dedicated Server shall restart automatically on failure (**mechanism TBD**) | Mandatory | |

### 16.4 Scalability

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| NFR-SCL-01 | System shall support current business scale: three locations, one building, shared Wi-Fi | Mandatory | |
| NFR-SCL-02 | System architecture shall not prevent future multi-branch expansion | Mandatory | Design constraint only |
| NFR-SCL-03 | Maximum inventory volume for Version 1 | Mandatory | Estimate **TBD** |

### 16.5 Maintainability

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| NFR-MNT-01 | System shall be maintainable for minimum ten years | Mandatory | Project Bible |
| NFR-MNT-02 | Business rules shall exist only in Backend API | Mandatory | |
| NFR-MNT-03 | All configuration values shall be externalized — nothing hardcoded that managers may change | Mandatory | |
| NFR-MNT-04 | System shall support versioned upgrades without inventory data loss | Mandatory | |

### 16.6 Usability

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| NFR-USE-01 | Salesperson shall complete core tasks with no more than **TBD** hours of training | Mandatory | |
| NFR-USE-02 | UI shall prioritize speed and simplicity over feature density | Mandatory | |
| NFR-USE-03 | UI shall meet premium SaaS quality standard with Light and Dark themes | Mandatory | |
| NFR-USE-04 | Error messages shall be plain language actionable by retail staff | Mandatory | |
| NFR-USE-05 | Empty states, loading states, and error states shall be designed for all primary screens | Mandatory | |

### 16.7 Accessibility

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| NFR-ACC-01 | Desktop applications shall support keyboard navigation for all frequent operations | Mandatory | |
| NFR-ACC-02 | Light and Dark themes shall meet minimum contrast requirements | Mandatory | Ratio **TBD** |
| NFR-ACC-03 | Full accessibility compliance standard | Future | **TBD** |

### 16.8 Availability

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| NFR-AVL-01 | System shall be available during all business operating hours | Mandatory | Hours **TBD** |
| NFR-AVL-02 | Planned maintenance windows shall be configurable and communicated | Mandatory | |
| NFR-AVL-03 | Target uptime percentage | Mandatory | **TBD** |

### 16.9 Backup

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| NFR-BAK-01 | PostgreSQL database shall be backed up on a defined schedule | Mandatory | Schedule **TBD** |
| NFR-BAK-02 | Main Admin shall trigger manual backup | Mandatory | |
| NFR-BAK-03 | Backup retention policy | Mandatory | **TBD** |
| NFR-BAK-04 | Backup procedure shall be documented in operations runbook | Mandatory | |

### 16.10 Recovery

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| NFR-REC-01 | System shall support restore from backup without inventory data loss | Mandatory | |
| NFR-REC-02 | Recovery procedure shall be documented and tested before production | Mandatory | |
| NFR-REC-03 | Recovery time objective (RTO) | Mandatory | **TBD** |
| NFR-REC-04 | Recovery point objective (RPO) | Mandatory | **TBD** |

### 16.11 Logging

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| NFR-LOG-01 | All services shall emit structured logs | Mandatory | Schema **TBD** |
| NFR-LOG-02 | Integration events (Excel, Tally) shall be logged with correlation identifiers | Mandatory | |
| NFR-LOG-03 | Log retention period | Mandatory | **TBD** |
| NFR-LOG-04 | Main Admin shall access system logs for troubleshooting | Mandatory | Interface **TBD** |

---

## 17. User Roles and Permissions

### 17.1 Role Definitions

| Role | Description |
|------|-------------|
| **Main Admin** | Full system access. Typically one or two accounts for business owner and IT lead. |
| **Admin** | Inventory and operational management. Store managers and warehouse supervisors. |
| **Salesperson** | Front-line search, sale verification, and inventory movement. |

Future roles: **TBD**.

### 17.2 Permission Matrix

| Action | Salesperson | Admin | Main Admin |
|--------|:-----------:|:-----:|:----------:|
| Search inventory | ✓ | ✓ | ✓ |
| Add inventory | — | ✓ | ✓ |
| Edit inventory | — | ✓ | ✓ |
| Move inventory | ✓ | ✓ | ✓ |
| Delete product model | — | — | ✓ |
| Excel synchronization | — | ✓ | ✓ |
| Tally synchronization | — | ✓ | ✓ |
| Tally Sync Now | — | ✓ | ✓ |
| Manual mark as Sold | — | ✓ | ✓ |
| System settings | — | — | ✓ |

### 17.3 Detailed Capability Matrix

| Capability | Main Admin | Admin | Salesperson |
|------------|:----------:|:-----:|:-----------:|
| **Authentication** | | | |
| Login / logout | ✓ | ✓ | ✓ |
| Change own password | ✓ | ✓ | ✓ |
| **User Management** | | | |
| Create / disable users; reset passwords | ✓ | — | — |
| Assign roles | ✓ | — | — |
| View all users | ✓ | — | — |
| **Inventory** | | | |
| Add inventory | ✓ | ✓ | — |
| Edit inventory attributes | ✓ | ✓ | — |
| View inventory | ✓ | ✓ | ✓ |
| Change inventory status (sold) — manual | — | ✓ | — |
| **Movement** | | | |
| Initiate movement | ✓ | ✓ | ✓ |
| View inventory history (audit) | ✓ | ✓ | ✓ |
| **Search** | | | |
| Global search | ✓ | ✓ | ✓ |
| **Dashboard** | | | |
| View operational dashboard | ✓ | ✓ | ✓ |
| **Sales History** | | | |
| View sales history | ✓ | ✓ | ✓ |
| **Brands & Locations** | | | |
| Manage brands | ✓ | ✓ | — |
| Manage product models (archive / restore) | ✓ | — | — |
| Manage locations | ✓ | — | — |
| **Reports & Export** | | | |
| View and export reports | ✓ | ✓ | — |
| **Integrations** | | | |
| Configure Excel sync schedule | ✓ | — | — |
| Configure Tally integration | ✓ | — | — |
| Trigger manual Excel sync | ✓ | ✓ | — |
| Trigger Tally Sync Now | ✓ | ✓ | — |
| View Tally Synchronization Dashboard | ✓ | ✓ | — |
| View sync status | ✓ | ✓ | — |
| **System Settings** | | | |
| Configure all settings | ✓ | — | — |
| **Audit Logs** | | | |
| View audit logs | ✓ | — | — |
| **Backup** | | | |
| Trigger backup / restore | ✓ | — | — |

**Legend:** ✓ = permitted, — = not permitted.

---

## 18. Business Rules

Business rules are authoritative for Version 1. Implementation belongs exclusively in the Backend API per [PROJECT_BIBLE](../PROJECT_BIBLE.md).

| ID | Rule | Rationale |
|----|------|-----------|
| BR-01 | **Serial Numbers are globally unique.** No two inventory records may share the same serial number. Authorized users may edit a serial number; uniqueness is always enforced. | Prevents duplicate stock; enables reliable search and audit |
| BR-02 | **Model Numbers may repeat.** One model number may identify many laptops. | Same product SKU appears in multiple physical units |
| BR-03 | **Every laptop has exactly one current location.** A laptop cannot be in two locations simultaneously. | Physical reality; enables location-based stock counts |
| BR-04 | **Inventory movements are logged.** Every location change records actor, timestamp, source, and destination in audit log. | Audit and dispute resolution |
| BR-05 | **Tally ERP 9 is the billing system.** WEBSTUDIO IMS never generates invoices, receipts, or accounting entries. | Business constraint; Tally is entrenched and sufficient |
| BR-06 | **PostgreSQL is the single source of truth** for inventory data, accessed exclusively via Backend API. | Eliminates conflicting records |
| BR-07 | **Excel is a synchronized representation** of inventory — not authoritative. Changes in Excel do not drive inventory state. | Business continuity during transition |
| BR-08 | **Inventory changes in PostgreSQL must be reflected in synchronized Excel** on the defined sync schedule. | Business requires Excel visibility |
| BR-09 | **Every inventory mutation is auditable.** No silent updates. | Compliance and trust |
| BR-10 | **Version 1 manages laptops only.** Accessories, printers, and non-laptop categories are out of scope. | Focused Version 1 delivery |
| BR-11 | **Sold laptops cannot be sold again.** Status change to Sold prevents duplicate sale reflection. | Prevents double-sale errors |
| BR-12 | **Business rules exist once in the Backend API.** Clients display and capture; they do not enforce rules. | Consistency across platforms |
| BR-13 | **Search is a primary feature.** Search capability must not be degraded by feature additions. | Core daily operation |
| BR-14 | **Configurable over hardcoded.** Locations, brands, statuses, sync schedules, and thresholds shall be configurable by Main Admin where reasonable. | Business evolves without developer intervention |
| BR-15 | **Customer details and invoice reference** on sold records shall reference Tally billing — WEBSTUDIO IMS stores reference, not authoritative billing data. | Data ownership boundary |
| BR-16 | **One inventory record equals one physical laptop.** Quantity-based inventory is not used in Version 1. | Serial-number-first tracking |
| BR-17 | **Inventory list is grouped by Model Number** within Brand, with serial units expandable beneath. | Matches retail mental model — see PR-01 |
| BR-18 | **Lifecycle states are enforced.** Only allowed transitions in [Section 9.3](#93-allowed-transitions--version-1) are permitted. | Prevents invalid state changes |
| BR-19 | **Product specifications are searchable** via Product Model fields (CPU, GPU, RAM, storage). | Search-first for spec-based customer queries |
| BR-20 | **Movement does not change lifecycle state.** Location changes are separate from status changes. | LC-03 |
| BR-21 | **Barcode scanner input is equivalent to keyboard input** for serial number fields. | No separate scanner workflow — see Section 14 |
| BR-22 | **Color is a per-unit inventory attribute** — not a Product Model attribute. Same model number may exist in multiple colors. | See [§10.4](#104-color-attribute) |
| BR-23 | **Color is searchable and filterable** alongside brand, model, serial, product specifications, location, and status. | FR-SRH-07, FR-SRH-13 |
| BR-24 | **Product Models use Active/Archived lifecycle** — not unrestricted deletion. Permanent delete only when no inventory, sales, or audit references exist. | See [§12.2](#122-product-model-lifecycle) |
| BR-25 | **Purchase Date, Purchase Cost, and Remarks are excluded from Version 1.** | See [§10.5](#105-version-1-excluded-inventory-fields) |
| BR-26 | **Business entities store operational ownership only** — `created_by_user_id` and `updated_by_user_id`, set by the backend. Action-specific fields (`sold_by_user_id`, `reserved_by_user_id`, `approved_by_user_id`) are excluded. | See [§10.6](#106-operational-ownership-fields) |
| BR-27 | **Salesperson may move inventory** within the permission matrix. | See [§17.2](#172-permission-matrix) |
| BR-28 | **System initialization** is determined by `system_initialized` in `system_settings` — not by Main Admin user existence. | Setup wizard visibility; see §8.7 |
| BR-29 | **Client installations never create users.** User accounts exist only on the server. | See §8.8, §8.10 |
| BR-30 | **Passwords are stored only as bcrypt hashes** on the Backend. Clients never store password material. | Authentication authority on server |
| BR-31 | **Clients never store business data** locally in Version 1. | Online-first; server URL and tokens only |
| BR-32 | **Tally is read-only from IMS perspective.** IMS reads invoices from Tally; IMS never creates invoices or billing entries in Tally. | Billing boundary |
| BR-33 | **Tally sale reflection** matches serial numbers in **available** inventory only. Serial globally unique (BR-01). | See §8.6.1 |
| BR-34 | **Non-laptop Tally lines** (neither serial nor model in IMS) are ignored without notification. | Accessory/non-IMS products |
| BR-35 | **Manual mark-as-sold is Admin and Main Admin only.** Salesperson cannot manually mark inventory Sold. | See §8.6.3 |
| BR-36 | **Duplicate sale protection:** serial already **sold** when Tally line processed → notification only; no duplicate sale or audit. | FR-TLY-17 |
| BR-37 | **Multi-company Tally sync failures are isolated** — one company's failure must not stop another company's synchronization. | See §8.6 |
| BR-38 | **Invoice processing state** on `tally_processed_invoices` — SUCCESS only when all inventory-related lines complete. | See §8.6.2 |
| BR-39 | **Tally synchronization statistics** belong in `tally_sync_logs` — not Audit Log. | Audit = business events only |
| BR-40 | **Partial retry:** PARTIAL_SUCCESS retries failed lines only; completed lines immutable. | See §8.6.2 |
| BR-41 | **Line-level transactions:** one failed line never rolls back sibling lines on same invoice. | See §8.6.3 |
| BR-42 | **Crash recovery:** SUCCESS skip; PARTIAL_SUCCESS resume; FAILED full retry — no duplicate updates. | See §8.6.2 |

Additional business rules: **TBD** in [inventory rules](../business/inventory-rules.md).

---

## 19. Constraints

### 19.1 Business Constraints

| ID | Constraint |
|----|------------|
| BC-01 | Tally ERP 9 remains the billing system — not replaced, not replicated |
| BC-02 | All three locations operate in one building on shared Wi-Fi |
| BC-03 | Software must be usable by retail staff with minimal training |
| BC-04 | Deployment must not disrupt store operations during business hours |
| BC-05 | Dedicated Server PC is installed once; clients are installed per workstation without creating users |
| BC-06 | Excel remains in use as synchronized export during and after transition |
| BC-07 | Version 1 inventory category limited to laptops |
| BC-08 | Business operates as a real commercial retail environment — not a pilot or demo |

### 19.2 Technical Constraints

| ID | Constraint |
|----|------------|
| TC-01 | PostgreSQL is the sole authoritative datastore |
| TC-02 | Backend API is the only gateway to PostgreSQL — no direct database access from clients, integrations, or scripts without ADR |
| TC-03 | All business rules enforced server-side |
| TC-04 | On-premise deployment on Dedicated Server PC |
| TC-05 | Clients: Windows Desktop, macOS Desktop, Android |
| TC-06 | Technology stack **TBD** pending ADRs — no unapproved frameworks |
| TC-07 | Monorepo structure per ADR-0001 |

### 19.3 Deployment Constraints

| ID | Constraint |
|----|------------|
| DC-01 | Initial deployment on local business network (Wi-Fi) |
| DC-02 | Dedicated Server PC hosts backend, database, and integration services |
| DC-03 | Installation and upgrade procedures must be documented and repeatable |
| DC-04 | Maintenance windows **TBD** with business owner approval |

### 19.4 Future Constraints (Design For, Not Implement)

| ID | Constraint |
|----|------------|
| FC-01 | Architecture shall not prevent multi-branch or cloud deployment |
| FC-02 | Data model shall not assume single-site-only permanently |
| FC-03 | Integration pattern shall support additional ERP or scanner integrations |

---

## 20. Success Criteria

Version 1 succeeds when the following measurable outcomes are achieved. Quantitative targets marked **TBD** will be set before release sign-off.

| ID | Criterion | Measurement |
|----|-----------|-------------|
| SC-01 | **Reduced manual work** | Manual Excel inventory editing reduced to sync verification only |
| SC-02 | **Inventory accuracy** | Physical stock matches WEBSTUDIO IMS across all three locations |
| SC-03 | **Search speed** | Staff find any laptop by serial number or product-specification term (e.g., RTX 4060) in seconds — target **TBD** |
| SC-04 | **Synchronization reliability** | Excel and Tally sync succeed without manual intervention — target **TBD** |
| SC-05 | **Employee adoption** | Staff prefer WEBSTUDIO IMS over manual Excel process — survey **TBD** |
| SC-06 | **Sale reflection latency** | Time from Tally billing to inventory update — target **TBD** |
| SC-07 | **Zero duplicate serials** | No duplicate serial numbers in production database |
| SC-08 | **Audit completeness** | Every inventory mutation has corresponding audit entry |
| SC-09 | **Upgrade safety** | System upgrades completed without inventory data loss |
| SC-10 | **Training efficiency** | Salesperson productive within **TBD** hours of training |
| SC-11 | **Model-grouped presentation** | Staff can see available unit count per model without manual counting |

---

## 21. Out of Scope

The following are **explicitly excluded** from Version 1. Items marked **Future** may appear in Version 2+.

| Feature | Status | Notes |
|---------|--------|-------|
| Billing and invoicing | **Excluded** | Tally ERP 9 |
| Accounting and ledger | **Excluded** | Tally ERP 9 |
| CRM / customer management | **Excluded** | Future **TBD** |
| Payment processing | **Excluded** | Billing domain |
| Tax calculation | **Excluded** | Billing domain |
| Warranty management | **Future** | Version 2+ |
| Service center / repairs | **Future** | Version 2+ |
| Accessories inventory | **Future** | Version 2+ |
| Printer inventory | **Future** | Version 2+ |
| Barcode scanner hardware certification / proprietary SDK integrations | **Future** | Version 1 supports keyboard-wedge scanners only — see [Section 14](#14-barcode-scanner-business-behaviour) |
| Cloud deployment | **Future** | Version 2+ |
| Multi-city / multi-branch | **Future** | Version 2+ |
| E-commerce / online storefront | **Excluded** | Not a business need |
| General ERP functionality | **Excluded** | IMS only |
| Tally returns, refunds, credit notes, invoice cancellation | **Excluded** | Version 1 — see FR-TLY-15 |
| Automatic inventory creation from Tally | **Excluded** | Version 1 |
| Fuzzy / partial Tally serial matching | **Excluded** | Exact match only — BR-33 |
| Replacing Tally ERP 9 | **Excluded** | Permanent business constraint |
| Replacing Excel entirely | **Future** | Excel remains synchronized in V1 |
| Multi-factor authentication | **Future** | Version 2+ **TBD** |
| Custom report builder | **Future** | Version 2+ |
| Native iOS application | **Future** | **TBD** |
| Purchase Date on inventory | **Excluded V1** | See [§10.5](#105-version-1-excluded-inventory-fields) |
| Purchase Cost on inventory | **Excluded V1** | See [§10.5](#105-version-1-excluded-inventory-fields) |
| Remarks / notes field on inventory | **Excluded V1** | See [§10.5](#105-version-1-excluded-inventory-fields) |

---

## 22. Risks

### 22.1 Business Risks

| ID | Risk | Impact | Mitigation |
|----|------|--------|------------|
| BRK-01 | Staff resist adopting new system and revert to Excel | High | Minimal training design; premium UX; phased rollout **TBD** |
| BRK-02 | Tally sale data does not map cleanly to serial numbers | High | Mapping spec; manual fallback workflow |
| BRK-03 | Business process changes during development | Medium | Change control via PRD amendment |
| BRK-04 | Owner expectations exceed Version 1 scope | Medium | Clear Out of Scope section; roadmap communication |

### 22.2 Technical Risks

| ID | Risk | Impact | Mitigation |
|----|------|--------|------------|
| TRK-01 | Tally ERP 9 integration complexity underestimated | High | Research phase; isolated integration package; ADR before implementation |
| TRK-02 | Excel sync format mismatch with business expectations | Medium | Sample file validation with stakeholders |
| TRK-03 | Network reliability affects client-server communication | Medium | Graceful degradation; offline behavior **TBD** |
| TRK-04 | Technology stack choices delay delivery | Medium | ADR-driven decisions; research docs |
| TRK-05 | Serial number data quality in Excel migration | High | Import validation; duplicate detection |

### 22.3 Operational Risks

| ID | Risk | Impact | Mitigation |
|----|------|--------|------------|
| ORK-01 | Dedicated Server hardware failure | High | Backup/recovery procedures; hardware spec **TBD** |
| ORK-02 | No IT staff for ongoing maintenance | Medium | Documented runbooks; Main Admin training |
| ORK-03 | Sync failures go unnoticed | Medium | Logging, alerting, admin dashboard |

### 22.4 Deployment Risks

| ID | Risk | Impact | Mitigation |
|----|------|--------|------------|
| DRK-01 | Migration from Excel causes inventory discrepancy | High | Parallel run period **TBD**; reconciliation tools |
| DRK-02 | Deployment during business hours disrupts sales | High | Off-hours deployment window |
| DRK-03 | Upgrade corrupts production database | High | Tested migration scripts; rollback procedure |

---

## 23. Assumptions

| ID | Assumption | Validated |
|----|------------|-----------|
| AS-01 | All locations remain on the same Wi-Fi network for Version 1 | **TBD** |
| AS-02 | Tally ERP 9 exposes sufficient data for sale detection | **TBD** — research required |
| AS-03 | Excel file format can be standardized for sync output | **TBD** |
| AS-04 | Dedicated Server PC hardware will be provisioned before deployment | **TBD** |
| AS-05 | Serial numbers in existing Excel are mostly accurate and unique | **TBD** — audit required before migration |
| AS-06 | One building / three locations remains the operating model for Version 1 | Yes — per business context |
| AS-07 | Laptop-only inventory is sufficient for Version 1 business needs | Yes — per scope decision |
| AS-08 | Staff have access to Windows, macOS, or Android devices on shop floor | **TBD** |
| AS-09 | Main Admin account is created during First-Time Setup Wizard — not seeded in migrations | **TBD** — validate on first deployment |
| AS-10 | Business operating hours and maintenance windows can be agreed before deployment | **TBD** |
| AS-11 | Barcode scanners used by the business support keyboard-wedge (HID) mode | **TBD** — validate with hardware |

---

## 24. Future Roadmap

The following expansions are anticipated but **not committed** for Version 1. Each requires PRD amendment and ADR before development.

| Version | Theme | Likely Capabilities |
|---------|-------|-------------------|
| **1.0** | Laptop inventory core | This PRD — serial tracking, lifecycle, model-grouped presentation, dashboard, product-specification search, movement, Tally/Excel sync, barcode serial entry, roles, audit |
| **1.1** | Operational hardening | Bulk import, movement approval, enhanced reporting |
| **2.0** | Service & warranty | Warranty registration, service center, repair tracking attached to serial numbers |
| **2.x** | Category expansion | Accessories, printers, additional inventory categories |
| **3.0** | Multi-branch | Location hierarchy beyond single building; branch-level administration |
| **3.x** | Cloud option | Optional cloud deployment; remote access **TBD** |

Detailed roadmap: [product vision roadmap](../product/vision/roadmap.md) (**TBD**).

---

## 25. Requirement Traceability

All downstream artifacts must reference PRD requirement IDs.

| Artifact Type | Traceability Rule |
|---------------|-------------------|
| Functional Spec (FS-xxx) | Maps to one or more FR-xxx |
| Technical Spec (TS-xxx) | Maps to FR-xxx and NFR-xxx |
| Integration Spec (IS-xxx) | Maps to FR-XLS-xxx, FR-TLY-xxx |
| ADR | References business rule or constraint ID when applicable |
| API endpoint | References FR-xxx in OpenAPI description |
| UI screen | References FR-xxx in design documentation |
| Test case | References FR-xxx or NFR-xxx |
| Database migration | References BR-xxx, LC-xxx — schema design in separate spec |
| Lifecycle implementation | References [Section 9](#9-inventory-lifecycle) and FR-INV-05, FR-INV-13 |
| Dashboard | References FR-DSH-xxx and [Section 13](#13-dashboard-requirements) |

---

## 26. References

| Document | Path | Relationship |
|----------|------|--------------|
| **This document** | `docs/product/PRODUCT_REQUIREMENTS.md` | PRD-001 — v1.7 |
| **Project Bible** | [docs/PROJECT_BIBLE.md](../PROJECT_BIBLE.md) | Governing constitution |
| Inventory Lifecycle | [Section 9](#9-inventory-lifecycle) | Downstream database and API design |
| Inventory Entity | [Section 10](#10-inventory-entity-definition) | Downstream data model |
| Presentation Rules | [Section 11](#11-inventory-presentation-rules) | Downstream UI design |
| Data Relationships | [Section 12](#12-data-relationships) | Downstream architecture |
| Dashboard Requirements | [Section 13](#13-dashboard-requirements) | Downstream UI design |
| Barcode Behaviour | [Section 14](#14-barcode-scanner-business-behaviour) | Downstream desktop UX |
| Business Documentation | [docs/business/](business/README.md) | Operational context and rules |
| Current Workflow | [docs/business/current-workflow.md](business/current-workflow.md) | Aligns with [Section 7](#7-existing-workflow) |
| Inventory Rules | [docs/business/inventory-rules.md](business/inventory-rules.md) | Extends [Section 18](#18-business-rules) |
| User Roles | [docs/business/user-roles.md](business/user-roles.md) | Extends [Section 17](#17-user-roles-and-permissions) |
| Tally Integration | [docs/integrations/tally-erp9/](integrations/tally-erp9/README.md) | Implements FR-TLY-xxx |
| Excel Integration | [docs/integrations/excel/](integrations/excel/README.md) | Implements FR-XLS-xxx |
| Product Specifications | [specs/product/](../specs/product/README.md) | Downstream functional specs |
| Architecture | [docs/architecture/](architecture/README.md) | Downstream design |
| API Documentation | [docs/api/](api/README.md) | Downstream API design |
| UI/UX Documentation | [docs/ui-ux/](ui-ux/README.md) | Downstream UI design |
| Testing Strategy | [docs/testing/](testing/README.md) | Downstream test plans |
| Security Documentation | [docs/security/](security/README.md) | Implements NFR-SEC-xxx |
| Product Roadmap | [docs/product/vision/roadmap.md](product/vision/roadmap.md) | Extends [Section 24](#24-future-roadmap) |

---

> **Document Authority:** This PRD is the primary business specification for WEBSTUDIO IMS Version 1. Architectural, database, API, and UI designs must trace to requirements herein. Amendments require version increment and stakeholder review.

*WEBSTUDIO IMS Team — 2026*
