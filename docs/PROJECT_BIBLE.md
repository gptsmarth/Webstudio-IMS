---
Title: WEBSTUDIO IMS — Project Bible
Version: 1.3
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/README.md, AGENTS.md, adr/README.md, docs/business/README.md, docs/ui-ux/README.md, docs/operations/README.md
---

# WEBSTUDIO IMS — Project Bible

> **This document is the constitution of the WEBSTUDIO IMS project.**
>
> Every developer, architect, designer, QA engineer, AI assistant, and future contributor must read and internalize this document before making any change to the repository, the product, or its documentation.
>
> When guidance conflicts, this document takes precedence over informal notes, chat messages, and unrecorded decisions — unless superseded by an accepted Architecture Decision Record (ADR).

---

## Version History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.3 | 2026-06-27 | WEBSTUDIO IMS Team | Audit-only history architecture: removed InventoryMovement module; `audit_log` is single source of truth for inventory lifecycle; Sprint 1E = audit logs migration. |
| 1.2 | 2026-06-27 | WEBSTUDIO IMS Team | Documentation consistency resolution: ADR index alignment; architecture frozen for Version 1 development. |
| 1.1 | 2026-06-27 | WEBSTUDIO IMS Team | Server initialization and client onboarding: `system_initialized` setting; first-time setup wizard; client discovery and manual server configuration; login gated on setup status; Main Admin-only user management; clients never store business data. |
| 1.0 | 2026-06-27 | WEBSTUDIO IMS Team | Architecture Review Revision 1. Strengthened backend authority, added product identity, lifecycle, quality standards, design principles, data ownership, integration principles, performance goals, observability, and expanded architecture philosophy. Frozen as governing document. |
| 0.1 | 2026-06-27 | WEBSTUDIO IMS Team | Initial draft. Establishes project constitution, principles, scope, and collaboration rules. |

---

## Product Identity

Permanent metadata for WEBSTUDIO IMS. Update this table when release, ownership, or platform support changes.

| Attribute | Value |
|-----------|-------|
| **Product Name** | WEBSTUDIO IMS |
| **Full Form** | WEBSTUDIO Inventory Management System |
| **Repository** | WEBSTUDIO IMS (monorepo) — see [ADR-0001](../adr/records/0001-monorepo-structure.md) |
| **Owner** | WEBSTUDIO IMS Team |
| **Deployment Model** | On-premise (initial); cloud deployment **TBD** — see [future architecture](architecture/future/cloud-deployment.md) |
| **License Type** | Proprietary — see [legal/LICENSE](../legal/LICENSE) |
| **Current Release** | 0.1.0 — Pre-development |
| **Document Version** | 1.3 (this Bible) |
| **Target Users** | Store staff, warehouse staff, managers |
| **Project Type** | Commercial internal platform (laptop retail inventory) |
| **Supported Platforms** | Windows Desktop, macOS Desktop, Android, Dedicated Server, Backend API |
| **Primary Language** | Python (backend), TypeScript (clients) — see [TECH_STACK.md](TECH_STACK.md) |
| **Authoritative Datastore** | PostgreSQL — accessed exclusively via Backend API |
| **Primary Integrations** | Tally ERP 9 (billing), Excel (synchronized representation) |
| **Architecture Status** | **FROZEN FOR VERSION 1 DEVELOPMENT** |

---

## Product Lifecycle

Every change belongs to a stage in the product lifecycle. Contributors must identify which stage they are working in before making changes — and produce the artifacts appropriate to that stage.

```
Requirements
     ↓
Specification
     ↓
Architecture
     ↓
Implementation
     ↓
Testing
     ↓
Deployment
     ↓
Maintenance
     ↓
Future Enhancements
```

| Stage | Purpose | Primary Artifacts | Where to Work |
|-------|---------|-------------------|---------------|
| **Requirements** | Capture business need | PRDs, user stories | [docs/product/requirements/](product/requirements/) |
| **Specification** | Define precise behavior | Functional, technical, integration specs | [specs/](specs/) |
| **Architecture** | Record structural decisions | ADRs, architecture diagrams | [adr/records/](../adr/records/), [docs/architecture/](architecture/README.md) |
| **Implementation** | Build the system | Source code in `apps/`, `packages/` | Platform guides in [docs/development/](development/README.md) |
| **Testing** | Verify correctness | Test plans, automated tests | [docs/testing/](testing/README.md), [tests/](../tests/README.md) |
| **Deployment** | Ship and operate | Runbooks, deployment scripts | [docs/deployment/](deployment/README.md), [infra/](../infra/README.md) |
| **Maintenance** | Sustain production | Operations runbooks, patches | [docs/operations/](operations/README.md) |
| **Future Enhancements** | Extend the platform | Future architecture notes, roadmap | [docs/architecture/future/](architecture/future/), [docs/product/vision/roadmap.md](product/vision/roadmap.md) |

**How to apply:** Before starting work, ask: *Which lifecycle stage does this task belong to?* Produce or update the artifact for that stage before moving to the next. Do not implement code without an approved spec. Do not adopt technology without an ADR. Do not deploy without tested runbooks.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Vision](#2-vision)
3. [Mission](#3-mission)
4. [Business Context](#4-business-context)
5. [Product Purpose](#5-product-purpose)
6. [Product Philosophy](#6-product-philosophy)
7. [Design Principles](#7-design-principles)
8. [Core Product Principles](#8-core-product-principles)
9. [Data Ownership](#9-data-ownership)
10. [Product Quality Standards](#10-product-quality-standards)
11. [Engineering Principles](#11-engineering-principles)
12. [UI / UX Philosophy](#12-ui--ux-philosophy)
13. [Security Philosophy](#13-security-philosophy)
14. [Performance Philosophy](#14-performance-philosophy)
15. [Performance Goals](#15-performance-goals)
16. [Scalability Philosophy](#16-scalability-philosophy)
17. [Maintainability Philosophy](#17-maintainability-philosophy)
18. [Observability Philosophy](#18-observability-philosophy)
19. [Documentation Philosophy](#19-documentation-philosophy)
20. [AI Collaboration Philosophy](#20-ai-collaboration-philosophy)
21. [Coding Philosophy](#21-coding-philosophy)
22. [Architecture Philosophy](#22-architecture-philosophy)
23. [Integration Principles](#23-integration-principles)
24. [Deployment Philosophy](#24-deployment-philosophy)
    - [24.4 Server Initialization](#244-server-initialization)
    - [24.5 Client Onboarding](#245-client-onboarding)
25. [Product Scope](#25-product-scope)
26. [Out of Scope](#26-out-of-scope)
27. [Business Constraints](#27-business-constraints)
28. [Technical Constraints](#28-technical-constraints)
29. [Future Expansion Guidelines](#29-future-expansion-guidelines)
30. [Non-Negotiable Rules](#30-non-negotiable-rules)
31. [Guiding Principles for Contributors](#31-guiding-principles-for-contributors)
32. [Definition of Done](#32-definition-of-done)
33. [Success Criteria](#33-success-criteria)
34. [Glossary of Core Terms](#34-glossary-of-core-terms)
35. [References to Related Documents](#35-references-to-related-documents)

---

## 1. Project Overview

**WEBSTUDIO IMS** (WEBSTUDIO Inventory Management System) is a commercial-grade inventory management platform being built for a real laptop retail business operating multiple store formats within a single building.

The system replaces manual Excel-based inventory tracking while preserving Tally ERP 9 as the sole billing and accounting system. It spans desktop applications (Windows and macOS), an Android application, a dedicated server application, a backend API, and a PostgreSQL database.

| Attribute | Value |
|-----------|-------|
| **Project Name** | WEBSTUDIO IMS |
| **Full Form** | WEBSTUDIO Inventory Management System |
| **Version** | 0.1.0 — Pre-development (see [Product Identity](#product-identity)) |
| **Status** | Active — governed by this Bible v1.1 |
| **Primary Users** | Store staff, warehouse staff, managers |
| **Primary Integrations** | Tally ERP 9, Excel |
| **Data Store** | PostgreSQL |

This document defines what the product is, what it is not, how it should be built, and how every contributor — human or AI — should behave when working on it.

---

## 2. Vision

WEBSTUDIO IMS will become a reliable, premium-quality internal platform that gives the business complete visibility and control over laptop inventory across every location — without disrupting established billing workflows in Tally.

Over time, the platform should grow into a durable foundation capable of supporting warranty management, service center operations, repairs, accessories, printers, multi-branch inventory, and cloud deployment — without requiring architectural reinvention.

**What this means:** We are not building a point solution for today's spreadsheet problem. We are building a platform whose boundaries can expand module by module.

**Why it exists:** Retail inventory errors compound into revenue loss, customer dissatisfaction, and operational chaos. A system designed for five years will fail; a system designed for ten or more creates compounding value.

**How to apply it:** Every design decision should be evaluated against the question: *Does this make future modules easier or harder to add?* If a shortcut closes a door the roadmap may need, reject it.

---

## 3. Mission

To eliminate manual inventory management for a laptop retail business by providing accurate, auditable, searchable inventory control across all locations — while keeping Tally ERP 9 as the billing system of record.

**What this means:** The mission is narrow and deliberate. Inventory accuracy is the problem we solve. Billing is not.

**Why it exists:** The business already has a billing system that works. Replacing it would introduce risk disproportionate to the problem. Our mission respects existing operations while removing the manual burden that causes inventory drift.

**How to apply it:** When evaluating features, ask: *Does this improve inventory accuracy, visibility, or control?* If the answer is no, it belongs in Out of Scope or Future Expansion — not in the current release.

---

## 4. Business Context

### 4.1 Operating Locations

The business operates three inventory-relevant locations, all within one building on a shared Wi-Fi network:

| Location | Description |
|----------|-------------|
| **ASUS Exclusive Store** | Brand-exclusive retail floor |
| **WEBSTUDIO Multi-brand Store** | Multi-brand retail floor |
| **Warehouse / Godown** | Storage and stock holding area |

Location-specific business rules, naming conventions, and movement policies are **TBD** in [business documentation](business/README.md).

### 4.2 Current Workflow

Today, the business operates as follows:

1. **Billing** is performed entirely in **Tally ERP 9**. Tally will not be replaced.
2. **Laptop inventory** is manually maintained in **Excel**.
3. **Employees manually mark sold laptops** in Excel after a sale is completed in Tally.
4. **Inventory movement between locations** is tracked manually.

This manual process creates delays, inconsistencies, and gaps between what Tally records as sold and what Excel reflects as available.

### 4.3 What the Software Changes

WEBSTUDIO IMS exists to **eliminate manual inventory management** while **keeping Tally as the billing system**.

| System | Role |
|--------|------|
| **Tally ERP 9** | Billing, accounting, invoicing — system of record for sales |
| **WEBSTUDIO IMS (PostgreSQL)** | Inventory — single source of truth for stock state |
| **Excel** | Synchronized representation of inventory — not authoritative |

The exact synchronization mechanics between these systems are **TBD** in [integration specifications](integrations/README.md). Regardless of sync mechanism, **no integration may write directly to PostgreSQL** — all inventory mutations pass through the [Backend API](#backend-authority). See [Section 8](#8-core-product-principles) and [Section 23](#23-integration-principles).

---

## 5. Product Purpose

WEBSTUDIO IMS is an **Inventory Management System**.

### What It Is

- A system for tracking laptop inventory across locations
- A platform for auditable inventory movements
- A searchable registry of stock, identified by serial numbers
- A bridge between billing events (Tally) and inventory state (IMS)

### What It Is Not

| Category | Status |
|----------|--------|
| ERP | **Not this product** |
| Accounting software | **Not this product** |
| Billing software | **Not this product** |
| CRM | **Not this product** |

> **Critical:** Billing will always remain inside Tally ERP 9. Inventory is the sole responsibility of WEBSTUDIO IMS. No feature, integration, or UI surface should blur this boundary.

---

## 6. Product Philosophy

Product philosophy defines how we think about what we build and what we refuse to build.

### 6.1 Simplicity Over Feature Overload

**What it means:** The product should do fewer things well rather than many things poorly. Every screen, field, and action must earn its place.

**Why it exists:** Retail staff use this software under time pressure, often while serving customers. Complexity creates errors. Feature overload creates abandonment.

**How to apply it:** Before adding a feature, demonstrate that it serves a documented business need. Default to deferral. When two designs achieve the same outcome, choose the one with fewer steps.

### 6.2 Search as a First-Class Feature

**What it means:** Finding a laptop by serial number, model, location, or status must be fast, reliable, and available from every primary surface of the application.

**Why it exists:** Inventory software that cannot be searched quickly is inventory software that is not used. Search is not a utility — it is the primary interaction pattern.

**How to apply it:** Design search into wireframes from the start. Performance requirements for search are **TBD** but must be defined before release. Never bury search behind multiple navigation levels.

### 6.3 Premium SaaS Quality

**What it means:** The software should look, feel, and behave like a premium SaaS application — polished, responsive, consistent, and trustworthy — regardless of whether it is deployed on-premise.

**Why it exists:** Internal tools that feel inferior are tolerated rather than adopted. Quality signals reliability. Reliability signals that the inventory data can be trusted.

**How to apply it:** Apply consistent spacing, typography, and interaction patterns. Support Light and Dark themes. Avoid visual clutter. Treat empty states, loading states, and error states as first-class design problems.

### 6.4 Configuration Over Hardcoding

**What it means:** Values that may change — locations, categories, statuses, labels, thresholds — should be configurable rather than embedded in source code.

**Why it exists:** A retail business evolves. Hardcoded values create deployment friction and require developer intervention for operational changes.

**How to apply it:** When introducing a constant, ask: *Could a manager reasonably need to change this?* If yes, make it configurable with appropriate authorization. Document configurable values in [business documentation](business/README.md) and [deployment documentation](deployment/README.md).

---

## 7. Design Principles

Design principles define how WEBSTUDIO IMS should look, feel, and behave. This section is the foundation of the future [Design System](ui-ux/design-system/) and [UI/UX documentation](ui-ux/README.md). Detailed component specifications are **TBD**.

### 7.1 Minimal Interface

**Meaning:** Every screen shows only what the user needs for the current task. Remove decorative elements, redundant labels, and infrequently used actions from primary surfaces.

**Reason:** Retail staff operate under time pressure. Visual noise increases cognitive load and error rates.

**Application:** Audit each screen against a single primary action. Move secondary actions to menus or detail views. Document screen layouts in [user flows](ui-ux/user-flows/).

### 7.2 Search First

**Meaning:** Search is the default entry point for finding inventory. Search controls are prominent, always accessible, and optimized for serial number lookup.

**Reason:** The most common operation is "find this laptop." If search is buried, the product fails its primary use case.

**Application:** Place search in a consistent, persistent location across all platforms. Design keyboard shortcuts to focus search instantly. See also [Section 6.2](#62-search-as-a-first-class-feature) and [Performance Goals](#15-performance-goals).

### 7.3 Keyboard Friendly

**Meaning:** Desktop applications support keyboard navigation and shortcuts for all frequent operations. Power users should rarely need the mouse.

**Reason:** Counter staff often juggle customer interaction, paperwork, and the screen simultaneously. Keyboard efficiency reduces transaction time.

**Application:** Define a platform keyboard map in [desktop platform guidelines](ui-ux/platform-guidelines/). Tab order, Enter-to-submit, and Escape-to-cancel are mandatory patterns. Android keyboard behavior is **TBD**.

### 7.4 Progressive Disclosure

**Meaning:** Show simple defaults first. Reveal advanced options, filters, and bulk actions only when the user requests them.

**Reason:** Information overload causes abandonment. Most daily tasks are simple; advanced capabilities must not clutter the default experience.

**Application:** Use expandable sections, "Advanced" toggles, and stepped workflows. Never require an expert mode to perform basic inventory operations.

### 7.5 Consistent Layouts

**Meaning:** Navigation, headers, action bars, tables, and forms follow the same spatial structure across every screen and platform.

**Reason:** Consistency reduces relearning cost when staff switch between Windows, macOS, and Android.

**Application:** Define layout templates in the design system. Deviations require documentation in [platform guidelines](ui-ux/platform-guidelines/) with explicit rationale.

### 7.6 Responsive Feedback

**Meaning:** Every user action receives immediate, visible acknowledgment — loading state, success confirmation, or actionable error message.

**Reason:** On a retail floor, uncertainty about whether an action succeeded leads to duplicate entries and inventory corruption.

**Application:** Define loading, success, error, and empty-state patterns in the design system. Never leave the user wondering. See also [Section 12.4](#124-responsive-feedback).

### 7.7 No Information Overload

**Meaning:** Data-dense views are paginated, filtered, and scannable. Never present unbounded lists or walls of unstructured text.

**Reason:** Inventory systems accumulate large datasets. Dumping everything on screen paralyzes decision-making.

**Application:** Default to paginated tables with clear sort and filter controls. Summarize before detail. Use progressive disclosure for record-level depth.

---

## 8. Core Product Principles

Each principle below is binding on product decisions.

| # | Principle | Meaning | Why | Application |
|---|-----------|---------|-----|-------------|
| P1 | **PostgreSQL is the single source of truth** | All authoritative inventory state lives in PostgreSQL. No client, file, or integration holds canonical data. | Eliminates conflicting records across Excel, clients, and integrations. | Clients read and write through the backend API. Excel receives exports; it never drives state. |
| P2 | **Excel is a synchronized representation** | Excel reflects inventory; it does not define it. | The business currently uses Excel; migration requires continuity without ceding authority. | Sync direction, frequency, and conflict resolution are **TBD** in [Excel integration specs](integrations/excel/import-export-spec.md). Excel sync processes call the Backend API — never PostgreSQL directly. |
| P3 | **Tally remains the billing system** | Sales, invoicing, and accounting stay in Tally ERP 9. | Tally is entrenched, trusted, and sufficient for billing. Replacing it is out of scope. | IMS reacts to billing events via integration services; it does not generate invoices or manage accounts. See [Tally integration docs](integrations/tally-erp9/README.md). |
| P4 | **Serial numbers are globally unique** | Every laptop serial number exists exactly once in the system, across all locations and time. | Duplicate serials make inventory untrustworthy and audits impossible. | Enforce uniqueness at the database level. Reject duplicates at the API level. Never allow client-side override. |
| P5 | **Every movement is auditable** | Every inventory state change records who, what, when, where, and why. | Retail disputes, shrinkage investigations, and compliance require traceability. | No silent updates. No bulk changes without audit trails. Design audit into the data model from the start. See [Observability Philosophy](#18-observability-philosophy). |
| P6 | **Business rules exist once** | Every business rule is implemented exactly once, in the backend. | Duplicated rules diverge. Divergent rules produce inconsistent inventory. | Desktop and Android are presentation and capture layers. They never enforce rules independently. |
| P7 | **Clients never bypass the backend** | Desktop and Android applications communicate only through the backend API. | Direct database access or integration shortcuts create untracked state changes. | No embedded database connections in clients. No direct Tally or Excel writes from clients. |
| P8 | **Backend API is the sole gateway to PostgreSQL** | The Backend API is the **only** component authorized to read from or write to PostgreSQL. | A single gateway enforces validation, authorization, audit, and consistency on every mutation. | See [Backend Authority](#backend-authority) below. No exceptions without an accepted ADR. |

> **Non-Negotiable:** Principles P1, P3, P4, P5, P6, P7, and P8 cannot be waived without an accepted ADR and explicit stakeholder approval.

### Backend Authority

PostgreSQL is the authoritative datastore. The Backend API is the **only** gateway to the database.

**No component other than the Backend API may directly modify PostgreSQL** — unless an Architecture Decision Record explicitly approves an exception.

This prohibition applies without exception to:

| Component | Prohibited Action |
|-----------|-------------------|
| **Desktop applications** (Windows, macOS) | Direct PostgreSQL connection or write |
| **Android application** | Direct PostgreSQL connection or write |
| **Excel synchronization process** | Direct PostgreSQL connection or write |
| **Tally integration service** | Direct PostgreSQL connection or write |
| **Maintenance scripts** | Direct PostgreSQL write without Backend API (read-only diagnostics **TBD** per ADR) |
| **Import/export tools** | Direct PostgreSQL connection or write |
| **Dedicated server application** | Direct PostgreSQL connection or write — server calls Backend API like any other client |

Every inventory mutation — whether triggered by a user, an integration, a sync job, or a script — **must pass through the Backend API** unless an ADR documents an approved exception with scope, rationale, and audit requirements.

Integration services in `packages/integrations/` and the dedicated server in `apps/server/` are consumers of the Backend API, not alternate database writers. Detailed API access patterns are **TBD** in [architecture documentation](architecture/README.md) and [API documentation](api/README.md).

---

## 9. Data Ownership

Every dataset has exactly one owning system. No dataset may have competing authorities. When systems exchange data, ownership does not transfer — only synchronized copies or event notifications cross boundaries.

| Data | System Owner | Notes |
|------|--------------|-------|
| **Inventory** | WEBSTUDIO IMS (PostgreSQL via Backend API) | Authoritative record of stock state, serial numbers, and locations. See [inventory rules](business/inventory-rules.md) (**TBD**). |
| **Billing** | Tally ERP 9 | Invoices, receipts, accounts, tax. WEBSTUDIO IMS reads billing events; it does not own billing data. See [Tally integration](integrations/tally-erp9/README.md). |
| **Authentication** | WEBSTUDIO IMS (Backend API) | Sessions, tokens, credentials. Auth architecture **TBD** in [security documentation](security/auth-architecture.md). |
| **Users** | WEBSTUDIO IMS (Backend API) | User accounts, profiles, role assignments. Role definitions **TBD** in [user roles](business/user-roles.md). |
| **Audit Logs** | WEBSTUDIO IMS (PostgreSQL via Backend API) | Immutable record of inventory mutations and sensitive operations. Retention policy **TBD**. |
| **Excel Representation** | Excel file (derived) | Synchronized copy of inventory for business continuity. **Not authoritative.** Owned as a file by the business; content is derived from WEBSTUDIO IMS. See [Excel integration](integrations/excel/README.md). |
| **Images** | WEBSTUDIO IMS (Backend API) | Product images, attachments, and media metadata. Storage mechanism **TBD** in ADR. |
| **Settings** | WEBSTUDIO IMS (Backend API) | User preferences, theme selection, display options. |
| **Application Configuration** | WEBSTUDIO IMS (Backend API + deployment config) | System-level settings: locations, categories, sync schedules, `system_initialized`. Deployment values in [infra/](../infra/README.md) and [config/env/](../config/env/). |
| **Client Local Storage** | Client device (derived / ephemeral) | Server HTTPS URL, theme preference, window layout, and authentication tokens only. **No business data** (inventory, users, audit) persisted locally in Version 1. |

> **Rule:** If ownership is unclear, it is **TBD** until documented in a spec or ADR. Never assume shared ownership. Never write to another system's data domain without a defined integration interface.

---

## 10. Product Quality Standards

Product quality standards define the non-functional qualities every release must uphold. These apply to all platforms and all contributors.

### 10.1 Reliability

**What it means:** The system performs correctly and consistently under normal retail operating conditions — every day, every location, without silent data loss.

**Why it exists:** Inventory software that fails intermittently is worse than no software. Staff lose trust and revert to Excel.

**How to apply it:** Test business rules under failure conditions. Ensure sync and integration paths handle retries and partial failures. Define uptime aspirations in [operations documentation](operations/README.md) (**TBD**).

### 10.2 Maintainability

**What it means:** The codebase and documentation can be understood, modified, and extended by contributors who did not build the original system.

**Why it exists:** This project targets a ten-year maintenance horizon. Unmaintainable code becomes frozen legacy.

**How to apply it:** Follow [Maintainability Philosophy](#17-maintainability-philosophy). Write ADRs. Keep modules bounded. Prefer clarity over cleverness.

### 10.3 Performance

**What it means:** The system feels fast and responsive during real retail operations — especially search, lookup, and inventory updates.

**Why it exists:** Slow software on a shop floor is abandoned software.

**How to apply it:** Prioritize search and lookup paths. Measure before optimizing. Correctness always precedes speed — see [Performance Philosophy](#14-performance-philosophy) and [Performance Goals](#15-performance-goals).

### 10.4 Security

**What it means:** Data, credentials, and operations are protected against unauthorized access, tampering, and leakage.

**Why it exists:** Inventory data is commercially sensitive. Breach or tampering has direct financial impact.

**How to apply it:** Follow [Security Philosophy](#13-security-philosophy). Enforce authorization in the Backend API. Never store secrets in source control.

### 10.5 Usability

**What it means:** Retail staff can perform daily inventory tasks with minimal training, minimal errors, and minimal frustration.

**Why it exists:** The primary users are not software professionals. Poor usability equals poor inventory accuracy.

**How to apply it:** Follow [Design Principles](#7-design-principles). Test with real task scenarios. Validate against [user roles](business/user-roles.md) (**TBD**).

### 10.6 Accessibility

**What it means:** The application is usable by people with diverse visual, motor, and cognitive needs within practical retail constraints.

**Why it exists:** Inclusive design is a quality standard, not an optional enhancement. Accessibility gaps exclude staff and create compliance risk.

**How to apply it:** Follow [accessibility documentation](ui-ux/accessibility/) (**TBD**). Support theme contrast in Light and Dark modes. Keyboard navigation is mandatory on desktop.

### 10.7 Consistency

**What it means:** Terminology, behavior, visual language, and data presentation are uniform across platforms, screens, and integrations.

**Why it exists:** Inconsistency causes user error — especially when staff switch devices mid-shift.

**How to apply it:** Use the design system. Enforce shared terminology in [.ai/GLOSSARY.md](../.ai/GLOSSARY.md). API responses use consistent field names and error formats per [API documentation](api/README.md).

### 10.8 Observability

**What it means:** Developers and operators can diagnose problems, trace failures, and verify system health without guesswork.

**Why it exists:** Undiagnosable systems stay broken. In inventory, undiagnosed failures create silent data corruption.

**How to apply it:** Follow [Observability Philosophy](#18-observability-philosophy). Log integration events. Expose health checks. Preserve audit trails.

---

## 11. Engineering Principles

Engineering principles govern how the system is constructed.

### 11.1 Backend as the Authority

**What it means:** The backend API owns validation, business logic, authorization, and data persistence. It is the sole gateway to PostgreSQL. Clients, integrations, and server processes are consumers of the API — not alternate writers to the database.

**Why it exists:** Multiple clients (Windows, macOS, Android) and integrations (Tally, Excel) must behave identically. Logic or database access outside the Backend API will diverge and bypass audit controls.

**How to apply it:** Implement rules in the backend first. Write client and integration code to call API endpoints, not database connections. Review every new service for direct PostgreSQL access. See [Backend Authority](#backend-authority).

### 11.2 Explicit Over Implicit

**What it means:** Behavior should be readable from code, configuration, and documentation — not inferred from convention alone.

**Why it exists:** A ten-year codebase will outlive its original authors many times over. Implicit behavior becomes tribal knowledge, then becomes bugs.

**How to apply it:** Name things precisely. Document non-obvious behavior. Prefer explicit configuration over magic defaults.

### 11.3 Fail Clearly

**What it means:** When something goes wrong, the system should report what happened, what was affected, and what the user can do — not fail silently or with opaque errors.

**Why it exists:** Silent failures in inventory systems create ghost stock — the most expensive class of bug in retail.

**How to apply it:** Log errors with context. Surface actionable messages to users. Never swallow exceptions in inventory paths. See [Observability Philosophy](#18-observability-philosophy).

### 11.4 Test What Matters

**What it means:** Testing effort should concentrate on business rules, integrations, and data integrity — not on achieving coverage for its own sake.

**Why it exists:** Inventory correctness is the product. A UI unit test that passes while serial uniqueness breaks is worse than no test.

**How to apply it:** Every business rule in the backend should have automated tests. Integration tests should cover Tally and Excel sync paths. Coverage targets are **TBD** in [testing documentation](testing/strategy/coverage-targets.md).

### 11.5 Small, Reviewable Changes

**What it means:** Changes should be decomposable, reviewable, and reversible. Large, sweeping changes are discouraged.

**Why it exists:** Small changes reduce risk, simplify rollback, and make AI-assisted development safer.

**How to apply it:** One concern per pull request where possible. Reference spec and ADR IDs. Include documentation updates in the same change.

---

## 12. UI / UX Philosophy

UI/UX philosophy governs how the product presents itself to users. Detailed guidance lives in [UI/UX documentation](ui-ux/README.md) and [Design Principles](#7-design-principles).

### 12.1 Clarity Over Cleverness

**What it means:** Interfaces should be immediately understandable by store staff without training manuals.

**Why it exists:** The primary users are retail employees, not software engineers. Cognitive load directly reduces adoption.

**How to apply it:** Use plain language. Label buttons with verbs. Show current state before asking for action.

### 12.2 Consistency Across Platforms

**What it means:** Windows, macOS, and Android should share interaction patterns, terminology, and visual language wherever platform conventions allow.

**Why it exists:** Staff may use multiple devices in one day. Inconsistent UX creates errors.

**How to apply it:** Maintain a shared design system. Document platform-specific deviations in [UI/UX documentation](ui-ux/README.md).

**How to apply it:** Maintain a shared design system in [design/](../design/README.md). Document platform-specific deviations in [platform guidelines](ui-ux/platform-guidelines/).

### 12.3 Light and Dark Themes

**What it means:** Every application surface must support both Light and Dark themes, user-selectable.

**Why it exists:** Retail environments vary in lighting. Forced light or dark themes reduce usability and perceived quality.

**How to apply it:** Design all components for both themes from the start. Never treat theming as a post-release addition.

**How to apply it:** Design all components for both themes from the start. Never treat theming as a post-release addition. Theme tokens **TBD** in [design system](ui-ux/design-system/).

### 12.4 Responsive Feedback

**What it means:** Every user action receives visible acknowledgment — loading indicators, success confirmation, or error explanation.

**Why it exists:** Inventory operations happen in real time on a shop floor. Uncertainty about whether an action succeeded leads to duplicate entries.

**How to apply it:** Apply the patterns defined in [Design Principle 7.6](#76-responsive-feedback). Define component-level patterns in the design system.

---

## 13. Security Philosophy

### 13.1 Least Privilege

**What it means:** Users and services receive only the permissions required for their role — no more.

**Why it exists:** Inventory systems contain commercially sensitive data. Over-permissioned accounts increase breach impact.

**How to apply it:** Define roles in [business documentation](business/user-roles.md) (**TBD**). Enforce authorization in the backend on every endpoint. Never rely on client-side access control alone.

### 13.2 Defense in Depth

**What it means:** Security is enforced at multiple layers — network, application, API, and database.

**Why it exists:** A single point of failure in access control exposes the entire inventory database.

**How to apply it:** Authenticate every API request. Authorize every operation. Log access to sensitive operations. Security architecture details are **TBD** in [security documentation](security/README.md).

### 13.3 No Secrets in Source

**What it means:** Credentials, API keys, and connection strings never appear in the repository.

**Why it exists:** Source control history is permanent. Leaked credentials compromise the entire system.

**How to apply it:** Use environment variables via templates in [config/env/](../config/env/.env.example). Document required variables. Scan for secrets in CI when configured — see [security documentation](security/README.md).

---

## 14. Performance Philosophy

### 14.1 Perceived Speed Matters

**What it means:** The application must feel fast to a user holding a customer at the counter.

**Why it exists:** Slow software on a retail floor is abandoned software. Staff revert to Excel.

**How to apply it:** Search and lookup operations are the highest priority performance targets. Specific latency budgets are **TBD** in [Performance Goals](#15-performance-goals).

### 14.2 Correctness Before Speed

**What it means:** A slow correct answer is always preferable to a fast wrong one in inventory operations.

**Why it exists:** Performance optimizations that compromise data integrity create inventory ghosts and duplicates.

**How to apply it:** Optimize only after correctness is verified by tests. Never skip validation for speed.

### 14.3 Measure Before Optimizing

**What it means:** Performance work begins with measurement, not assumption.

**Why it exists:** Premature optimization adds complexity without guaranteed benefit.

**How to apply it:** Define performance benchmarks before release. Profile before refactoring. Benchmark methodology **TBD** in [testing documentation](testing/automation/).

---

## 15. Performance Goals

Performance goals are aspirations — not hard requirements. They guide design and review. Exact numeric targets will be defined in specifications before release (**TBD**). Correctness always takes precedence over speed — see [Section 14.2](#142-correctness-before-speed).

| Goal | Aspiration | Application |
|------|------------|-------------|
| **Fast search** | Serial number and model lookup feel instantaneous to the user | Optimize search indexes and API query paths first. Search is the primary interaction — see [Design Principle 7.2](#72-search-first). |
| **Responsive UI** | Screen transitions, form submissions, and list rendering feel immediate | Avoid blocking the UI thread. Show loading states immediately. Profile desktop and Android clients during development. |
| **Quick startup** | Applications launch and reach a usable state without noticeable delay | Defer non-critical initialization. Cache authentication state appropriately. Startup budgets **TBD**. |
| **Reliable synchronization** | Excel and Tally sync complete predictably without user intervention | Sync failures are visible, logged, and recoverable. Never silently skip sync. See [Integration Principles](#23-integration-principles). |
| **Minimal waiting time** | Users rarely stare at spinners during normal operations | Reduce round trips. Batch where appropriate without compromising audit granularity. |

> **Rule:** Performance optimization must never skip validation, audit logging, or authorization checks. A fast incorrect answer is a defect, not an optimization.

---

## 16. Scalability Philosophy

### 16.1 Scale Within Scope First

**What it means:** The immediate scaling target is the current business — three locations, one building, one Wi-Fi network. Design for this reality first.

**Why it exists:** Over-engineering for hypothetical scale wastes effort and introduces complexity that harms maintainability.

**How to apply it:** Size infrastructure for current and near-term load. Document scaling triggers that would prompt architectural review.

### 16.2 Enable Future Scale Without Redesign

**What it means:** Architectural choices should not prevent future multi-branch or cloud deployment, even if those are not implemented now.

**Why it exists:** The long-term vision includes multi-branch inventory and cloud deployment. Closing those doors now creates expensive rework later.

**How to apply it:** Use location-aware data models. Avoid hardcoded single-site assumptions. Keep deployment configuration external. Cloud architecture is **TBD**.

### 16.3 Horizontal Where It Counts

**What it means:** Components that will need independent scaling (API, database, sync services) should be separable.

**Why it exists:** Monolithic deployment is acceptable initially, but entangled components resist later separation.

**How to apply it:** Maintain clear boundaries between backend, server, and integration services as defined in [architecture documentation](architecture/README.md).

---

## 17. Maintainability Philosophy

### 17.1 Built for Ten Years

**What it means:** Every decision should assume this codebase will be maintained for at least ten years by people who did not write the original code.

**Why it exists:** Short-term shortcuts compound into long-term paralysis. The cost of maintenance exceeds the cost of initial development.

**How to apply it:** Prefer readable code over clever code. Document decisions in ADRs. Avoid dependencies that are unmaintained or likely to disappear.

### 17.2 One Repository, Clear Boundaries

**What it means:** The project uses a monorepo structure with explicit boundaries between applications and shared packages.

**Why it exists:** A single repository enables atomic changes across API, clients, and database. Clear boundaries prevent uncontrolled coupling.

**How to apply it:** Follow the structure defined in [ADR-0001](../adr/records/0001-monorepo-structure.md). Place shared logic in `packages/`. Place deployable code in `apps/`.

### 17.3 Deprecate, Do Not Delete

**What it means:** When removing or replacing functionality, mark it deprecated, document the migration path, and archive — do not silently delete history.

**Why it exists:** Long-lived systems need audit trails of their own evolution.

**How to apply it:** Use ADR status `Deprecated` or `Superseded`. Move obsolete documentation to [docs/archive/](archive/README.md).

---

## 18. Observability Philosophy

The software must always help developers and operators diagnose problems. Observability is not optional infrastructure — it is a product quality requirement. Detailed runbooks and tooling are **TBD** in [operations documentation](operations/README.md).

### 18.1 Structured Logging

**What it means:** All services emit logs in a consistent, machine-parseable format with contextual fields — timestamp, service, operation, user, correlation ID, and outcome.

**Why it exists:** Unstructured logs are unsearchable under pressure. When inventory sync fails at close of business, logs must answer "what happened" in minutes, not hours.

**How to apply it:** Define a logging schema **TBD** in [operations/logging/](operations/logging/). Integration services log every inbound and outbound event. Never log secrets or credentials.

### 18.2 Metrics

**What it means:** The system exposes quantitative indicators — request rates, error rates, sync latency, queue depth — that reveal health trends over time.

**Why it exists:** Logs tell you what happened once. Metrics tell you whether the system is degrading before users notice.

**How to apply it:** Define key metrics **TBD** in [operations/monitoring/](operations/monitoring/). Instrument the Backend API and integration services from the start.

### 18.3 Health Checks

**What it means:** Every deployable service exposes an endpoint or signal that confirms it is running and able to perform its core function.

**Why it exists:** Operators must distinguish "service is down" from "integration partner is unreachable" without reading source code.

**How to apply it:** Backend API, dedicated server, and integration workers each expose health checks. Health check contracts **TBD** in [deployment documentation](deployment/README.md).

### 18.4 Diagnostics

**What it means:** Developers can trace a single inventory operation from client action through API, business logic, database write, and integration side effects.

**Why it exists:** Inventory bugs often manifest hours after the triggering action. Without traceability, root cause analysis is guesswork.

**How to apply it:** Use correlation IDs across service boundaries. Document diagnostic procedures in [troubleshooting guide](development/troubleshooting/) (**TBD**).

### 18.5 Auditability

**What it means:** Every inventory mutation produces a durable, queryable audit record independent of application logs.

**Why it exists:** Logs rotate. Audit records must survive for the life of the business relationship with the data — disputes, investigations, and compliance depend on them.

**How to apply it:** Audit records are a data domain owned by WEBSTUDIO IMS — see [Data Ownership](#9-data-ownership). Audit schema **TBD** in [database documentation](database/README.md).

### 18.6 Monitoring

**What it means:** Operators receive proactive notification when the system deviates from healthy baselines — not only when users report failure.

**Why it exists:** Inventory sync failures during business hours have immediate financial impact. Reactive support is insufficient.

**How to apply it:** Define alert thresholds and escalation paths **TBD** in [support playbooks](operations/support-playbooks/) and [operations monitoring](operations/monitoring/).

---

## 19. Documentation Philosophy

### 19.1 Documentation Is Part of the Product

**What it means:** Documentation is not an afterthought. It is a deliverable with the same quality standards as code.

**Why it exists:** Undocumented systems cannot be maintained, onboarded to, or safely extended — by humans or AI.

**How to apply it:** Update documentation in the same pull request as code changes. A feature without documentation is incomplete.

### 19.2 Single Source of Truth per Topic

**What it means:** Every fact exists in exactly one canonical location. Other documents link to it.

**Why it exists:** Duplicated documentation diverges. Diverged documentation is worse than no documentation.

**How to apply it:** Business rules live in [docs/business/](business/README.md). Architecture decisions live in [adr/](../adr/README.md). API contracts live in [OpenAPI specs](api/openapi/). This document is the constitution; it links to detail, it does not duplicate it.

### 19.3 Write for the Next Reader

**What it means:** Documentation should be understandable by a competent developer or AI assistant who has never seen the project.

**Why it exists:** Turnover, growth, and AI-assisted development all introduce new readers constantly.

**How to apply it:** Include metadata headers per [documentation style guide](meta/style-guide.md). Define acronyms. Link to related documents. Use TBD rather than omitting unfinished sections.

---

## 20. AI Collaboration Philosophy

AI tools are first-class participants in the development of WEBSTUDIO IMS. They are force multipliers — not autonomous decision-makers.

### 20.1 General Rules for All AI Assistants

| Rule | Description |
|------|-------------|
| **Read before acting** | Always read this document, [AGENTS.md](../AGENTS.md), and relevant ADRs before making changes. |
| **Do not invent** | Do not invent API endpoints, database tables, business rules, or workflows. Use TBD or ask. |
| **Spec-first** | Extend OpenAPI specs and formal specifications before implementing features. |
| **Document alongside code** | Documentation updates are part of every change, not a follow-up task. |
| **Reference IDs** | Cite spec IDs, ADR numbers, and issue numbers in commits and pull requests. |
| **Respect boundaries** | Do not generate billing, accounting, or CRM functionality. Inventory only. |
| **No secrets** | Never generate, commit, or suggest hardcoded credentials. |
| **Backend authority** | Never generate direct PostgreSQL access from clients, integrations, or scripts. All mutations go through the Backend API. |

### 20.2 Cursor

**Role:** Primary in-IDE development assistant for code, documentation, refactoring, and repository navigation.

| Responsibility | Detail |
|----------------|--------|
| Code generation | Generate code within established patterns and approved ADRs only. |
| Refactoring | Improve code quality without altering business behavior unless spec-backed. |
| Documentation | Create and update docs following templates in `docs/meta/templates/`. |
| Navigation | Use [AGENTS.md](../AGENTS.md), `.ai/CONTEXT.md`, and `.cursor/rules/` as entry points. |
| Constraints | Follow [CONSTRAINTS.md](../.ai/CONSTRAINTS.md). Never bypass backend authority rules. |

**How to apply:** Cursor rules in `.cursor/rules/` enforce project-specific behavior. Developers should verify AI-generated code against this document before merging.

### 20.3 ChatGPT

**Role:** Strategic assistant for architecture discussion, specification drafting, research synthesis, and documentation authoring.

| Responsibility | Detail |
|----------------|--------|
| Architecture | Explore options and trade-offs. Output requires ADR before adoption. |
| Specifications | Draft functional and technical specs for human review. |
| Research | Synthesize findings into `docs/research/` documents. |
| Documentation | Author and refine prose documentation. |
| Constraints | Must not be treated as an authority on project state. Verify all outputs against the repository. |

**How to apply:** Use ChatGPT for thinking and drafting. Record decisions in ADRs. Transfer approved content into the repository — do not treat chat history as documentation.

### 20.4 Antigravity

**Role:** Autonomous task execution agent for well-defined, bounded development tasks.

| Responsibility | Detail |
|----------------|--------|
| Task execution | Execute clearly scoped tasks with explicit spec and ADR references. |
| Boundaries | Operate only within defined scope. Escalate ambiguity rather than assume. |
| Verification | All output must pass human review and CI before merge. |
| Constraints | Must not make architectural decisions. Must not merge without review. |

**How to apply:** Assign Antigravity tasks with explicit inputs (spec ID, ADR, file paths) and expected outputs. Treat its work as a draft until reviewed.

### 20.5 Future AI Assistants

Any future AI tool integrated into this project must:

1. Read this document and [AGENTS.md](../AGENTS.md) before any action.
2. Follow the prompt library in [docs/ai/prompt-library/](ai/prompt-library/README.md).
3. Operate under the same non-negotiable rules defined in [Section 30](#30-non-negotiable-rules).
4. Be documented in [docs/ai/](ai/README.md) when onboarded.

---

## 21. Coding Philosophy

### 21.1 Match the Repository

**What it means:** Code should look like it was written by one team. Follow existing patterns, naming, and structure.

**Why it exists:** Inconsistent codebases are harder to review, maintain, and safely modify with AI assistance.

**How to apply it:** Read surrounding code before writing new code. Follow [coding standards](development/conventions/coding-standards.md) (**TBD**).

### 21.2 Minimal Scope

**What it means:** Change only what the task requires. Resist drive-by refactors and scope expansion.

**Why it exists:** Large diffs hide defects, slow review, and increase merge risk.

**How to apply it:** One concern per change. If refactoring is needed, make it a separate pull request.

### 21.3 Types and Contracts

**What it means:** Data shapes should be explicit at system boundaries — API requests, responses, database schemas, and integration payloads.

**Why it exists:** Inventory systems fail at boundaries — where one component's assumptions meet another's.

**How to apply it:** Define API contracts in [OpenAPI specs](api/openapi/webstudio-ims-api-v1.yaml). Define database schemas in [database/migrations/](../database/migrations/). Define integration payloads in [integration specs](integrations/README.md). Implementation technology is **TBD** pending ADRs.

---

## 22. Architecture Philosophy

### 22.1 Decisions Are Recorded

**What it means:** Significant architectural choices are documented as ADRs before or alongside implementation.

**Why it exists:** Undocumented architecture becomes legend. Legend becomes inconsistency.

**How to apply it:** Create an ADR for technology choices, integration patterns, and structural changes. Reference ADR IDs in code and documentation. See [adr/README.md](../adr/README.md).

### 22.2 Integration at the Edges

**What it means:** External systems (Tally, Excel, and all future integrations) are accessed through dedicated integration packages, not scattered across application code.

**Why it exists:** Integration logic is the most volatile part of the system. Isolation limits blast radius.

**How to apply it:** Place Tally logic in [packages/integrations/tally/](../packages/integrations/tally/). Place Excel logic in [packages/integrations/excel/](../packages/integrations/excel/). Future integrations follow the same pattern — see [Integration Principles](#23-integration-principles).

### 22.3 Event-Aware, Not Event-Dependent

**What it means:** The system should be capable of reacting to billing and sync events without requiring real-time event infrastructure on day one.

**Why it exists:** Event-driven architecture may be appropriate later, but premature infrastructure adds complexity.

**How to apply it:** Design for eventual event support. Initial sync mechanisms are **TBD** in [architecture](architecture/README.md) and [integration specs](integrations/README.md).

### 22.4 Modules Communicate Through Defined Interfaces

**What it means:** Applications and packages interact only through published APIs, contracts, and package exports — never through internal implementation details.

**Why it exists:** Direct access to internal modules creates hidden coupling that breaks during refactoring.

**How to apply it:** Define package public APIs explicitly. Clients call the Backend API. Packages expose documented entry points. No reaching into internal modules.

### 22.5 No Circular Dependencies

**What it means:** The dependency graph flows in one direction: `apps/` depend on `packages/`; `packages/` do not depend on `apps/`. Integration packages do not depend on client applications.

**Why it exists:** Circular dependencies make the codebase untestable, unbuildable, and unmaintainable.

**How to apply it:** Enforce dependency direction in code review. CI dependency checks **TBD**. Document allowed dependencies in [workspace structure](development/monorepo/workspace-structure.md).

### 22.6 Shared Logic Belongs in Shared Packages

**What it means:** Code used by more than one application lives in `packages/`, not duplicated across `apps/`.

**Why it exists:** Duplicated logic diverges. Shared packages provide a single place to fix, test, and evolve common behavior.

**How to apply it:** Before adding code to an app, ask: *Will another app need this?* If yes, place it in the appropriate package under [packages/](../packages/README.md).

### 22.7 Business Logic Must Never Leak into UI

**What it means:** Client applications render state and capture input. They do not validate business rules, compute inventory outcomes, or decide authorization.

**Why it exists:** UI-layer logic is untested, unaudited, and platform-specific. It will diverge across Windows, macOS, and Android.

**How to apply it:** Client-side validation is for UX convenience only (format hints, required fields). Authoritative validation lives in the Backend API. See [Section 11.1](#111-backend-as-the-authority).

### 22.8 Integration Code Remains Isolated

**What it means:** Code that communicates with external systems is confined to integration packages and services — never embedded in UI or core business logic.

**Why it exists:** External systems change independently. Isolated integration code can be updated, tested, and replaced without touching the core.

**How to apply it:** All Tally, Excel, and future integration code (barcode scanners, cloud sync, additional ERP systems) lives under [packages/integrations/](../packages/integrations/README.md).

### 22.9 Architecture Decisions Require ADRs

**What it means:** No significant structural, technology, or boundary decision is adopted without an ADR in `Accepted` or `Proposed` status.

**Why it exists:** Verbal decisions evaporate. ADRs create accountability and a durable record for future contributors and AI assistants.

**How to apply it:** Use [adr/template.md](../adr/template.md). Submit ADRs for review before implementation begins.

### 22.10 Technology Selection

Approved technologies at the time of this document:

| Technology | Status | Role |
|------------|--------|------|
| PostgreSQL | **Approved** | Authoritative datastore — accessed exclusively via Backend API |
| Tally ERP 9 | **Approved** (external) | Billing and accounting |
| Excel | **Approved** (external) | Synchronized inventory representation |

All other technology choices — backend framework, desktop framework, mobile framework, server runtime — are **TBD** pending research and ADRs. See [docs/research/](research/README.md).

---

## 23. Integration Principles

Integration principles govern how WEBSTUDIO IMS connects to external systems — Tally ERP 9 and Excel today; barcode scanners, cloud sync, additional ERP systems, and other services in the future. Detailed integration specifications are **TBD** in [docs/integrations/](integrations/README.md).

| # | Principle | Meaning | Why | Application |
|---|-----------|---------|-----|-------------|
| I1 | **Every integration must be isolated** | Each external system is accessed through its own integration package with a defined boundary. | External systems change independently. Isolation limits blast radius. | One package per integration in [packages/integrations/](../packages/integrations/README.md). No cross-integration coupling. |
| I2 | **Every integration must have logging** | All inbound and outbound integration events are logged with structured context. | Integration failures are the most common production incidents. Logs are the first diagnostic tool. | Follow [Observability Philosophy](#18-observability-philosophy). Log payloads at appropriate detail level — never log secrets. |
| I3 | **Every integration must be testable** | Integration logic can be tested with mocks, fixtures, and recorded responses without live external systems. | Untestable integrations ship with undetected bugs. CI must not depend on Tally or Excel being available. | Use sample data from [docs/examples/](examples/README.md). Integration test strategy **TBD** in [testing documentation](testing/README.md). |
| I4 | **Integrations never bypass backend rules** | Integration services call the Backend API to mutate inventory. They do not write directly to PostgreSQL. | Direct database writes bypass validation, authorization, and audit. | See [Backend Authority](#backend-authority). Integration services are API clients, not database clients. |
| I5 | **Integrations communicate through defined interfaces** | Each integration exposes a documented interface — input format, output format, error conditions, retry behavior. | Ad hoc integration code is unmaintainable and unreplacable. | Document interfaces in [integration specs](integrations/README.md) and [specs/](../specs/README.md). |
| I6 | **Integrations must fail safely** | When an external system is unavailable, WEBSTUDIO IMS continues operating with clear error state — no silent data corruption. | Tally or Excel may be offline during business hours. Failure must be visible and recoverable. | Define retry, queue, and manual reconciliation procedures **TBD**. Never partially apply a sync. |

> **Future integrations** — barcode scanners, cloud sync, additional ERP systems — must follow these same principles. Each requires a spec, an isolated package, and an ADR before implementation.

---

## 24. Deployment Philosophy

### 24.1 On-Premise First

**What it means:** The initial deployment target is on-premise within the business building, on the existing Wi-Fi network.

**Why it exists:** The business operates from a single building with local infrastructure. Cloud deployment is a future capability, not a day-one requirement.

**How to apply it:** Design for local network deployment. Document installation and upgrade procedures. Cloud architecture is **TBD**.

### 24.2 Reproducible Deployments

**What it means:** Deployments should be scripted, documented, and repeatable — not dependent on manual steps remembered by one person.

**Why it exists:** Undocumented deployment processes become single points of failure.

**How to apply it:** Maintain deployment scripts in [infra/](../infra/README.md). Document procedures in [deployment documentation](deployment/README.md).

### 24.3 Safe Upgrades

**What it means:** Upgrading the system must not corrupt inventory data. Rollback paths must exist.

**Why it exists:** Inventory data loss is catastrophic and potentially unrecoverable.

**How to apply it:** Database migrations must be backward-compatible or paired with rollback scripts. Test upgrades against production-like data before deployment. See [migration runbook](deployment/database/migration-runbook.md).

### 24.4 Server Initialization

**What it means:** The Dedicated Server PC is installed **once**. During installation the Backend checks whether the system has already been initialized. Initialization state is stored as a dedicated `system_settings` key — `system_initialized` — **not** inferred from whether a Main Admin user exists.

**Why it exists:** A reliable, explicit initialization flag prevents the first-time setup wizard from reappearing after successful setup and gives clients a single API signal (`GET /api/v1/setup/status`) to decide between setup and login.

**How to apply it:**

| Phase | Behaviour |
|-------|-----------|
| **Fresh database** | Seed reference data (brands, locations) and `system_initialized = false`. **Do not** seed a Main Admin user. |
| **First-time setup** | When `system_initialized = false`, present the First-Time Setup Wizard (Company Name, Main Admin Name, Username, Password, Confirm Password). Passwords are stored only as **bcrypt** hashes on the server. |
| **After setup** | Create the Main Admin user; set `system_initialized = true` and persist `company_name`. The wizard must not appear again unless the database is intentionally reinitialized. |
| **Reinitialization** | Deliberate operator action only (restore empty database or documented reset procedure) — never automatic. |

### 24.5 Client Onboarding

**What it means:** Desktop and Android clients are installed on staff workstations and devices. **Client installations never create users.** Clients connect to the Backend, check setup status, then show either the First-Time Setup Wizard (server not initialized — typically only from the first client after server install) or the Login screen.

**Why it exists:** User accounts and credentials are authoritative on the server. Separating server install from client install allows multiple clients to join an already-initialized system without duplicating admin creation logic on each device.

**How to apply it:**

| Step | Client behaviour |
|------|------------------|
| **1. First launch** | Attempt automatic server discovery on the LAN. |
| **2. One server found** | Display server information; ask for confirmation. |
| **3. Multiple servers found** | Let the user select one. |
| **4. Discovery fails** | Automatically switch to Manual Server Configuration (HTTPS URL, Test Connection, Save Configuration). |
| **5. After connection** | Call `GET /api/v1/setup/status`. If initialized → Login screen. If not → First-Time Setup Wizard. |
| **6. Authentication** | Users authenticate **only** against the Backend. Clients store tokens and connection settings locally — **never** business inventory data. |

**Future:** Automatic discovery may use mDNS / Bonjour or an equivalent LAN discovery protocol. Version 1 documents the workflow; protocol choice is **TBD** in an ADR.

---

## 25. Product Scope

### 25.1 Current Scope (v1 — TBD Detail)

The initial release scope will be defined in product requirements documentation. At this stage, the following are in scope at a high level:

| Area | In Scope |
|------|----------|
| Inventory tracking | Laptop inventory across three locations |
| Serial number management | Globally unique serial number registry |
| Inventory movements | Auditable transfers between locations |
| Search | First-class search across inventory |
| Tally integration | React to billing events without replacing Tally |
| Excel synchronization | Export/sync inventory representation to Excel |
| Authentication & authorization | Role-based access (**roles TBD**) |
| Desktop applications | Windows and macOS |
| Mobile application | Android |
| Server application | Dedicated on-premise server |
| Backend API | Central authority for all clients |
| Theming | Light and Dark themes |

Detailed functional requirements are **TBD** in [product requirements](product/requirements/prd-v1.0-inventory-core.md).

### 25.2 Platforms

| Platform | Role |
|----------|------|
| Windows Desktop | Primary staff interface — **TBD** |
| macOS Desktop | Primary staff interface — **TBD** |
| Android | Mobile inventory operations — **TBD** |
| Dedicated Server | Sync, scheduling, integration hosting — **TBD** |
| Backend API | Business logic, validation, persistence — sole gateway to PostgreSQL | |
| PostgreSQL | Authoritative datastore — no direct client or integration access | |

---

## 26. Out of Scope

The following are explicitly excluded from WEBSTUDIO IMS. They must not be designed, prototyped, or implied in any surface without an accepted ADR and stakeholder approval.

| Category | Rationale |
|----------|-----------|
| Billing and invoicing | Owned by Tally ERP 9 |
| Accounting and ledger management | Owned by Tally ERP 9 |
| Customer relationship management (CRM) | Different product category |
| Payment processing | Billing domain |
| Tax calculation | Billing domain |
| Payroll and HR | Unrelated to inventory |
| Replacing Tally ERP 9 | Business constraint |
| Replacing Excel entirely (immediately) | Excel remains as synchronized representation during transition |
| E-commerce / online storefront | Not a current business need |
| General ERP functionality | WEBSTUDIO IMS is an IMS, not an ERP |

---

## 27. Business Constraints

| Constraint | Detail |
|------------|--------|
| **Tally is mandatory** | Billing remains in Tally ERP 9 indefinitely. |
| **Single building** | All locations are in one building on shared Wi-Fi. |
| **Real business operations** | This is production software for daily retail operations — not a demo. |
| **Staff-driven adoption** | Software must be usable by retail staff without extensive training. |
| **Operational continuity** | Deployment must not disrupt store operations during business hours. **Maintenance windows TBD.** |
| **Excel transition** | Excel remains in use as a synchronized view. Deprecation timeline is **TBD**. |
| **Data ownership** | Inventory data belongs to the business. Export and backup capabilities are required. See [Data Ownership](#9-data-ownership). |

Business workflows, inventory rules, and role definitions are **TBD** in [business documentation](business/README.md).

---

## 28. Technical Constraints

| Constraint | Detail |
|------------|--------|
| **PostgreSQL only** | PostgreSQL is the sole authoritative data store. No client-side databases for inventory state. |
| **Backend API gateway** | The Backend API is the **only** gateway to PostgreSQL. No desktop app, Android app, Excel sync, Tally integration, maintenance script, or import/export tool may write directly to the database. Exceptions require an ADR. |
| **Backend authority** | All business rules enforced server-side. |
| **API-only client access** | Desktop, Android, server, and integration services communicate with inventory data exclusively through the Backend API. |
| **On-premise deployment** | Initial deployment is local to the business network. |
| **Shared Wi-Fi** | All locations connect via the same network. Network topology details are **TBD**. |
| **Audit trail** | Every inventory mutation must be auditable. |
| **Serial uniqueness** | Enforced at database and API level. |
| **Technology approval** | No framework or library is approved until documented in an accepted ADR. |
| **Monorepo** | Single repository per [ADR-0001](../adr/records/0001-monorepo-structure.md). |
| **Integration isolation** | All external system access through [packages/integrations/](../packages/integrations/README.md) per [Integration Principles](#23-integration-principles). |

---

## 29. Future Expansion Guidelines

Future modules are anticipated but not scheduled. When expansion occurs, follow these guidelines:

| Module | Guideline |
|--------|-----------|
| **Warranty** | Extend inventory records with warranty metadata. Do not create a parallel product registry. |
| **Service Center** | Attach service history to existing serial numbers. Maintain audit trail. |
| **Repairs** | Model as inventory state changes, not a separate system. |
| **Accessories** | Extend category model. Serial uniqueness rules may differ — **TBD** in business rules. |
| **Printers** | Treat as inventory category with distinct attributes. |
| **Multi-Branch** | Extend location model. Avoid single-site assumptions in current design. |
| **Cloud Deployment** | Extract deployment configuration. Keep application boundaries clean. Architecture **TBD**. |

> **Rule:** Future modules are added by extension, not by parallel systems. If a proposed module requires a separate database, direct PostgreSQL access, or bypasses the Backend API, it requires an ADR.

Detailed future architecture notes live in [docs/architecture/future/](architecture/future/).

---

## 30. Non-Negotiable Rules

These rules cannot be violated under any circumstance without an accepted ADR and explicit stakeholder approval.

| # | Rule |
|---|------|
| N1 | **PostgreSQL is the single source of truth for inventory data.** |
| N2 | **The Backend API is the only gateway to PostgreSQL.** No desktop app, Android app, Excel sync, Tally integration, maintenance script, or import/export tool may directly modify the database. |
| N3 | **Excel is only a synchronized representation — never authoritative.** |
| N4 | **Tally ERP 9 remains the billing system. WEBSTUDIO IMS does not bill.** |
| N5 | **Desktop and Android applications must never bypass the backend API.** |
| N6 | **Every business rule must exist only once — in the backend.** |
| N7 | **Serial numbers must always be globally unique.** |
| N8 | **Every inventory movement must be auditable.** |
| N9 | **The software must support both Light and Dark themes.** |
| N10 | **The software must look and behave like a premium SaaS application.** |
| N11 | **Simplicity takes precedence over feature overload.** |
| N12 | **Search is a first-class feature.** |
| N13 | **Nothing should be hardcoded if it can reasonably be configured.** |
| N14 | **The software must be maintainable for at least 10 years.** |
| N15 | **Documentation is part of the product — not optional.** |
| N16 | **No secrets, credentials, or API keys in source control.** |
| N17 | **No business rule, API endpoint, or database table may be invented without a spec or ADR.** |
| N18 | **Every integration must be isolated, logged, testable, and fail safely.** |

---

## 31. Guiding Principles for Contributors

Whether you are a developer, architect, designer, QA engineer, or AI assistant, follow these principles on every contribution:

1. **Read this document first.** Before your first change and whenever you are uncertain.
2. **Understand the business context.** Inventory software exists to serve retail operations, not the other way around.
3. **Respect system boundaries.** Tally bills. PostgreSQL stores (via Backend API only). Excel syncs. Clients display. Integrations call the API.
4. **Identify your lifecycle stage.** Know whether you are writing requirements, specs, architecture, code, tests, or runbooks — see [Product Lifecycle](#product-lifecycle).
5. **Ask when uncertain.** Use TBD. Do not guess business rules or workflows.
6. **Record decisions.** If you make an architectural choice, write an ADR.
7. **Keep changes small.** Small pull requests are reviewable pull requests.
8. **Test business rules.** Inventory correctness is the product.
9. **Update documentation.** If you change behavior, change docs in the same commit.
10. **Think in ten years.** Will this decision help or harm the maintainer in 2036?
11. **Protect the user.** Retail staff are the primary users. Design for their reality.
12. **Never bypass the Backend API.** No direct PostgreSQL access without an ADR.

---

## 32. Definition of Done

A task, feature, or change is **done** when all of the following are satisfied:

| Criterion | Required |
|-----------|----------|
| Functional requirements met per spec | Yes |
| Business rules implemented in backend only | Yes |
| Automated tests for business logic | Yes |
| API contract updated (if applicable) | Yes |
| Database migration created (if applicable) | Yes |
| Documentation updated | Yes |
| ADR created (if architectural) | Yes |
| Code reviewed and approved | Yes |
| No non-negotiable rules violated | Yes |
| No direct PostgreSQL access outside Backend API | Yes |
| Integration changes follow Integration Principles (Section 23) | Yes — when applicable |
| Light and Dark themes verified (if UI change) | Yes |
| Search functionality unaffected or improved (if relevant) | Yes |
| Audit trail preserved or extended | Yes |
| CI checks passing | Yes — when CI is configured |

Specific checklists per platform and feature type are **TBD** in [testing documentation](testing/README.md).

---

## 33. Success Criteria

The project succeeds when the business can answer "yes" to these questions:

| # | Question |
|---|----------|
| S1 | Can staff find any laptop by serial number in seconds? |
| S2 | Does inventory in WEBSTUDIO IMS match physical stock across all three locations? |
| S3 | Is every inventory movement traceable to a person, time, and reason? |
| S4 | Does billing in Tally automatically reflect in inventory without manual Excel updates? |
| S5 | Has manual Excel inventory maintenance been eliminated or reduced to review-only? |
| S6 | Do staff prefer WEBSTUDIO IMS over the previous manual process? |
| S7 | Can a new developer or AI assistant understand the system from documentation alone? |
| S8 | Can the system be upgraded without inventory data loss? |
| S9 | Does the software feel premium, fast, and reliable? |
| S10 | Can future modules (warranty, service center, multi-branch) be added without redesign? |

Quantitative targets (search latency, sync frequency, uptime) are **TBD** in [Performance Goals](#15-performance-goals) and [testing documentation](testing/README.md).

---

## 34. Glossary of Core Terms

| Term | Definition |
|------|------------|
| **WEBSTUDIO IMS** | WEBSTUDIO Inventory Management System — this product. |
| **IMS** | Inventory Management System. |
| **Tally ERP 9** | External billing and accounting software. System of record for sales. Not replaced by WEBSTUDIO IMS. |
| **PostgreSQL** | Authoritative database for all inventory data. Single source of truth. Accessed exclusively via Backend API — never directly by clients or integrations. |
| **Backend API Gateway** | The sole authorized interface for reading from and writing to PostgreSQL. All inventory mutations pass through it. |
| **Excel** | External spreadsheet used as a synchronized representation of inventory. Not authoritative. |
| **Serial Number** | Unique identifier assigned to an individual laptop unit. Must be globally unique within WEBSTUDIO IMS. |
| **Location** | A physical place where inventory is held or displayed: ASUS Exclusive Store, WEBSTUDIO Multi-brand Store, or Warehouse/Godown. |
| **Inventory Movement** | Any transfer, receipt, sale reflection, or adjustment that changes inventory state or location. Must be auditable. |
| **Audit Trail** | Immutable record of who performed an action, what changed, when, and why. |
| **Backend API** | Central service that enforces business rules, authorization, and data persistence. The only gateway to PostgreSQL. |
| **Client** | Desktop (Windows, macOS) or Android application that communicates with the backend API. |
| **Dedicated Server** | On-premise application hosting sync, scheduling, and integration services. |
| **Synchronization** | Process of aligning inventory data between PostgreSQL and external representations (Excel). Direction and conflict rules **TBD**. |
| **ADR** | Architecture Decision Record — binding document for significant technical decisions. |
| **Spec** | Formal specification (functional, technical, integration) identified by prefix and number (e.g., FS-001). |
| **Godown** | Warehouse / storage area within the building. |
| **Integration** | A bounded service or package connecting WEBSTUDIO IMS to an external system via defined interfaces. Must not bypass the Backend API. |
| **Theme** | Visual mode of the application interface: Light or Dark. Both are required. |

Extended business terminology is **TBD** in [business glossary](business/business-glossary.md) and [.ai/GLOSSARY.md](../.ai/GLOSSARY.md).

---

## 35. References to Related Documents

| Document | Path | Status |
|----------|------|--------|
| **This document** | `docs/PROJECT_BIBLE.md` | Active — v1.2 |
| Documentation Index | [docs/README.md](README.md) | Active |
| AI Agent Instructions | [AGENTS.md](../AGENTS.md) | Active |
| AI Context | [.ai/CONTEXT.md](../.ai/CONTEXT.md) | Draft |
| AI Constraints | [.ai/CONSTRAINTS.md](../.ai/CONSTRAINTS.md) | Draft |
| AI Glossary | [.ai/GLOSSARY.md](../.ai/GLOSSARY.md) | Draft |
| AI Context Guide | [docs/ai/context-guide.md](ai/context-guide.md) | Draft |
| AI Prompt Library | [docs/ai/prompt-library/](ai/prompt-library/README.md) | Draft |
| ADR Index | [adr/README.md](../adr/README.md) | Active |
| ADR-0001: Monorepo Structure | [adr/records/0001-monorepo-structure.md](../adr/records/0001-monorepo-structure.md) | Proposed |
| ADR-0010: Authentication & Initialization | [adr/ADR-0010-authentication-and-initialization.md](../adr/ADR-0010-authentication-and-initialization.md) | Accepted |
| ADR-0011: Tally Integration Strategy | [adr/ADR-0011-tally-integration-strategy.md](../adr/ADR-0011-tally-integration-strategy.md) | Accepted |
| Architecture Overview | [docs/architecture/](architecture/README.md) | Draft |
| Design System (future) | [docs/ui-ux/design-system/](ui-ux/design-system/) | Draft |
| Business Documentation | [docs/business/](business/README.md) | Draft |
| Current Workflow | [docs/business/current-workflow.md](business/current-workflow.md) | Draft — TBD |
| Inventory Rules | [docs/business/inventory-rules.md](business/inventory-rules.md) | Draft — TBD |
| User Roles | [docs/business/user-roles.md](business/user-roles.md) | Draft — TBD |
| Tally Integration | [docs/integrations/tally-erp9/](integrations/tally-erp9/README.md) | Draft |
| Excel Integration | [docs/integrations/excel/](integrations/excel/README.md) | Draft |
| API Documentation | [docs/api/](api/README.md) | Draft |
| OpenAPI Spec (v1) | [docs/api/openapi/webstudio-ims-api-v1.yaml](api/openapi/webstudio-ims-api-v1.yaml) | Draft |
| Database Documentation | [docs/database/](database/README.md) | Draft |
| UI/UX Documentation | [docs/ui-ux/](ui-ux/README.md) | Draft |
| Development Guide | [docs/development/](development/README.md) | Draft |
| Deployment Guide | [docs/deployment/DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md) | Active — v1.0 |
| Testing Strategy | [docs/testing/](testing/README.md) | Draft |
| Security Documentation | [docs/security/](security/README.md) | Draft |
| Operations / Monitoring | [docs/operations/](operations/README.md) | Draft |
| Research | [docs/research/](research/README.md) | Draft |
| Product Requirements (v1) | [docs/product/PRODUCT_REQUIREMENTS.md](product/PRODUCT_REQUIREMENTS.md) | Active — v1.6 |
| Technology Stack | [docs/TECH_STACK.md](TECH_STACK.md) | Active — TS-001 v1.2 |
| Product Requirements (legacy stub) | [docs/product/requirements/prd-v1.0-inventory-core.md](product/requirements/prd-v1.0-inventory-core.md) | Superseded by PRODUCT_REQUIREMENTS.md |
| Product Roadmap | [docs/product/vision/roadmap.md](product/vision/roadmap.md) | Draft |
| Future Architecture | [docs/architecture/future/](architecture/future/) | Draft |
| Documentation Style Guide | [docs/meta/style-guide.md](meta/style-guide.md) | Draft |
| Contributing Guide | [CONTRIBUTING.md](../CONTRIBUTING.md) | Active |
| Changelog | [CHANGELOG.md](../CHANGELOG.md) | Active |

---

> **Document Authority:** This Project Bible is the highest-level governing document in the WEBSTUDIO IMS repository. It is superseded only by accepted ADRs for specific technical decisions and by approved specifications for specific feature requirements. When in doubt, follow this document, record the decision, and update related docs.

*WEBSTUDIO IMS Team — 2026*
