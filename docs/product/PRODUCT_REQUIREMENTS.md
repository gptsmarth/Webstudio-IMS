---
Title: WEBSTUDIO IMS — Product Requirements Document
Version: 1.2
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
| **Version** | 1.2 |
| **Status** | Active — business model refinements applied |
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

**Version 1 scope:** Individual laptop tracking by serial number across three locations, with model-grouped inventory presentation, per-unit Color tracking, operational dashboard, configuration- and color-aware search, Excel synchronization, Tally billing integration, barcode scanner support for serial entry, user management, movement history, reports, and audit logging — delivered on Windows Desktop, macOS Desktop, Android, and a Dedicated Server PC.

**Core philosophy:** WEBSTUDIO IMS is **inventory-first**, **serial-number-first**, and **search-first**. Every design and requirement decision must serve accurate individual laptop tracking, instant lookup, and minimal employee training — not feature breadth. Simplicity takes precedence over feature overload.

**Version 1 explicitly excludes:** Billing, accounting, CRM, warranty, service center, accessories, printers, cloud deployment, and multi-city branches.

---

## 2. Problem Statement

### 2.1 Current State

The business tracks every laptop as a row in an Excel spreadsheet. Each row contains Brand, Model Number, Serial Number, Configuration, and Current Location. When a laptop is sold:

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
| PG-15 | Support **configuration-aware search** across processor, GPU, RAM, storage, and screen size | See [Section 15.7](#157-search) |

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
| 2 | Admin | Add new row to Excel with Brand, Model Number, Serial Number, Configuration, Current Location | Excel |
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
| 2 | Staff | Enters Brand, Model Number, Serial Number, **Color**, Configuration, Current Location |
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
| 2 | System | Validates laptop exists, is in **Available** status, and is movable (see [Section 9.3](#93-allowed-transitions--version-1)) |
| 3 | System | Records movement with actor, timestamp, source location, destination location, reason (**TBD**) |
| 4 | System | Updates current location in PostgreSQL via Backend API |
| 5 | System | Creates audit log entry |
| 6 | System | Queues Excel synchronization |

**Business rule:** Every laptop has exactly one current location at any time.

### 8.3 Inventory Search

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | Any authorized user | Enters serial number, model number, brand, color, configuration term (processor, GPU, RAM, storage), location, or status — alone or in combination |
| 2 | System | Returns matching laptops with current location, configuration, color, status, and serial number |
| 3 | User | Views detail, expands model group, or initiates action (movement, sale reflection) |

**Design priority:** Search is accessible from every primary screen. Search must feel instant — see [Performance Goals in PROJECT_BIBLE](../PROJECT_BIBLE.md#15-performance-goals).

### 8.4 Sales (Tally-Driven)

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | Salesperson | Customer selects laptop; salesperson verifies availability via search |
| 2 | Salesperson | Completes billing in **Tally ERP 9** (unchanged) |
| 3 | System | Tally integration detects sale event (**mechanism TBD**) |
| 4 | System | Matches sale to inventory record by serial number or mapped identifier (**mapping TBD**) |
| 5 | System | Updates inventory lifecycle status to **Sold**; records customer and invoice reference fields (**field list TBD**) |
| 6 | System | Creates audit log and sales history entry |
| 7 | System | Queues Excel synchronization |

**Fallback (TBD):** Manual sale reflection by Admin/Salesperson if Tally sync fails or serial mapping is ambiguous.

> **Critical:** WEBSTUDIO IMS does not perform billing. Tally remains the billing system. IMS reflects billing outcomes in inventory.

### 8.5 Excel Synchronization

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | System | On schedule or trigger (**TBD**), exports current inventory state from PostgreSQL via Backend API |
| 2 | System | Writes synchronized representation to Excel file (**format TBD** — must preserve business-recognizable columns) |
| 3 | System | Logs sync result (success, failure, record count, timestamp) |

**Direction:** PostgreSQL → Excel (authoritative to derived). Excel must not drive inventory state.

### 8.6 Tally Synchronization

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | System | Polls or receives Tally billing events (**mechanism TBD**) |
| 2 | System | Parses sale data relevant to laptop inventory (**data mapping TBD**) |
| 3 | System | Calls Backend API to update inventory status |
| 4 | System | Logs integration event; surfaces failures to Admin |

**Direction:** Tally → WEBSTUDIO IMS (billing event to inventory update). WEBSTUDIO IMS does not write billing data to Tally.

### 8.7 User Management

| Step | Actor | System Action |
|------|-------|---------------|
| 1 | Main Admin | Creates, edits, deactivates user accounts |
| 2 | Main Admin | Assigns role: Main Admin, Admin, or Salesperson |
| 3 | System | Enforces role permissions on all operations via Backend API |

### 8.8 Exports and Reports

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
| **Sold** | Laptop has been billed and is no longer available inventory | Tally sale reflected; manual sale fallback | System (Tally sync), Admin, Salesperson (manual fallback) |

**Default flow for new stock:** Received → Available (when Admin confirms unit is ready for sale).

**Sale flow:** Available → Sold.

### 9.2 Future States (Not Version 1)

| State | Meaning | Planned Version |
|-------|---------|-----------------|
| **Reserved** | Laptop held for a customer but not yet billed | **Future** — TBD |
| **Returned** | Laptop returned after sale; re-entry to inventory workflow | **Future** — TBD |
| **Under Service** | Laptop with service center for repair or warranty work | **Future** — Version 2+ |
| **Disposed** | Laptop written off, damaged beyond sale, or removed from active inventory permanently | **Future** — TBD |

### 9.3 Allowed Transitions — Version 1

| From | To | Allowed | Actor | Condition |
|------|-----|---------|-------|-----------|
| — | Received | ✓ | Admin, Main Admin | New inventory addition |
| Received | Available | ✓ | Admin, Main Admin | Unit verified ready for sale |
| Received | Sold | — | — | **Not allowed** — must pass through Available |
| Available | Sold | ✓ | System, Admin, Salesperson | Tally sale or manual fallback |
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
| **Serial Number** | Exactly one; globally unique | Primary identity — see BR-01 |
| **Model Number** | Exactly one; may repeat across records | Product SKU — groups units for presentation |
| **Brand** | Exactly one | Required; links to brand reference |
| **Configuration** | Exactly one | Describes processor, GPU, RAM, storage, screen size, and other specs — free text or structured **TBD** |
| **Color** | Exactly one | Per-unit chassis/finish color — **not** a Product Model attribute; see [§10.4](#104-color-attribute) |
| **Current Location** | Exactly one | ASUS Exclusive Store, WEBSTUDIO Multi-brand Store, or Warehouse/Godown |
| **Current Status** | Exactly one | Lifecycle state — see [Section 9](#9-inventory-lifecycle) |
| **Audit History** | Complete; append-only | Every create, update, movement, and status change |

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
    Serial Number: SN-001  |  Color: Black  |  Configuration: i7 / 16GB / 512GB / RTX 4060  |  Location: ASUS Exclusive Store
    Serial Number: SN-002  |  Color: Silver |  Configuration: i7 / 16GB / 1TB / RTX 4060   |  Location: Warehouse / Godown
    Serial Number: SN-003  |  Color: Blue   |  Configuration: i5 / 8GB / 512GB              |  Location: WEBSTUDIO Multi-brand Store
    ...
```

### 11.2 Presentation Requirements

| ID | Rule |
|----|------|
| PR-01 | Inventory list is grouped by **Brand**, then **Model Number** |
| PR-02 | Each model group displays **count of available units** prominently |
| PR-03 | Individual serial numbers are visible on **expand** — not hidden, but not default clutter |
| PR-04 | Each expanded serial row shows **Color**, **Configuration**, and **Current Location** at minimum |
| PR-05 | Each expanded serial row shows **Current Status** (Received, Available, Sold) |
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
              └── has many → Inventory Movements (location changes)
              └── has many → Audit Log Entries (all changes)
```

| Relationship | Description |
|--------------|-------------|
| **Brand → Product Model** | Every product model belongs to one brand. A brand has many product models. |
| **Product Model → Inventory Unit** | Many laptops share a product model. Units differ by serial number, color, and configuration. |
| **Brand → Inventory Unit** | Every laptop belongs to one brand (via product model). |
| **Inventory Unit → Sales Record** | When sold, a laptop has one associated sales record with customer and invoice reference. |
| **Inventory Unit → Inventory Movement** | Each location change produces a movement record linked to the serial number. |
| **Inventory Unit → Audit Log** | Every mutation on the unit produces an audit entry. |

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
| PM-06 | **Permanent deletion** is permitted only when **all** of the following are true: no Inventory Items were ever created; no Sale records exist; no Audit Log references exist |
| PM-07 | If any historical reference exists, only **Archive** is permitted — not delete |

### 12.3 Operational Domain

```
User
  └── performs → Inventory Movement
  └── performs → Inventory Addition
  └── performs → Status Change
  └── triggers (via action) → Audit Log Entry
```

| Relationship | Description |
|--------------|-------------|
| **User → Inventory Movement** | Every movement records the acting user. |
| **User → Audit Log** | Every auditable action records the acting user. |
| **Inventory Movement → Audit Log** | Movement creation produces an audit entry. |
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
| 4 | User completes remaining fields: Brand, Model Number, **Color**, Configuration, Location |
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

### 15.1 Authentication

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-AUTH-01 | System shall require authentication before any inventory operation | Mandatory | Via Backend API |
| FR-AUTH-02 | System shall support secure login for all platforms (Windows, macOS, Android) | Mandatory | Method **TBD** (username/password minimum) |
| FR-AUTH-03 | System shall terminate inactive sessions after configurable timeout | Mandatory | Default **TBD** |
| FR-AUTH-04 | System shall lock account after configurable failed login attempts | Mandatory | Threshold **TBD** |
| FR-AUTH-05 | System shall support password change by user and reset by Main Admin | Mandatory | |
| FR-AUTH-06 | System shall support multi-factor authentication | Future | Version 2+ **TBD** |

### 15.2 User Management

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-USER-01 | Main Admin shall create, edit, deactivate, and reactivate user accounts | Mandatory | |
| FR-USER-02 | Main Admin shall assign one role per user: Main Admin, Admin, or Salesperson | Mandatory | |
| FR-USER-03 | System shall prevent deactivation of the last Main Admin account | Mandatory | |
| FR-USER-04 | System shall record user management actions in audit log | Mandatory | |
| FR-USER-05 | Main Admin shall view list of all users with role and status | Mandatory | |
| FR-USER-06 | Admin shall view list of users at their location | Future | **TBD** — location-scoped admin |

### 15.3 Inventory Management

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-INV-01 | System shall register laptops with Brand, Model Number, Serial Number, **Color**, Configuration, and Current Location | Mandatory | One record = one physical laptop — see [Section 10](#10-inventory-entity-definition) |
| FR-INV-02 | System shall treat Serial Number as the globally unique identifier for each laptop | Mandatory | See BR-01 |
| FR-INV-03 | System shall allow Model Number to repeat across multiple laptops | Mandatory | See BR-02 |
| FR-INV-04 | System shall enforce exactly one current location per laptop | Mandatory | See BR-03 |
| FR-INV-05 | System shall support lifecycle states: **Received**, **Available**, **Sold** in Version 1 | Mandatory | See [Section 9](#9-inventory-lifecycle) |
| FR-INV-06 | System shall allow editing of laptop attributes by authorized roles | Mandatory | Permission matrix in [Section 17](#17-user-roles-and-permissions) |
| FR-INV-07 | System shall prevent deletion of inventory records — deactivation or status change only | Mandatory | Audit integrity |
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
| FR-PM-01 | System shall maintain Product Models as distinct entities within a Brand (model number + brand) | Mandatory | See [§12.2](#122-product-model-lifecycle) |
| FR-PM-02 | Product Models shall have lifecycle states: **Active** and **Archived** | Mandatory | PM-01–PM-07 |
| FR-PM-03 | Main Admin shall Archive and Restore Product Models | Mandatory | |
| FR-PM-04 | System shall prevent selection of Archived Product Models during inventory creation | Mandatory | PM-04 |
| FR-PM-05 | System shall hide Archived Product Models from Salesperson default inventory views | Mandatory | PM-05; Admin filter **TBD** |
| FR-PM-06 | System shall allow permanent deletion of a Product Model only when no Inventory Items, Sales, or Audit references exist | Mandatory | PM-06, PM-07 |
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
| FR-MOV-02 | System shall record source location, destination location, actor, timestamp, and optional reason | Mandatory | Audit requirement |
| FR-MOV-03 | System shall update current location upon successful movement | Mandatory | Does not change lifecycle state — see LC-03 |
| FR-MOV-04 | System shall display movement history per laptop | Mandatory | |
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
| FR-SRH-05 | System shall search within Configuration text for: Processor, Graphics Card (GPU), RAM, Storage, Screen Size | Mandatory | Configuration-aware search |
| FR-SRH-06 | Search for partial configuration terms shall return all matching laptops — e.g., `4060` returns all units with RTX 4060; `i7` returns all Intel Core i7 units; `16GB` returns all 16GB RAM units | Mandatory | Case-insensitive **TBD** |
| FR-SRH-07 | System shall support **combined search criteria** — Brand, Model Number, Serial Number, configuration terms (CPU/GPU/RAM/Storage), Color, Location, and Status may be applied together | Mandatory | Multi-filter search |
| FR-SRH-08 | System shall return results within perceived instant response time | Mandatory | Numeric target **TBD** |
| FR-SRH-09 | System shall support barcode scanner input for serial number search | Mandatory | See [Section 14](#14-barcode-scanner-business-behaviour) |
| FR-SRH-10 | Search shall be keyboard-accessible on desktop platforms | Mandatory | See Design Principles in Project Bible |
| FR-SRH-11 | Search results for specific serial number shall show unit detail directly | Mandatory | |
| FR-SRH-12 | Search results for model or configuration terms may show grouped or flat list — **TBD** in UI spec | Mandatory | See PR-08 |
| FR-SRH-13 | System shall search and filter by **Color** with exact and partial match | Mandatory | See [§10.4](#104-color-attribute) |

### 15.8 Sales History

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-SLS-01 | System shall record sales history when inventory status changes to Sold | Mandatory | |
| FR-SLS-02 | Sales history shall include serial number, sale date/time, actor, customer details, invoice reference | Mandatory | Invoice reference links to Tally |
| FR-SLS-03 | Authorized users shall view sales history with filter by date range, location, brand | Mandatory | |
| FR-SLS-04 | System shall support manual sale reflection when Tally sync unavailable | Mandatory | Fallback workflow **TBD** |
| FR-SLS-05 | System shall not generate invoices or billing documents | Mandatory | Tally owns billing |

### 15.9 Excel Synchronization

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-XLS-01 | System shall synchronize inventory from PostgreSQL to Excel on a defined schedule | Mandatory | Schedule **TBD** |
| FR-XLS-02 | System shall support manual trigger of Excel sync by Main Admin | Mandatory | |
| FR-XLS-03 | Excel output shall include columns: Brand, Model Number, Serial Number, **Color**, Configuration, Current Location, Status | Mandatory | Per [§10.4](#104-color-attribute) |
| FR-XLS-04 | System shall log every sync attempt with timestamp, outcome, and record count | Mandatory | |
| FR-XLS-05 | System shall surface sync failures to Main Admin | Mandatory | |
| FR-XLS-06 | Excel sync shall never write inventory changes back to PostgreSQL | Mandatory | See BR-08 |
| FR-XLS-07 | Excel sync shall operate through Backend API — never direct database access | Mandatory | Project Bible N2 |

### 15.10 Tally Integration

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-TLY-01 | System shall detect or receive billing events from Tally ERP 9 | Mandatory | Mechanism **TBD** |
| FR-TLY-02 | System shall map Tally sale data to inventory records by serial number or mapped identifier | Mandatory | Mapping spec **TBD** |
| FR-TLY-03 | System shall update inventory lifecycle status to Sold upon confirmed Tally sale | Mandatory | Available → Sold |
| FR-TLY-04 | System shall log every Tally integration event | Mandatory | |
| FR-TLY-05 | System shall surface integration failures to Main Admin | Mandatory | |
| FR-TLY-06 | System shall not replace or replicate Tally billing functionality | Mandatory | See BR-07 |
| FR-TLY-07 | Tally integration shall operate through Backend API — never direct database access | Mandatory | Project Bible N2 |
| FR-TLY-08 | System shall support manual reconciliation when Tally sync fails | Mandatory | Workflow **TBD** |

### 15.11 Reports and Export

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-RPT-01 | System shall provide inventory summary report by location | Mandatory | |
| FR-RPT-02 | System shall provide sold inventory report by date range | Mandatory | |
| FR-RPT-03 | System shall provide movement history report | Mandatory | |
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
| FR-SET-02 | Main Admin shall configure Tally integration connection parameters | Mandatory | Parameters **TBD** |
| FR-SET-03 | Main Admin shall configure session timeout and lockout thresholds | Mandatory | |
| FR-SET-04 | Main Admin shall configure application display name and business details | Mandatory | Fields **TBD** |
| FR-SET-05 | System shall support Light and Dark theme default per user or global | Mandatory | |
| FR-SET-06 | Main Admin shall view system health and integration status | Mandatory | Detail level **TBD** |
| FR-SET-07 | Main Admin shall configure barcode scanner auto-submit behaviour on Enter | Mandatory | See BC-03 — default **TBD** |

### 15.14 Audit Logs

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-AUD-01 | System shall record audit entry for every inventory create, update, status change, and movement | Mandatory | |
| FR-AUD-02 | System shall record audit entry for user management actions | Mandatory | |
| FR-AUD-03 | System shall record audit entry for settings changes | Mandatory | |
| FR-AUD-04 | Audit entry shall include actor, timestamp, action type, entity identifier, before/after state (**detail level TBD**) | Mandatory | |
| FR-AUD-05 | Main Admin shall search and filter audit logs | Mandatory | |
| FR-AUD-06 | Audit logs shall be immutable — no edit or delete | Mandatory | |
| FR-AUD-07 | Audit log retention period | Mandatory | Duration **TBD** |

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
| NFR-PERF-01 | Serial number and configuration-term search shall feel instant to the user on desktop | Mandatory | Numeric target **TBD** |
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
| **Salesperson** | Front-line search, sale verification, and limited inventory actions. |

Future roles: **TBD**.

### 17.2 Permission Matrix

| Capability | Main Admin | Admin | Salesperson |
|------------|:----------:|:-----:|:-----------:|
| **Authentication** | | | |
| Login / logout | ✓ | ✓ | ✓ |
| Change own password | ✓ | ✓ | ✓ |
| **User Management** | | | |
| Create / edit / deactivate users | ✓ | — | — |
| Assign roles | ✓ | — | — |
| View all users | ✓ | — | — |
| **Inventory** | | | |
| Add inventory | ✓ | ✓ | — |
| Edit inventory attributes | ✓ | ✓ | — |
| View inventory | ✓ | ✓ | ✓ |
| Change inventory status (sold) — manual fallback | ✓ | ✓ | ✓ |
| **Movement** | | | |
| Initiate movement | ✓ | ✓ | Request **TBD** |
| View movement history | ✓ | ✓ | ✓ |
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
| Configure Excel sync | ✓ | — | — |
| Configure Tally integration | ✓ | — | — |
| Trigger manual sync | ✓ | ✓ | — |
| View sync status | ✓ | ✓ | — |
| **System Settings** | | | |
| Configure all settings | ✓ | — | — |
| **Audit Logs** | | | |
| View audit logs | ✓ | — | — |
| **Backup** | | | |
| Trigger backup / restore | ✓ | — | — |

**Legend:** ✓ = permitted, — = not permitted. Refinements **TBD** during specification phase.

---

## 18. Business Rules

Business rules are authoritative for Version 1. Implementation belongs exclusively in the Backend API per [PROJECT_BIBLE](../PROJECT_BIBLE.md).

| ID | Rule | Rationale |
|----|------|-----------|
| BR-01 | **Serial Numbers are globally unique.** No two inventory records may share the same serial number. | Prevents duplicate stock; enables reliable search and audit |
| BR-02 | **Model Numbers may repeat.** One model number may identify many laptops. | Same product SKU appears in multiple physical units |
| BR-03 | **Every laptop has exactly one current location.** A laptop cannot be in two locations simultaneously. | Physical reality; enables location-based stock counts |
| BR-04 | **Inventory movements are logged.** Every location change records actor, timestamp, source, destination. | Audit and dispute resolution |
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
| BR-19 | **Configuration is searchable.** Processor, GPU, RAM, storage, and screen size terms in Configuration field must be findable via search. | Search-first for spec-based customer queries |
| BR-20 | **Movement does not change lifecycle state.** Location changes are separate from status changes. | LC-03 |
| BR-21 | **Barcode scanner input is equivalent to keyboard input** for serial number fields. | No separate scanner workflow — see Section 14 |
| BR-22 | **Color is a per-unit inventory attribute** — not a Product Model attribute. Same model number may exist in multiple colors. | See [§10.4](#104-color-attribute) |
| BR-23 | **Color is searchable and filterable** alongside brand, model, serial, configuration, location, and status. | FR-SRH-07, FR-SRH-13 |
| BR-24 | **Product Models use Active/Archived lifecycle** — not unrestricted deletion. Permanent delete only when no inventory, sales, or audit references exist. | See [§12.2](#122-product-model-lifecycle) |
| BR-25 | **Purchase Date, Purchase Cost, and Remarks are excluded from Version 1.** | See [§10.5](#105-version-1-excluded-inventory-fields) |

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
| BC-05 | Excel remains in use as synchronized export during and after transition |
| BC-06 | Version 1 inventory category limited to laptops |
| BC-07 | Business operates as a real commercial retail environment — not a pilot or demo |

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
| SC-03 | **Search speed** | Staff find any laptop by serial number or configuration term (e.g., RTX 4060) in seconds — target **TBD** |
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
| AS-09 | Main Admin account will be maintained by business owner or designated lead | **TBD** |
| AS-10 | Business operating hours and maintenance windows can be agreed before deployment | **TBD** |
| AS-11 | Barcode scanners used by the business support keyboard-wedge (HID) mode | **TBD** — validate with hardware |

---

## 24. Future Roadmap

The following expansions are anticipated but **not committed** for Version 1. Each requires PRD amendment and ADR before development.

| Version | Theme | Likely Capabilities |
|---------|-------|-------------------|
| **1.0** | Laptop inventory core | This PRD — serial tracking, lifecycle, model-grouped presentation, dashboard, configuration search, movement, Tally/Excel sync, barcode serial entry, roles, audit |
| **1.1** | Operational hardening | Bulk import, movement approval, enhanced reporting, structured configuration fields (**TBD**) |
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
| **This document** | `docs/product/PRODUCT_REQUIREMENTS.md` | PRD-001 — v1.1 |
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
