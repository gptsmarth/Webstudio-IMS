---
Title: WEBSTUDIO IMS — System Architecture
Version: 1.10
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/PROJECT_BIBLE.md, docs/product/PRODUCT_REQUIREMENTS.md, docs/TECH_STACK.md, adr/README.md
---

# WEBSTUDIO IMS — System Architecture

| Attribute | Value |
|-----------|-------|
| **Document ID** | ARCH-001 |
| **Version** | 1.10 |
| **Status** | Active — **Tally synchronization architecture fully frozen** including inventory matching strategy |
| **Governing Documents** | [PROJECT_BIBLE.md](PROJECT_BIBLE.md), [PRODUCT_REQUIREMENTS.md](product/PRODUCT_REQUIREMENTS.md), [TECH_STACK.md](TECH_STACK.md) |
| **Purpose** | Definitive engineering blueprint for building and maintaining WEBSTUDIO IMS |

> **Authority:** This document defines how WEBSTUDIO IMS is structured, how components communicate, where business logic lives, and how the system evolves. It must not contradict the Project Bible, PRD, or approved Technology Stack. Implementation details (API endpoints, database tables, source files) are defined in downstream specifications — not here.

---

## Version History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.10 | 2026-06-27 | WEBSTUDIO IMS Team | **Inventory matching strategy frozen:** Serial Number authoritative; product model verification informational only; model normalization; `product_model_mismatch` warning notification. |
| 1.9 | 2026-06-27 | WEBSTUDIO IMS Team | **Final Tally sync freeze:** processing status lifecycle; partial retry; crash recovery; line-level transactions; table responsibilities. |
| 1.8 | 2026-06-27 | WEBSTUDIO IMS Team | **Audit-only history:** removed `InventoryMovement` module; location transfers update `current_location_id` + `audit_logs` only; `AuditRecorder` is single source of truth; Sprint 1E = `0005_audit_logs`, `0006_audit_log_description`. |
| 1.8 | 2026-06-27 | WEBSTUDIO IMS Team | **Frozen** Tally synchronization rules: invoice-level idempotency; AVAILABLE-only matching; Tally Sync Log; notification categories; line-independent processing. |
| 1.7 | 2026-06-27 | WEBSTUDIO IMS Team | Finalized Tally ERP 9 synchronization: read-only invoices; multi-company sync; invoice line matching; Tally Sync Dashboard; notifications; manual mark-as-sold (Admin/Main Admin only). |
| 1.6 | 2026-06-27 | WEBSTUDIO IMS Team | Server initialization and client onboarding: `system_initialized` setting; first-time setup wizard; client discovery and manual configuration; login gated on setup status; Main Admin-only user management. |
| 1.5 | 2026-06-27 | WEBSTUDIO IMS Team | Migration roadmap: `0005` movement → `0006` audit → `0007` users → `0008` ownership columns (deferred until `users` exists). |
| 1.4 | 2026-06-27 | WEBSTUDIO IMS Team | Authentication & audit strategy: Salesperson movement; operational ownership fields on business entities; enriched audit log with actor snapshots and movement fields. |
| 1.3 | 2026-06-27 | WEBSTUDIO IMS Team | Synchronized with Sprint 1D: `current_location_id` on inventory; `reserved` status; Product Model structured specs; movement history via InventoryMovement; removed inventory `configuration`/`row_version`. |
| 1.2 | 2026-06-27 | WEBSTUDIO IMS Team | Business model refinements: Product Model Active/Archived lifecycle; mandatory Color on inventory items; expanded search dimensions; excluded Purchase Date/Cost/Remarks from V1. |
| 1.1 | 2026-06-27 | WEBSTUDIO IMS Team | ARB finalization. HTTPS mandatory in production (internal CA); sync job orchestration; service boundaries; domain mapping; idempotency; threat model; audit enrichment; deployment workflow; engineering conventions. |
| 1.0 | 2026-06-27 | WEBSTUDIO IMS Team | Initial system architecture. Complete engineering blueprint for on-premise Windows deployment, backend authority model, integration boundaries, security, and future evolution. |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architectural Goals](#2-architectural-goals)
3. [System Context](#3-system-context)
4. [High-Level Architecture](#4-high-level-architecture)
5. [Architectural Principles](#5-architectural-principles)
6. [Component Design](#6-component-design)
7. [Backend Architecture](#7-backend-architecture)
8. [Desktop Architecture](#8-desktop-architecture)
9. [Android Architecture](#9-android-architecture)
10. [Database Architecture](#10-database-architecture)
11. [Authentication & Authorization](#11-authentication--authorization)
12. [Inventory Engine](#12-inventory-engine)
13. [Search Engine](#13-search-engine)
14. [Synchronization Services](#14-synchronization-services)
15. [Barcode Integration](#15-barcode-integration)
16. [Security Architecture](#16-security-architecture)
17. [Logging & Observability](#17-logging--observability)
18. [Failure & Recovery](#18-failure--recovery)
19. [Configuration Management](#19-configuration-management)
20. [Deployment Architecture](#20-deployment-architecture)
    - [20.8 Installation & Deployment Workflow](#208-installation--deployment-workflow)
    - [20.9 Service Startup & Shutdown Order](#209-service-startup--shutdown-order)
    - [20.10 Update Strategy](#2010-update-strategy)
    - [20.11 Server Initialization & Client Onboarding](#2011-server-initialization--client-onboarding)
21. [Performance Strategy](#21-performance-strategy)
22. [Future Evolution](#22-future-evolution)
    - [22.5 Engineering Conventions](#225-engineering-conventions)
    - [22.6 Deferred Future Enhancements](#226-deferred-future-enhancements)
23. [Architecture Decision Summary](#23-architecture-decision-summary)
24. [Architecture Readiness Assessment](#24-architecture-readiness-assessment)

---

## 1. Executive Summary

WEBSTUDIO IMS is a commercial, on-premise inventory management platform for a laptop retail business operating three locations within one building. The system replaces manual Excel tracking while preserving **Tally ERP 9** as the sole billing system and **PostgreSQL** as the authoritative inventory datastore.

### 1.1 System in One Paragraph

Staff use **Electron desktop applications** (Windows and macOS) and a **React Native Android application** to search, register, move, and review laptop inventory. All clients communicate exclusively over **HTTPS** with a **FastAPI Backend API** running on a **dedicated Windows 11 Pro server PC** within the office Wi-Fi network. The Backend API is the **only component authorized to read from or write to PostgreSQL** — no client, sync worker, or integration may access the database directly. Two background **Windows Services** — Excel Synchronization and Tally Integration — are API clients only: they submit and retrieve data through authenticated REST endpoints. **Excel** receives one-way synchronized exports produced by the Excel Sync worker. **Tally** drives sale reflection when billing events are detected and processed through the API.

### 1.2 Architectural Stance

| Decision | Choice |
|----------|--------|
| **Deployment** | On-premise, office LAN only — no cloud in Version 1 |
| **Server OS** | Windows 11 Pro dedicated server PC |
| **Backend style** | Layered architecture with hexagonal integration boundaries |
| **Authority model** | Backend-first; thin clients; PostgreSQL as single source of truth |
| **Transport (production)** | **HTTPS** + JSON + JWT — mandatory; TLS terminated at Backend API (internal CA certificate) |
| **Transport (development)** | HTTP permitted on `localhost` only for local developer workstations |
| **Transport (remote access — future)** | HTTPS with public or VPN-terminated certificates; reverse proxy ADR if required |
| **Integrations** | Isolated services; fail safely; logged; testable |
| **Maintainability horizon** | 10+ years |

### 1.3 What This Document Defines

This architecture explains **what exists**, **why it exists**, **how components interact**, **where business logic lives**, **how security is enforced**, **how failures are handled**, and **how the system expands** without redesign. It is written for an experienced engineering team to begin database design and implementation without additional **structural** clarification — subject to the open decisions and integration POC items identified in [Section 24](#24-architecture-readiness-assessment).

### 1.4 Transport & TLS Policy

| Environment | Protocol | Requirement |
|-------------|----------|-------------|
| **Production** (store LAN) | **HTTPS only** | Mandatory — satisfies NFR-SEC-01 |
| **Development** (local) | HTTP on `localhost` | Permitted for developer convenience |
| **Future remote access** | HTTPS | Public CA or VPN; optional reverse proxy per ADR-0012 (reserved — not authored) |

**Production rule:** The Backend API exposes **HTTPS endpoints only**. Plain HTTP is not accepted in production deployments.

**Certificate approach:** Use a **trusted internal Certificate Authority (CA)** for the office environment:

1. Establish an internal CA (e.g., `step-ca`, OpenSSL-based private CA, or Windows AD Certificate Services if available).
2. Issue a server certificate for the dedicated server hostname/IP (e.g., `webstudio-server.local` or static IP SAN).
3. Distribute the **CA root certificate** to all clients:
   - **Windows Desktop** — import to Trusted Root Certification Authorities (group policy or installer).
   - **macOS Desktop** — add to System Keychain via installer or MDM profile.
   - **Android** — install CA via network security config (`res/xml/network_security_config.xml`) or device admin profile.
4. Configure Uvicorn (or equivalent) with server cert + key on the API Windows Service.

**Future migration:** If the software is later accessed outside the office, replace or supplement the internal CA with a public certificate (Let's Encrypt, commercial CA) or terminate TLS at a reverse proxy. Client installers must support updating the trusted CA/cert bundle without reinstall.

> **Governance note:** This architecture refines TS-001 v1.1 transport guidance for production. [ADR-0010](../adr/ADR-0010-authentication-and-initialization.md) records HTTPS-from-day-one with internal CA as the binding production decision.

---

## 2. Architectural Goals

Every structural decision in WEBSTUDIO IMS is evaluated against the following objectives, derived from the Project Bible and PRD.

### 2.1 Maintainability (10+ Year Horizon)

| Objective | Architectural Response |
|-----------|------------------------|
| Small team, long lifespan | Python + TypeScript monorepo; explicit layering; ADRs for decisions |
| Business rules in one place | All enforcement in Backend API service layer |
| Readable by future contributors | Domain vocabulary in `packages/shared-kernel/`; OpenAPI as contract |
| AI-assisted development | Conventional patterns; documented boundaries; no clever indirection |

### 2.2 Security

| Objective | Architectural Response |
|-----------|------------------------|
| No unauthorized inventory mutation | RBAC on every API endpoint; audit on every mutation |
| No database bypass | Integrations and clients are API consumers only |
| Credential protection | bcrypt hashing; JWT with refresh rotation; secrets in environment |
| Client hardening | Electron sandbox; Android Keystore for tokens |
| Defense in depth on LAN | HTTPS + firewall subnet rules; service accounts; no internet exposure V1 |

### 2.3 Simplicity

| Objective | Architectural Response |
|-----------|------------------------|
| One developer team | No microservices beyond three Windows Services on one server |
| No premature infrastructure | No Redis, Celery, or message bus in V1 |
| Clear dependency direction | `apps/` → `packages/`; no circular dependencies |
| Configuration over hardcoding | Locations, brands, sync schedules in database + admin UI |

### 2.4 Scalability (Appropriate to Retail Scale)

| Objective | Architectural Response |
|-----------|------------------------|
| Three locations, one building | Single PostgreSQL instance; vertical scaling sufficient V1 |
| Future multi-branch | Location model extensible; API versioning; no client coupling to server IP hardcoding |
| Future cloud | Stateless API; externalized config; OpenAPI contract portable |
| Search at scale | PostgreSQL indexing strategy; pagination on all list endpoints |

### 2.5 Modularity

| Objective | Architectural Response |
|-----------|------------------------|
| Future modules (warranty, service center) | Domain packages; additive API namespaces |
| Integration volatility isolated | `packages/integrations/tally/`, `packages/integrations/excel/` |
| Shared UI patterns | `packages/ui-components/` for desktop; NativeWind-equivalent on mobile |
| Shared contracts | `packages/api-client/` generated or hand-maintained from OpenAPI |

### 2.6 Testability

| Objective | Architectural Response |
|-----------|------------------------|
| Business rules unit-testable | Service layer independent of FastAPI and SQLAlchemy |
| Integrations mockable | Adapter interfaces; fixture recordings from Tally POC |
| End-to-end confidence | Playwright for desktop critical paths; pytest for API |
| CI without live Tally | Integration tests use recorded XML fixtures |

### 2.7 Performance

| Objective | Architectural Response |
|-----------|------------------------|
| Search feels instant | Indexed serial lookup; Product Model specification search; server-side filtering |
| Correctness over speed for mutations | Synchronous transactions; audit in same transaction |
| Non-blocking UI | Async client requests; loading states mandatory |
| Acceptable sync windows | Scheduled off-peak Excel export; Tally poll interval configurable |

---

## 3. System Context

### 3.1 Participating Systems

| System | Role | Trust Level | Data Authority |
|--------|------|-------------|----------------|
| **Electron Desktop App** | Primary staff UI — Windows & macOS | Trusted client (authenticated) | Display only; no local inventory authority |
| **React Native Android App** | Mobile search, movement, verification | Trusted client (authenticated) | Display only; minimal optional cache |
| **Backend API** | Business logic, auth, persistence gateway | **Trusted compute zone** | Enforces all inventory rules; sole DB writer |
| **PostgreSQL** | Authoritative datastore | **Highest trust — data zone** | Single source of truth for inventory |
| **Excel Synchronization Service** | One-way export to Excel workbook | Semi-trusted internal service | Reads via API; writes Excel file only |
| **Tally Integration Service** | Detect billing events; reflect sales | Semi-trusted — external input boundary | Reads Tally; mutates inventory via API only |
| **Excel Workbook** | Business-visible inventory export | Untrusted — derived copy | Never authoritative (BR-07, N3) |
| **Tally ERP 9** | Billing and accounting | External system of record for billing | Authoritative for invoices only (N4) |
| **Barcode Scanner** | Keyboard-wedge serial input | Untrusted input device | Input treated as untyped string; validated server-side |
| **Dedicated Server PC** | Hosts API, DB, sync services | Physical trust boundary | Windows 11 Pro; not a workstation |

### 3.2 Actors

| Actor | Interacts With | Primary Goals |
|-------|----------------|---------------|
| **Salesperson** | Desktop, Android | Search, verify availability, movement |
| **Admin** | Desktop, Android | Add inventory, movement, reports, manual mark-as-sold, Tally Sync Now |
| **Main Admin** | Desktop | Full configuration, users, integrations, backup, audit |
| **System (Tally Sync)** | Tally → API | Reflect sales automatically |
| **System (Excel Sync)** | API → Excel | Keep spreadsheet current |

### 3.3 Trust Boundaries

```mermaid
flowchart TB
    subgraph UNTRUSTED["Untrusted Zone"]
        SCANNER[Barcode Scanner]
        EXCEL_FILE[Excel Workbook]
    end

    subgraph CLIENT["Client Zone — Authenticated"]
        DESKTOP[Electron Desktop]
        ANDROID[React Native Android]
    end

    subgraph LAN["Trusted Office LAN"]
        subgraph SERVER["Dedicated Server PC — Trusted Compute"]
            API[Backend API]
            EXCEL_SVC[Excel Sync Service]
            TALLY_SVC[Tally Sync Service]
            PG[(PostgreSQL)]
        end
        TALLY[Tally ERP 9]
    end

    SCANNER -->|keyboard wedge| DESKTOP
    DESKTOP -->|HTTPS + JWT| API
    ANDROID -->|HTTPS + JWT| API
    API -->|SQL localhost| PG
    EXCEL_SVC -->|HTTPS service account JWT| API
    EXCEL_SVC -->|write file| EXCEL_FILE
    TALLY_SVC -->|XML HTTP| TALLY
    TALLY_SVC -->|HTTPS service account JWT| API

    style PG fill:#2d5016,color:#fff
    style API fill:#1a3a5c,color:#fff
```

**Boundary rules:**

1. **Clients and sync workers never cross into the data zone.** No PostgreSQL drivers in Electron, Android, Excel Sync, Tally Sync, or integration packages. **Every** inventory read or write from Electron, Android, Excel Sync, and Tally Sync **must pass through the Backend API** (N2, N5).
2. **External systems are always validated.** Tally XML is untrusted input until parsed and validated. Excel is never read for inventory state.
3. **The LAN is not a substitute for authorization** — every API request requires valid JWT and RBAC regardless of HTTPS.
4. **The server PC is a dedicated appliance** — no interactive browsing, minimal attack surface.

### 3.4 Context Diagram

```mermaid
C4Context
    title WEBSTUDIO IMS — System Context

    Person(salesperson, "Salesperson", "Searches inventory, verifies stock")
    Person(admin, "Admin / Main Admin", "Manages inventory, users, settings")

    System(ims, "WEBSTUDIO IMS", "On-premise inventory management platform")

    System_Ext(tally, "Tally ERP 9", "Billing and accounting")
    System_Ext(excel, "Excel Workbook", "Synchronized inventory export")

    Rel(salesperson, ims, "Uses", "Desktop / Android")
    Rel(admin, ims, "Administers", "Desktop")
    Rel(ims, tally, "Reads billing events", "XML over HTTP")
    Rel(ims, excel, "Exports inventory", "openpyxl file write")
```

---

## 4. High-Level Architecture

### 4.1 Overall System

```mermaid
flowchart LR
    subgraph Clients
        D[Electron Desktop\nWin + macOS]
        M[React Native\nAndroid]
    end

    subgraph Server["Windows 11 Pro Server PC"]
        API[WEBSTUDIO API\nFastAPI + Uvicorn]
        ES[WEBSTUDIO Excel Sync]
        TS[WEBSTUDIO Tally Sync]
        DB[(PostgreSQL 16)]
    end

    subgraph External
        T[Tally ERP 9]
        X[Excel File]
    end

    D & M -->|REST /api/v1| API
    API --> DB
    ES -->|REST read + trigger| API
    ES --> X
    TS -->|XML poll| T
    TS -->|REST mutate sales| API
```

### 4.2 Component Interactions (Request Path)

```mermaid
sequenceDiagram
    participant C as Desktop / Android Client
    participant A as Backend API
    participant S as Service Layer
    participant R as Repository Layer
    participant D as PostgreSQL

    C->>A: HTTPS POST /api/v1/inventory/move
    A->>A: JWT validate + RBAC check
    A->>A: Pydantic request validation
    A->>S: move_inventory(command)
    S->>S: Business rules + lifecycle check
    S->>R: persist within transaction
    R->>D: UPDATE current_location_id + INSERT audit
    D-->>R: commit
    R-->>S: result
    S-->>A: domain result
    A-->>C: 200 JSON response
```

### 4.3 Deployment View

```mermaid
flowchart TB
    subgraph WIFI["Office Wi-Fi LAN — 192.168.x.x"]
        subgraph STORE["Retail Floor"]
            PC1[Windows Desktop]
            PC2[macOS Desktop]
            PHONE[Android Phone]
        end

        subgraph SERVER_ROOM["Server Location"]
            SERVER[Windows 11 Pro\nDedicated Server PC\nStatic IP]
        end

        TALLY_PC[Tally ERP 9 PC]
    end

    PC1 & PC2 & PHONE -->|HTTPS :8443 JWT| SERVER
    SERVER -->|localhost :5432| SERVER
    SERVER -.->|XML :9000 TBD| TALLY_PC

    subgraph SERVER_INTERNAL["Server Internal Processes"]
        direction TB
        WS1[Windows Service:\nWEBSTUDIO API]
        WS2[Windows Service:\nWEBSTUDIO Excel Sync]
        WS3[Windows Service:\nWEBSTUDIO Tally Sync]
        WS4[Windows Service:\nPostgreSQL]
    end

    SERVER --- SERVER_INTERNAL
```

### 4.4 Data Flow — Authority Direction

```mermaid
flowchart LR
    subgraph AUTHORITY["Authoritative Flow"]
        USER[Staff Action] --> API[Backend API]
        API --> PG[(PostgreSQL)]
    end

    subgraph DERIVED["Derived Flow — One Way"]
        PG --> API2[Backend API]
        API2 --> EXCEL_SVC[Excel Sync]
        EXCEL_SVC --> XLS[Excel File]
    end

    subgraph EXTERNAL["External Billing Flow"]
        TALLY[Tally ERP 9] --> TALLY_SVC[Tally Sync]
        TALLY_SVC --> API3[Backend API]
        API3 --> PG2[(PostgreSQL)]
    end

    style PG fill:#2d5016,color:#fff
    style PG2 fill:#2d5016,color:#fff
    style XLS fill:#888,color:#fff
    style TALLY fill:#888,color:#fff
```

**Critical invariant:** Arrows into PostgreSQL pass **only** through the Backend API. Excel Sync, Tally Sync, Electron, and Android **never** read from or write to PostgreSQL — directly or indirectly.

> **Excel Sync data path:** Excel Sync reads inventory **only via Backend API** export endpoints — never via direct SQL.

### 4.5 Monorepo Structure (Logical)

| Path | Architectural Role |
|------|-------------------|
| `apps/backend/` | FastAPI application — WEBSTUDIO API Windows Service |
| `apps/server/` | Excel Sync and Tally Sync worker entry points — separate Windows Services |
| `apps/desktop/` | Electron shell + React renderer |
| `apps/mobile/` | React Native Android application |
| `packages/shared-kernel/` | Domain types, enums, lifecycle states, error codes |
| `packages/auth/` | Permission constants, role-to-permission maps (shared contract) |
| `packages/api-client/` | Typed HTTP client generated from OpenAPI |
| `packages/integrations/excel/` | Excel export logic (openpyxl) |
| `packages/integrations/tally/` | Tally XML client and parser |
| `packages/ui-components/` | Shared React components (desktop; adapted patterns for mobile) |
| `packages/testing/` | Fixtures, factories, test helpers |
| `database/migrations/` | Alembic migrations — schema evolution |
| `infra/` | Deployment scripts, Windows Service install templates |
| `config/env/` | Environment templates (no secrets in Git) |

**Dependency rule:** `apps/` may depend on `packages/`. `packages/` must not depend on `apps/`. Integration packages must not depend on desktop or mobile apps.

---

## 5. Architectural Principles

These principles govern all design and implementation decisions. They map directly to Project Bible non-negotiable rules (N1–N18).

| Principle | Meaning | Enforcement |
|-----------|---------|-------------|
| **Backend-first** | All inventory outcomes are decided by the Backend API | N6, BR-12; service layer is authoritative |
| **Database authority** | PostgreSQL is the single source of truth for inventory | N1, BR-06; no dual writes |
| **Thin clients** | Desktop and Android render state and capture input | No business rule enforcement in UI |
| **Single responsibility** | Each component has one reason to change | API / sync / UI separated |
| **Configuration over hardcoding** | Locations, brands, schedules are admin-configurable | N13, BR-14; settings in DB |
| **Fail safely** | Partial failures must not corrupt inventory | Transactions; idempotent sync; no silent errors |
| **Never trust the client** | All inputs re-validated server-side | Pydantic + service layer rules |
| **API-first** | OpenAPI contract precedes or accompanies implementation | `/api/v1/` versioning |
| **Security by default** | Deny unless permitted; least privilege RBAC | NFR-SEC-03, NFR-SEC-05 |
| **Integration at the edges** | External I/O in dedicated packages and services | I1, I8; Project Bible §22.2 |
| **Audit everything material** | Inventory mutations and admin actions are logged | N8, BR-09; immutable audit |
| **Search-first** | Search is never degraded by feature additions | N12, BR-13; dedicated search service |
| **Event-aware, not event-dependent** | No message bus required V1; design allows future events | Polling/sync workers initially |
| **Idempotent integrations** | External events and sync jobs safe to retry without duplicate effects | Sale reflection, Tally vouchers, sync jobs |
| **API-only data access** | Electron, Android, Excel Sync, Tally Sync → API only; API → PostgreSQL only | N2, N5 |
| **Document decisions** | Significant choices require ADRs | N15, N17 |

---

## 6. Component Design

### 6.1 Backend API (`apps/backend`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Sole gateway to PostgreSQL; enforces all business rules, authorization, and audit |
| **Responsibilities** | REST API, JWT auth, RBAC, inventory engine, search, user management, settings, health checks, audit logging |
| **Dependencies** | PostgreSQL (localhost), `packages/shared-kernel`, `packages/auth`, SQLAlchemy, Alembic |
| **Interfaces** | OpenAPI 3.1 REST at `/api/v1/`; health at `/health` |
| **Failure modes** | DB connection loss → 503; validation error → 422; auth failure → 401/403; business rule violation → 409 with clear message |
| **Recovery** | Connection pool retry; Windows Service auto-restart; clients show retry UI |

**Why it exists:** Central authority prevents divergent behavior across three client platforms and two integrations (N2, N5).

### 6.2 Excel Synchronization Service (`apps/server` — Excel worker)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Export current inventory state from API to Excel workbook on schedule or manual trigger |
| **Responsibilities** | Scheduled export, manual trigger via API endpoint or internal scheduler, atomic file write, sync logging |
| **Dependencies** | Backend API (read endpoints + sync status write), `packages/integrations/excel`, openpyxl, filesystem path |
| **Interfaces** | Inbound: APScheduler timer, sync job queue via API; Outbound: HTTPS REST to API, `.xlsx` file write |
| **Failure modes** | API unreachable → retry with backoff, log failure, alert Main Admin; Excel file locked → skip or queue, log warning |
| **Recovery** | Next scheduled run; manual re-trigger via new sync job; last-known-good file preserved |

**Orchestration rule:** Manual sync requests create a **Sync Job** record via the API. The Excel Sync worker executes the job. **The API never writes Excel files directly.**

**Why separate service:** Isolates file I/O failures from API availability; allows independent restart and scheduling (N18, I1).

### 6.3 Tally Integration Service (`apps/server` — Tally worker)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Read invoices from Tally ERP 9 and reflect laptop sales in inventory via API — **never write to Tally** |
| **Responsibilities** | Poll Tally per company on configurable interval (default 30 minutes); parse invoice lines; **serial-authoritative** match in **`available`** inventory; post-sale product model verification with normalization; call API to mark sold or create notifications; update per-company sync cursor; log all events |
| **Dependencies** | Backend API, `packages/integrations/tally`, Tally ERP 9 HTTP/XML interface |
| **Interfaces** | Inbound: Tally XML over HTTP (**mechanism Requires POC**); Outbound: REST to API |
| **Failure modes** | Tally offline → log, continue next interval; per-company failure isolated; serial/model mismatch → notification, no mutation |
| **Recovery** | Sync Now from dashboard; manual mark-as-sold (Admin/Main Admin); review Notification Center |

**Why separate service:** Tally is the most volatile integration; isolation limits blast radius (I1, highest risk per TECH_STACK).

### 6.4 PostgreSQL Database

| Aspect | Detail |
|--------|--------|
| **Purpose** | Authoritative persistent store for all inventory, users, audit, configuration |
| **Responsibilities** | ACID transactions, uniqueness constraints, indexing, backup target |
| **Dependencies** | None (foundation) |
| **Interfaces** | SQL via SQLAlchemy from Backend API only |
| **Failure modes** | Disk full, corruption, service crash |
| **Recovery** | `pg_dump` restore; WAL archiving recommended; UPS for power loss |

### 6.5 Electron Desktop Application (`apps/desktop`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Primary staff interface for inventory operations on Windows and macOS |
| **Responsibilities** | UX, search, forms, dashboard, reports display, barcode field capture, theme, token storage |
| **Dependencies** | Backend API, `packages/api-client`, `packages/ui-components`, OS keychain |
| **Interfaces** | REST + JWT; IPC between main and renderer processes |
| **Failure modes** | Network loss → error state + retry; token expiry → refresh or re-login |
| **Recovery** | Automatic token refresh; user-initiated retry; no local inventory queue V1 |

### 6.6 React Native Android Application (`apps/mobile`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Mobile access for search, verification, and limited inventory actions |
| **Responsibilities** | Same API contract as desktop for permitted role actions; mobile-optimized UX |
| **Dependencies** | Backend API, `packages/api-client`, Android Keystore |
| **Interfaces** | REST + JWT |
| **Failure modes** | Network loss, token expiry, background kill |
| **Recovery** | Re-auth flow; online-first V1 — no offline mutation queue |

### 6.7 Excel Workbook (External)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Business continuity — familiar spreadsheet view of inventory |
| **Responsibilities** | None within WEBSTUDIO IMS — passive file |
| **Trust** | **Untrusted / non-authoritative** — changes in Excel are ignored |
| **Failure modes** | User opens file during sync → lock conflict |
| **Recovery** | Sync retries; warn in admin UI |

### 6.8 Tally ERP 9 (External)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Billing, invoicing, accounting — unchanged by WEBSTUDIO IMS |
| **Responsibilities** | Generate sales vouchers with serial references |
| **Trust** | Authoritative for billing only; voucher data validated before inventory mutation |
| **Failure modes** | Tally not running, XML API disabled, network partition |
| **Recovery** | Manual sale reflection; reconciliation UI for Main Admin |

### 6.9 Barcode Scanner (External Input Device)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Rapid serial number entry via keyboard-wedge emulation |
| **Responsibilities** | None — treated as fast keyboard input |
| **Trust** | Untrusted string input — server validates format and uniqueness |
| **Failure modes** | Mis-scan, damaged barcode, wrong symbology |
| **Recovery** | Manual entry always available (BC-07) |

### 6.10 Backup Runner (Scheduled Task)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Automated PostgreSQL backup and verification coordination |
| **Host** | Windows Scheduled Task on dedicated server (not the API process) |
| **Responsibilities** | `pg_dump` on schedule; copy to `D:\WEBSTUDIO-IMS\backups\`; optional off-server copy; trigger monthly restore verification script |
| **Dependencies** | PostgreSQL localhost; filesystem; optional NAS path |
| **Failure modes** | Dump failure, disk full, restore verification failure |
| **Recovery** | Alert Main Admin; retain last known good backup; documented in [Section 20.6](#206-backups) |

**Backup validity rule:** A backup is **not considered valid** until it has been successfully restored and verified (see [Section 20.6](#206-backups)).

---

## 7. Backend Architecture

### 7.1 Architecture Style — Layered with Hexagonal Integration Boundaries

**Recommendation: Layered Architecture (4 layers) with Ports & Adapters at integration edges.**

| Style | Fit Assessment |
|-------|----------------|
| **Layered** | **Selected** — clear separation for small team; maps naturally to FastAPI structure |
| **Clean Architecture** | **Adopted selectively** — domain rules in service layer; dependencies point inward |
| **Hexagonal** | **Adopted at integration boundary** — Tally and Excel are adapters, not embedded in core |
| **Microservices** | **Rejected V1** — unnecessary operational overhead for single-server deployment |
| **CQRS / Event Sourcing** | **Rejected V1** — over-engineering for retail scale; revisit if analytics module demands it |

**Why this fits WEBSTUDIO IMS:** A one-building, three-location retail deployment with a small engineering team needs **predictable structure** over theoretical purity. FastAPI routers map to the API layer. Business rules concentrate in testable services. SQLAlchemy repositories isolate persistence. Integration volatility stays in `packages/integrations/` and `apps/server/` workers — not in inventory core logic.

### 7.2 Layer Diagram

```mermaid
flowchart TB
    subgraph API["API Layer — apps/backend/api/"]
        ROUTERS[FastAPI Routers]
        DEPS[Dependencies — auth, db session]
        SCHEMAS[Pydantic Request/Response Schemas]
    end

    subgraph APP["Application / Service Layer — apps/backend/services/"]
        INV_SVC[InventoryService]
        SALE_SVC[SaleService]
        SRCH_SVC[SearchService]
        AUTH_SVC[AuthenticationService]
        USER_SVC[UserService]
        AUDIT_SVC[AuditRecorder]
        SETTINGS_SVC[SettingsService]
        SYNC_SVC[SyncJobService]
    end

    subgraph DOMAIN["Domain Layer — packages/shared-kernel/"]
        ENTITIES[Entities & Value Objects]
        ENUMS[Lifecycle States, Roles, Permissions]
        RULES[Domain Rules & Exceptions]
    end

    subgraph INFRA["Infrastructure Layer — apps/backend/infrastructure/"]
        REPOS[SQLAlchemy Repositories]
        DB[Database Session Factory]
        SECURITY[JWT, bcrypt utilities]
    end

    subgraph ADAPTERS["Integration Adapters — packages/integrations/"]
        EXCEL_ADP[Excel Adapter]
        TALLY_ADP[Tally Adapter]
    end

    ROUTERS --> DEPS --> SCHEMAS
    ROUTERS --> APP
    APP --> DOMAIN
    APP --> REPOS
    REPOS --> DB
    ADAPTERS -.->|HTTPS only| ROUTERS
```

### 7.3 API Layer

| Concern | Design |
|---------|--------|
| **Routers** | One router per domain: `auth`, `inventory`, `search`, `brands`, `product_models`, `locations`, `users`, `settings`, `audit`, `reports`, `health`, `sync` |
| **Versioning** | URL prefix `/api/v1/` — breaking changes require v2 |
| **Validation** | Pydantic v2 models on every request body and query parameter |
| **Dependencies** | FastAPI `Depends()` for: DB session, current user, permission checks |
| **Response format** | Consistent envelope: data + error structure; HTTP status codes per REST conventions |
| **Documentation** | Auto-generated OpenAPI; exported to `docs/api/openapi/` |

**Rule:** Routers contain **no business logic** — only HTTP concerns, delegation to services, and exception mapping.

### 7.4 Application / Service Layer

Core domain services and their boundaries:

| Service | Responsibility | Does NOT |
|---------|----------------|----------|
| **InventoryService** | Create inventory; update attributes (including **Color**); lifecycle transitions (Received ↔ Available); **location transfers** (updates `current_location_id` + audit); enforce LC rules; validate Product Model is **Active** for new units | Process sales; execute search queries |
| **ProductModelService** | Create product models; Archive/Restore lifecycle; enforce permanent-delete preconditions | Inventory mutations; sales |
| **SaleService** | Reflect Tally invoice lines (AVAILABLE match); manual mark-as-sold (Admin/Main Admin); invoice-level idempotency; duplicate sold detection; sales history | Create inventory; change location |
| **SearchService** | Query parsing; search execution; pagination; result grouping | Mutate inventory |
| **AuthenticationService** | Login; token issue/refresh/revoke; lockout; session invalidation; password verify | User profile CRUD (delegates to UserService) |

Supporting services:

| Service | Responsibility |
|---------|----------------|
| **UserService** | CRUD users; role assignment; password reset by Main Admin |
| **AuditRecorder** | Append-only audit record creation with human-readable snapshots — **single source of truth** for inventory history, location changes, and lifecycle traceability |
| **SettingsService** | System configuration read/write |
| **ReportService** | Aggregate queries for dashboard and reports |
| **SyncJobService** | Create and track sync jobs; authorize manual triggers; job status for workers |
| **ProductModelService** | Product model CRUD; Active/Archived lifecycle; permanent-delete guard |

**Business rules live here exclusively** (N6, BR-12). Services are plain Python classes — testable without HTTP context. Services accept and return **domain types** — never ORM models.

**Integration rule:** Tally Sync and Excel Sync call API endpoints that delegate to these services. Integrations **never bypass** the service layer or access repositories directly.

### 7.5 Repository Layer

| Concern | Design |
|---------|--------|
| **Pattern** | Repository per aggregate: `InventoryRepository`, `AuditRepository`, `UserRepository` |
| **ORM** | SQLAlchemy 2.x with typed models |
| **Queries** | Parameterized only — no string concatenation (SQL injection prevention) |
| **Transactions** | Unit of Work pattern: service opens transaction, repository participates, commit on success |
| **Pagination** | Cursor or offset pagination on all list endpoints — mandatory for search results |

### 7.6 Background Jobs

Version 1 does **not** embed heavy job processing in the API process.

| Job | Host | Mechanism |
|-----|------|-----------|
| Excel scheduled export | Excel Sync Windows Service | APScheduler; polls `SyncJobService` for pending jobs |
| Tally polling | Tally Sync Windows Service | APScheduler or async loop |
| Manual sync trigger | `POST /api/v1/sync/excel/trigger` → creates Sync Job; Excel worker executes | API enqueues only — **never writes Excel** |
| Database backup | Windows Scheduled Task | `pg_dump` — see §6.10 |

**Future:** Celery + Redis if job volume or complexity grows — requires ADR.

### 7.7 Configuration

| Source | Contents |
|--------|----------|
| Environment variables | DB connection, JWT secret, log level, API bind host/port |
| Database settings table | Business-configurable: sync schedule, session timeout, lockout threshold |
| `config/env/.env.example` | Template committed to Git — no secrets |

Configuration is loaded at startup via Pydantic `Settings` class. Changes to DB-backed settings take effect on next read or via explicit cache invalidation.

### 7.8 Validation Strategy

| Layer | Validation |
|-------|------------|
| **Client (Zod)** | Format hints, required fields — UX only |
| **API (Pydantic)** | Type, length, pattern, enum constraints |
| **Service** | Business rules: lifecycle transitions, sold movement block, brand deactivation block |
| **Database** | Unique constraints on serial number, foreign keys, not-null |

### 7.9 Dependency Injection

FastAPI native DI:

- `get_db()` → yields SQLAlchemy session per request
- `get_current_user()` → validates JWT, loads user
- `require_permission(Permission.INVENTORY_CREATE)` → RBAC guard
- Services injected into routers via factory functions

### 7.10 Error Handling

| Error Type | HTTP Status | Client Message |
|------------|-------------|----------------|
| Validation failure | 422 | Field-level detail |
| Unauthorized | 401 | Generic "Invalid credentials" |
| Forbidden | 403 | "You do not have permission" |
| Business rule violation | 409 | Plain-language rule explanation |
| Not found | 404 | Entity type + identifier |
| Conflict (duplicate serial) | 409 | "Serial number already exists" |
| Server error | 500 | Generic message; detail in logs only |

**Correlation ID:** Every request receives `X-Request-ID` — propagated through logs and audit entries.

### 7.11 Domain Model Mapping

Business logic **must never depend directly on ORM entities**.

| Layer | Location | Contents |
|-------|----------|----------|
| **ORM models** | `apps/backend/infrastructure/models/` | SQLAlchemy table mappings; no business methods |
| **Domain models** | `packages/shared-kernel/domain/` | Entities, value objects, enums (`LifecycleState`, `SerialNumber`) |
| **Repositories** | `apps/backend/infrastructure/repositories/` | Map ORM ↔ domain; parameterized queries only |

**Mapping rules:**

1. Routers receive/return Pydantic **DTOs** (API schemas).
2. Services accept/return **domain types**.
3. Repositories translate domain types to ORM models at the persistence boundary.
4. No SQLAlchemy `Session` or ORM models imported in `services/` or `packages/shared-kernel/`.
5. Integration workers never import repository or ORM modules — API calls only.

### 7.12 Idempotent Operations

The following operations **must be idempotent** — repeated execution never duplicates business effects:

| Operation | Idempotency Key | Behaviour on Repeat |
|-----------|-----------------|---------------------|
| **Tally invoice (fully processed)** | `tally_voucher_guid` + company where `processing_status = success` | Skip — sync log `skipped` |
| **Tally invoice (partial)** | Failed lines in `tally_processed_invoice_lines` | Retry failed lines only |
| **Tally line (duplicate sold)** | Serial in **sold** inventory | Duplicate Sale notification; line marked completed |
| **Manual sale reflection** | `invoice_number` + `serial_number` (or `Idempotency-Key`) | No-op if already Sold; Tally sync treats as same transaction |
| **Excel sync job** | `sync_job_id` | Overwrite export file; update job status |
| **Sync job creation** | Optional client `Idempotency-Key` | Return existing job if duplicate trigger |

API clients (including sync workers) may send `Idempotency-Key` header on mutation requests. `SaleService` enforces idempotency before any state change.

---

## 8. Desktop Architecture

### 8.1 Process Model

```mermaid
flowchart LR
    subgraph ELECTRON["Electron Application"]
        MAIN[Main Process\nNode.js]
        PRELOAD[Preload Script\ncontextBridge]
        RENDERER[Renderer Process\nReact + Vite]
    end

    API[Backend API]

    RENDERER <-->|IPC whitelist| PRELOAD
    PRELOAD <-->|IPC| MAIN
    MAIN -->|HTTPS Axios + JWT| API
    RENDERER -.->|no direct network\nin hardened config| API
```

### 8.2 Main Process

| Responsibility | Detail |
|----------------|--------|
| Window management | Create, minimize, multi-window **TBD** |
| Secure token storage | `safeStorage` / `keytar` for refresh token |
| IPC broker | Whitelisted channels only |
| Auto-update | **Future** — code signing required |
| Deep linking | **Future** |
| API base URL | Loaded from config; configurable at install |

### 8.3 Renderer Process

| Responsibility | Detail |
|----------------|--------|
| UI rendering | React 18 + TypeScript + Vite |
| Styling | Tailwind CSS + shadcn/ui |
| State | Zustand stores per domain |
| Forms | React Hook Form + Zod (client-side UX validation) |
| API calls | **Mandatory:** via IPC to main process — renderer has **no network access** |

**Security configuration (mandatory):**

- `contextIsolation: true`
- `nodeIntegration: false`
- `sandbox: true`
- `webSecurity: true`
- Content Security Policy restricting script sources
- `shell.openExternal` allowlist only; block arbitrary `window.open` navigation

### 8.4 IPC Communication

| Channel | Direction | Payload |
|---------|-----------|---------|
| `auth:login` | Renderer → Main | credentials |
| `auth:logout` | Renderer → Main | — |
| `auth:getAccessToken` | Renderer → Main | — |
| `api:request` | Renderer → Main | method, path, body |
| `config:getServerUrl` | Renderer → Main | — |

All IPC payloads validated with Zod in preload script.

### 8.5 API Communication

- Base URL: `https://{server-host}:8443/api/v1/` (production — internal CA trusted)
- Development override: `http://localhost:8000/api/v1/` on developer machines only
- Authorization: `Bearer {access_token}` attached by main process via IPC proxy
- TLS: validate server certificate against installed internal CA root
- Token refresh: Main process intercepts 401, refreshes via `/auth/refresh`, retries once
- Timeout: Configurable; default 30 seconds
- Error mapping: API error codes → user-friendly toast messages

### 8.6 Local Storage

| Data | Storage | Notes |
|------|---------|-------|
| Refresh token | OS keychain | Never localStorage |
| Access token | Main process memory | Short-lived |
| User preferences (theme) | Encrypted local file or API-backed | Sync across devices **Future** |
| Inventory cache | **None V1** | Online-first |
| Offline queue | **None V1** | Mutations require API |

### 8.7 Client Connection & Authentication Flow (Desktop)

```mermaid
sequenceDiagram
    participant U as User
    participant R as Renderer
    participant M as Main Process
    participant A as Backend API

    Note over R,M: First launch — server discovery or manual HTTPS URL
    M->>A: GET /api/v1/setup/status
    alt system_initialized = false
        R->>U: First-Time Setup Wizard
        R->>M: IPC setup:initialize
        M->>A: POST /api/v1/setup/initialize
        A-->>M: Main Admin created; system_initialized = true
    else system_initialized = true
        U->>R: Enter credentials
        R->>M: IPC auth:login
        M->>A: POST /auth/login
        A-->>M: access + refresh tokens
        M->>M: Store refresh in keychain
        M-->>R: success + user profile
        R->>M: IPC api:request (with auto token)
        M->>A: Bearer access token
    end
```

**Rules:** Client installations never create users locally. Users authenticate only against the Backend. Clients store server URL and tokens — not business data (V1 online-first).

### 8.8 Update Strategy

| Phase | Approach |
|-------|----------|
| **V1** | Manual installer distribution via LAN share or USB |
| **Future** | Electron auto-update with code-signed releases |

### 8.9 Offline Behaviour

**V1: Online-first.** Without API connectivity:

- Dashboard and inventory views show connection error state
- No local mutation queue — staff must retry when server available
- Search unavailable offline

**Rationale:** Offline inventory queues create conflict resolution complexity inappropriate for V1. Android and desktop share this policy.

---

## 9. Android Architecture

### 9.1 Application Layers

```mermaid
flowchart TB
    subgraph UI["Presentation Layer"]
        SCREENS[Screens & Navigation]
        COMPONENTS[UI Components]
    end

    subgraph STATE["State Layer"]
        ZUSTAND[Zustand Stores]
        HOOKS[Custom Hooks]
    end

    subgraph DATA["Data Layer"]
        API_CLIENT[packages/api-client]
        TOKEN[Token Manager]
    end

    SCREENS --> ZUSTAND --> API_CLIENT
    API_CLIENT --> TOKEN
    API_CLIENT -->|HTTPS + JWT| BACKEND[Backend API]
```

### 9.2 Networking

- Axios via shared `packages/api-client`
- Base URL: `https://{server-host}:8443/api/v1/` — configured at first launch
- Internal CA root installed via network security config — required for production HTTPS
- Certificate pinning: **Recommended** — pin server cert or CA for production LAN
- Request interceptors: attach access token
- Response interceptors: 401 → refresh → retry once

> **Known V1 gap:** Access tokens pass through the React Native JavaScript runtime. Acceptable with short-lived tokens on trusted LAN. See [§22.6](#226-deferred-future-enhancements) for native networking improvement.

### 9.3 Caching

| Data | Cache | TTL |
|------|-------|-----|
| Inventory search results | **None V1** | — |
| User profile | Memory | Session |
| Brands/locations list | Memory | Refresh on app foreground |
| Dashboard aggregates | Memory | Short TTL (30s) **TBD** |

**No persistent offline inventory cache V1** — minimizes stale data risk.

### 9.4 Authentication

- Access token: memory
- Refresh token: Android Keystore via EncryptedSharedPreferences
- Biometric unlock: **Future**
- Session timeout: enforced client-side idle timer + server-side token expiry

### 9.5 Offline Behaviour

Same as desktop: **online-first V1**. Clear error UI when server unreachable. No mutation queue.

### 9.6 Synchronization

Android does not run sync jobs. Excel and Tally synchronization are server-side Windows Services. Android benefits from sync outcomes indirectly via current inventory state.

---

## 10. Database Architecture

> **Scope:** This section describes database **architecture** — not table designs. Schema design is the next downstream artifact.

### 10.1 Ownership

| Rule | Detail |
|------|--------|
| **Single database** | One PostgreSQL 16 instance on dedicated server |
| **Single application schema** | `webstudio` schema — all application tables |
| **Application user** | `webstudio_app` — SELECT/INSERT/UPDATE/DELETE on app schema only |
| **Superuser** | Migrations and admin tasks only — never used by running API |
| **Access path** | Backend API only — localhost connection |

### 10.2 Transactions

| Operation | Transaction Boundary |
|-----------|---------------------|
| Create inventory | Insert inventory + insert audit — single transaction |
| Lifecycle transition | Update status + insert audit + insert sales history (if sold) — single transaction |
| Location transfer | Update `current_location_id` + insert `audit_logs` (`LOCATION_CHANGE`) — single transaction |
| Sale reflection (Tally) | Update status + sales history + audit — single transaction |
| Settings change | Update setting + audit — single transaction |

**Rule:** No partial inventory mutations. If audit insert fails, entire operation rolls back.

### 10.3 Concurrency

| Scenario | Strategy |
|----------|----------|
| Two staff edit same laptop | Optimistic locking via `version` column or `updated_at` check — second writer receives 409 |
| Simultaneous sale reflection | Idempotent sale by voucher ID + serial — second attempt is no-op |
| Serial number race on create | Database UNIQUE constraint on serial — second insert fails with 409 |
| Excel sync during mutations | Sync reads committed state via API — point-in-time snapshot |

Expected concurrency is low (small staff, one building). Row-level locking on hot paths is sufficient V1.

### 10.4 Integrity

| Constraint | Enforcement |
|------------|-------------|
| Global serial uniqueness | UNIQUE index on serial number |
| One location per laptop | NOT NULL `current_location_id` FK to locations; **history in `audit_log` only** |
| One lifecycle state | NOT NULL enum/check constraint |
| Valid lifecycle transitions | Service layer + optional DB check constraint |
| Immutable audit | INSERT only — no UPDATE/DELETE grants for audit table |
| Referential integrity | Foreign keys with appropriate ON DELETE restrictions |

### 10.5 Indexing Strategy (Conceptual)

| Access Pattern | Index Approach |
|----------------|----------------|
| Serial number exact lookup | B-tree unique index — primary search path |
| Serial number prefix search | B-tree `varchar_pattern_ops` or `LIKE 'prefix%'` |
| Model + brand grouping | Composite index on (brand_id, model_number) |
| Location + status filters | Composite index on (`current_location_id`, `status`) |
| Product Model specification search | B-tree / ILIKE on `product_model` `cpu`, `gpu`, `ram_gb`, storage fields — FR-SRH-05/06 |
| Color exact / partial search | B-tree on `color`; optional `pg_trgm` GIN — FR-SRH-13 |
| Active product models only | Index on `product_model.status` for creation flows |
| Dashboard aggregates | Indexes supporting `COUNT(*) WHERE status = 'available' GROUP BY brand/location` |
| Audit log queries | Index on (created_at DESC), (entity_type, entity_id) |
| Inventory history | Index on `audit_log` (`entity_identifier`, `created_at DESC`) and (`entity_type`, `entity_id`, `created_at DESC`) |

Full index design follows query analysis during schema specification.

### 10.6 Migration Strategy

| Aspect | Approach |
|--------|----------|
| Tool | Alembic |
| Location | `database/migrations/` |
| Naming | Timestamp + descriptive slug |
| Review | Every migration reviewed for backward compatibility |
| Rollback | Downgrade scripts for non-destructive changes |
| Production | `alembic upgrade head` during deployment window |
| Data migrations | Separate scripts with backup requirement |
| Version 1 sequence | `0005` audit logs (**Sprint 1E**) → `0006` users & authentication → `0007` ownership columns → `0008` integrations — see [DATABASE_DESIGN.md §16.5](database/DATABASE_DESIGN.md#165-implementation-order-recommended) |

### 10.7 Backup Philosophy

| Aspect | Approach |
|--------|----------|
| **Schedule** | Daily `pg_dump` — time **TBD** with business (off-peak) |
| **Location** | `D:\WEBSTUDIO-IMS\backups\` + off-server copy recommended |
| **Retention** | Policy **TBD** — minimum 30 days recommended |
| **Verification** | Monthly automated restore test to isolated database; **backup invalid until restore succeeds** |
| **WAL archiving** | Recommended for point-in-time recovery |
| **Pre-upgrade** | Mandatory backup before Alembic migration |

### 10.8 PostgreSQL Extensions & Migration Prerequisites

**Required extensions** (enabled in initial Alembic migration `0001_enable_extensions`):

| Extension | Purpose |
|-----------|---------|
| `pg_trgm` | Optional color partial search (FR-SRH-13); product spec search uses structured `product_model` fields |
| `pgcrypto` | Cryptographic functions if used for token hashing |

**Migration prerequisites:**

- PostgreSQL 16.x installed and running before `alembic upgrade head`
- `webstudio` schema created; `webstudio_app` role with least privilege
- Extensions require superuser or `CREATE` privilege on first migration only
- Every migration reviewed for backward compatibility; downgrade script where feasible

### 10.9 Audit Retention

| Aspect | Policy |
|--------|--------|
| **Storage** | PostgreSQL `audit_log` table — append-only |
| **Retention** | Duration **TBD** with business; minimum 2 years recommended for retail audit |
| **Archival** | Cold storage export **Future** — see §22.6 |
| **Growth** | Monitor table size; index on `created_at` for efficient queries |

---

## 11. Authentication & Authorization

### 11.1 Login Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Auth API
    participant S as AuthenticationService
    participant D as PostgreSQL

    C->>A: POST /auth/login {username, password}
    A->>S: authenticate(credentials)
    S->>D: fetch user by username
    S->>S: verify bcrypt hash
    alt valid credentials
        S->>S: check lockout status
        S->>D: reset failed attempts
        S->>S: issue access + refresh JWT
        S->>D: store refresh token hash
        S-->>A: tokens + user profile
        A-->>C: 200 OK
    else invalid credentials
        S->>D: increment failed attempts
        S-->>A: 401 generic error
        A-->>C: 401 Invalid credentials
    end
```

### 11.2 JWT Strategy

| Token | Lifetime | Storage | Contents |
|-------|----------|---------|----------|
| **Access token** | 15 minutes (default, configurable) | Client memory | `sub`, `role`, `permissions`, `exp`, `iss`, `aud` |
| **Refresh token** | 7 days (rotatable) | Keychain / Keystore | Opaque or JWT — stored hashed server-side |

- Algorithm: HS256 or RS256 — **TBD**; RS256 preferred if multi-service validation needed ([ADR-0010](../adr/ADR-0010-authentication-and-initialization.md) specifies JWT; algorithm pin at implementation)
- Validation on every request: signature, expiry, issuer, audience
- Refresh rotation: new refresh token issued on each refresh; reuse detection revokes family

**Permission staleness:** Role and permission changes take effect when a **new access token is issued** (login or refresh). The JWT carries permissions at issue time. Main Admin may **invalidate active sessions** by incrementing a user's `token_version` (or revoking refresh tokens), forcing re-login on next refresh.

### 11.3 Password Hashing

| Aspect | Decision |
|--------|----------|
| **V1 algorithm** | **bcrypt** — cost factor ≥ 12 (TECH_STACK approved) |
| **Future** | Argon2id — evaluate in V1.1 via ADR |
| **Policy** | Minimum 10 characters; common password blocklist **TBD** |
| **First login** | Force password change |
| **Reset** | Main Admin reset only V1 |

> **Note:** Argon2id is architecturally preferable for new systems but is not the approved V1 algorithm. Implementation must use bcrypt unless [ADR-0010](../adr/ADR-0010-authentication-and-initialization.md) is superseded.

### 11.4 RBAC Model

```mermaid
flowchart LR
  USER[User] --> ROLE[Role]
  ROLE --> PERM[Permissions]
  PERM --> ENDPOINT[API Endpoint Guards]
```

| Role | Scope |
|------|-------|
| **Main Admin** | All permissions |
| **Admin** | Inventory, movement, reports, brands, limited sync — per PRD matrix |
| **Salesperson** | Search, view, move inventory |

Permissions are defined as constants in `packages/auth/permissions.py`. Roles map to permission sets in `packages/auth/role_permissions.py`. Adding a role = new mapping — no schema redesign.

### 11.4.1 Operational Ownership vs Audit

| Layer | Responsibility |
|-------|----------------|
| **Business entities** | Store `created_by_user_id` and `updated_by_user_id` only — set automatically by the backend from the authenticated user |
| **Audit log** | Store complete history: actor ID, display name snapshot, role snapshot, action, entity, before/after values, optional IP/platform/reason |
| **Location transfer** | `audit_logs` entry (`LOCATION_CHANGE`) with from/to location names in `old_value`/`new_value`, actor, timestamp — updates `current_location_id` |

**Excluded from business entities V1:** `sold_by_user_id`, `reserved_by_user_id`, `approved_by_user_id`. Sale attribution uses `sale.recorded_by_user_id` (manual) or audit/Tally events — not a column on `inventory_item`.

### 11.5 Permission Enforcement

| Layer | Enforcement |
|-------|-------------|
| **API router** | `Depends(require_permission(...))` on every endpoint |
| **Service layer** | Secondary check for sensitive operations — defense in depth |
| **Integration services** | Dedicated service accounts with minimum permissions — see table below |

**Service account scopes:**

| Account | Permissions | Used By |
|---------|-------------|---------|
| `svc-excel-sync` | `sync:excel:read`, `sync:job:update` | Excel Sync Windows Service |
| `svc-tally-sync` | `integration:tally:sale` | Tally Sync Windows Service |

**Every endpoint has a permission declaration and a unit test per role.**

### 11.6 Session Expiry

| Mechanism | Detail |
|-----------|--------|
| Access token expiry | 15 minutes — client refreshes automatically |
| Idle timeout | Configurable (default 30 min) — client tracks activity, logout on expiry |
| Refresh token expiry | 7 days — re-login required |
| Server-side revocation | Refresh token table supports revoke on logout and admin force-logout **TBD** |

### 11.7 Account Lockout

| Parameter | Default |
|-----------|---------|
| Failed attempts threshold | 5 (configurable) |
| Lockout duration | 15 minutes (configurable) |
| Unlock | Automatic after duration; Main Admin manual unlock |
| Response | Generic "Invalid credentials" — no user enumeration |

### 11.8 Password Reset Strategy

| Actor | Capability |
|-------|------------|
| User | Change own password (requires current password) |
| Main Admin | Reset any user password → temporary password → force change on login |
| Self-service email reset | **Future** |

### 11.9 Future MFA Considerations

- TOTP or SMS second factor for Main Admin — Version 2+
- Architecture accommodates MFA via additional auth step in `AuthenticationService` without client redesign
- Refresh token flow unchanged; access token includes `mfa_verified` claim when enabled

---

## 12. Inventory Engine

### 12.1 Inventory Lifecycle

Version 1 states: **Received**, **Available**, **Reserved**, **Sold**.

```mermaid
stateDiagram-v2
    [*] --> Received : Add Inventory
    Received --> Available : Admin confirms ready
    Available --> Reserved : Customer hold
    Reserved --> Available : Hold released
    Available --> Sold : Tally sale / manual fallback
    Reserved --> Sold : Tally sale / manual fallback
    Sold --> [*] : Terminal V1

    note right of Received : New stock intake
    note right of Available : Sellable and movable
    note right of Reserved : Held for customer
    note right of Sold : No movement V1
```

### 12.2 State Machine Rules

| Rule ID | Enforcement |
|---------|-------------|
| LC-01 | Exactly one state per laptop — `InventoryService` |
| LC-02 | Every transition creates audit entry — same transaction |
| LC-03 | Location transfer does not change lifecycle state — `InventoryService` |
| LC-04 | Sold laptops cannot transfer location — `InventoryService` rejects |
| LC-05 | Transitions only via API — clients request, service validates |

### 12.3 Location Transfer Rules

| Rule | Service Behaviour |
|------|-------------------|
| Source ≠ destination | Reject identical move |
| Status must be Available or Reserved | **V1 policy:** only **Available** or **Reserved** laptops may move; Received must transition to Available first |
| Record full history | **Audit log only** — source, destination, actor, timestamp, optional reason; human-readable location names |
| Location count | Denormalized counts updated via query — not separate quantity table |

### 12.4 Validation Rules (Representative)

| Operation | Validations |
|-----------|-------------|
| **Create** | Serial unique; brand exists; **product model exists and is Active**; location exists; **color required**; required fields present |
| **Update attributes** | Role check; audit before/after; serial editable with uniqueness enforced; **color editable** |
| **Receive → Available** | Role: Admin+; current state must be Received |
| **Available ↔ Reserved** | Role: Admin+; hold and release |
| **Mark sold** | Current state must be Available or Reserved; idempotent if already Sold — via `SaleService` |
| **Transfer location** | Not Sold; valid destination; role check; updates `current_location_id`; `audit_logs` (`LOCATION_CHANGE`) |
| **Delete** | Only when not Sold and no sale/audit references — FR-INV-07 |

### 12.5 Audit Trail

Every inventory operation produces an audit record:

| Field | Content |
|-------|---------|
| **User** | Actor user ID or service account ID |
| **User name** | Optional display name snapshot at time of action |
| **User role** | Role snapshot at time of action |
| **Timestamp** | UTC stored; displayed in business timezone **TBD** |
| **Request ID** | `X-Request-ID` correlation identifier |
| **Client platform** | `windows-desktop`, `macos-desktop`, `android`, `excel-sync`, `tally-sync` |
| **IP address** | Client source IP from request |
| **Device information** | User-agent / app version where available |
| **Action** | `CREATE`, `UPDATE`, `LOCATION_CHANGE`, `STATUS_CHANGE`, `SYSTEM_ACTION`, etc. |
| **Entity** | Inventory ID + serial number |
| **Before / after** | JSON snapshot of changed fields (previous and new values) |
| **Reason** | Optional note on location transfer or manual sale |
| **Location transfer (when applicable)** | From location, to location, actor, timestamp — FR-AUD-08 |

Audit records are **immutable** — no UPDATE or DELETE.

### 12.6 Product Model Lifecycle

Product Models use lifecycle states **Active** and **Archived** (PRD §12.2). Enforced by `ProductModelService`.

```mermaid
stateDiagram-v2
    [*] --> active : Create
    active --> archived : Main Admin archives
    archived --> active : Main Admin restores
    active --> [*] : Delete (no history only)
    archived --> [*] : Delete (no history only)
```

| Rule | Service Behaviour |
|------|-------------------|
| Archive | Set `status = archived`; hidden from inventory creation and Salesperson default views |
| Restore | Set `status = active` |
| Permanent delete | Allowed only if no inventory items, sales, or audit references ever existed |
| New inventory | `InventoryService` rejects archived product models |

**Version 1 excluded inventory fields:** Purchase Date, Purchase Cost, and Remarks are **not** modeled (PRD §10.5).

---

## 13. Search Engine

### 13.1 Search Philosophy

Search is a **first-class capability** (N12, BR-13). It must be:

1. **Accessible** — global search on every primary screen including dashboard
2. **Fast** — perceived instant response on desktop
3. **Correct** — results reflect current authoritative state
4. **Product-specification-aware** — finds laptops by CPU, GPU, RAM, storage via Product Model fields
5. **Color-aware** — exact and partial match on per-unit Color attribute
6. **Multi-filter** — Brand, Model, Serial, CPU/GPU/RAM/Storage, Color, Location, and Status combinable
7. **Keyboard-first** — desktop shortcuts; barcode scanner compatible

### 13.2 Search Dimensions

| Dimension | Match Type | Priority |
|-----------|------------|----------|
| **Serial Number** | Exact + prefix | Highest — direct to unit detail |
| **Model Number** | Exact + partial | High — grouped results |
| **Brand** | Exact + partial | High |
| **Color** | Exact + partial | High — per-unit attribute |
| **CPU / GPU / RAM / Storage** | Match on `product_model` specification fields | High — `4060`, `i7`, `16` |
| **Location** | Filter / exact | Medium |
| **Status** | Filter / exact | Medium |
| **Combined** | AND composition | All selected filters applied |

### 13.3 Search Flow

```mermaid
flowchart LR
    Q[User Query] --> P[SearchService.parse_query]
    P --> C{Query Type?}
    C -->|Serial exact| D1[Direct lookup index]
    C -->|Serial prefix| D2[Prefix scan]
    C -->|Color filter| D5[B-tree / ILIKE on color]
    C -->|Spec term| D3[Product Model field match]
    C -->|Model/brand| D4[Grouped query]
    D1 & D2 & D3 & D4 & D5 --> R[Paginated results]
    R --> API[JSON response]
```

### 13.4 Result Presentation

| Query Pattern | Response Shape |
|---------------|----------------|
| Exact serial match | Single unit detail |
| Model / brand / spec | Grouped by brand → model with available count; expandable serials |
| Location / status filter | Filtered list with pagination |

Presentation rules per PRD Section 11 — UI renders groups; API returns structured groups.

**Query parsing:** Formal behaviour defined in `docs/specs/search-query-spec.md` (**required before search implementation**).

### 13.5 Indexing Strategy (Conceptual)

| Index | Purpose |
|-------|---------|
| `UNIQUE (serial_number)` | O(1) exact serial lookup |
| `(product_model.cpu)`, `(product_model.gpu)`, etc. | Product specification search |
| `(color)` or `GIN (color gin_trgm_ops)` | Color exact and partial filter |
| `(brand_id, model_number)` | Model-grouped browsing |
| `(current_location_id, status)` | Location dashboard filters |

### 13.6 Performance Targets

Numeric targets **TBD** in NFR-PERF-01. Architectural commitment:

- Serial exact lookup: < 50ms server-side at V1 scale
- Product specification search: < 200ms server-side at V1 scale
- All list endpoints paginated — default page size 50
- No unbounded `SELECT *` without `LIMIT`

---

## 14. Synchronization Services

### 14.1 Separation of Concerns

| Service | Direction | Mutates Inventory? | Mutates Excel/Tally? |
|---------|-----------|--------------------|-----------------------|
| **Excel Sync** | PostgreSQL → API → Excel | **No** — read-only via API | Yes — overwrites export file |
| **Tally Sync** | Tally → API → PostgreSQL | **Yes** — via API sale endpoint | **No** |

Both are **separate Windows Services** for failure isolation and independent scheduling.

### 14.2 Excel Synchronization

```mermaid
sequenceDiagram
    participant U as Main Admin / Scheduler
    participant A as Backend API
    participant S as Excel Sync Service
    participant F as Excel File

    U->>A: POST /sync/excel/trigger (or scheduled job creation)
    A->>A: SyncJobService creates job (pending)
    S->>A: GET /sync/jobs/pending (service JWT)
    A-->>S: sync_job_id
    S->>A: GET /sync/excel/export?cursor= (paginated, service JWT)
    A-->>S: inventory page JSON
    S->>S: openpyxl assemble workbook
    S->>F: write .tmp then atomic rename
    S->>A: POST /sync/jobs/{id}/complete {success, count}
```

| Concern | Design |
|---------|--------|
| **Schedule** | APScheduler creates sync jobs via internal API call or job table poll — default **TBD** |
| **Manual trigger** | `POST /api/v1/sync/excel/trigger` → `SyncJobService` creates job; **API never writes Excel** |
| **Export** | Paginated API export (`?cursor=`) — worker assembles workbook; avoids memory exhaustion at scale |
| **Columns** | Brand, Model, Serial, **Color**, CPU, GPU, RAM, Storage (from Product Model), Current Location, Status — per FR-XLS-03 |
| **File permissions** | NTFS: sync service account write-only on export dir; staff read via share optional |
| **Conflict** | Excel file locked → skip job cycle, log warning, retry next run |
| **Atomic write** | Write to `.tmp` then rename — preserve last-known-good copy in `exports/archive/` |
| **Idempotency** | Re-running same `sync_job_id` overwrites export; no duplicate inventory effects |
| **Never import** | No code path reads Excel into inventory (BR-08) |

### 14.3 Tally Integration

> **Architecture status:** **Frozen** — official synchronization behaviour is defined in [docs/integrations/tally-erp9/sync-strategy.md](integrations/tally-erp9/sync-strategy.md). Implementation must follow that document exactly.

**Billing boundary:** Tally ERP 9 is the **primary source of truth for sales**. WEBSTUDIO IMS reads invoices only. IMS **never** creates invoices, credit notes, or billing entries in Tally. Manual **Mark as Sold** (Admin/Main Admin only) remains for exceptional cases and generates normal audit entries.

```mermaid
sequenceDiagram
    participant T as Tally ERP 9
    participant S as Tally Sync Service
    participant A as Backend API

    loop Every sync interval (default 30 min)
        loop Each configured company
            S->>T: Read invoices since cursor
            T-->>S: Invoice XML
            S->>S: parse with defusedxml
            S->>A: POST /integrations/tally/invoices/process
            alt processing_status = success
                A->>A: tally_sync_log (skipped)
            else partial_success
                A->>A: retry failed lines only
            else failed or new
                A->>A: process all inventory-related lines
            end
            loop Each line (independent transaction)
                A->>A: evaluate line (§14.3.1)
                A->>A: update tally_processed_invoice_lines
            end
            A->>A: derive processing_status (success | partial_success | failed)
            A->>A: tally_sync_log (this run)
            A->>A: update tally_processed_invoice
            S->>A: PATCH company sync state
        end
    end
```

| Concern | Design |
|---------|--------|
| **Direction** | Tally → IMS read-only; no writes to Tally |
| **Multi-company** | Independent sync state per Tally company; failure in one company does not block others |
| **Initial companies** | WEBSTUDIO; ASUS Exclusive Store |
| **Per-company state** | `last_successful_sync_time`, `last_processed_voucher_identifier` |
| **Interval** | Configurable via `system_settings` — default **1800 seconds (30 minutes)** |
| **Manual trigger** | `POST /integrations/tally/sync/trigger` — Admin and Main Admin (**Sync Now**) |
| **Invoice model** | Each line processed **independently**; one line failure never stops others |
| **Matching** | Serial Number authoritative — search **`available`** inventory only; product model verification **after** sale (informational); global serial uniqueness (BR-01) |
| **Duplicate sale** | Serial in **sold** inventory → notification only; no inventory or audit mutation |
| **Model mismatch** | Serial matched and sold; normalized models genuinely differ → **`product_model_mismatch`** notification (informational) |
| **Missing data** | Model exists / serial missing → `serial_number_missing`; serial exists (non-available) / model not in catalog → `product_model_missing`; neither → ignore |
| **Invoice state** | `tally_processed_invoice.processing_status` — SUCCESS only when all lines complete |
| **Partial retry** | `partial_success` → retry failed lines only via `tally_processed_invoice_lines` |
| **Crash recovery** | SUCCESS skip; PARTIAL_SUCCESS resume; FAILED full retry |
| **Transactions** | Line-level — one failed line never rolls back siblings |
| **Invoice idempotency** | Skip when `processing_status = success`; not before |
| **Validation** | All XML untrusted — `defusedxml`; schema validation |
| **Partial failure** | One line or company failure does not roll back other lines or companies |
| **Manual mark-as-sold** | Admin/Main Admin only via `POST /sales/reflect` — invoice number required |
| **Tally Sync Log** | Per-invoice sync statistics — separate from Audit Log (§14.3.3) |
| **Audit Log** | Business events only — sold, manual sale, location change, inventory created |
| **Dashboard** | Tally Synchronization Dashboard — connection, companies, last sync, next sync, pending notifications, sync log, Sync Now |
| **Notifications** | Duplicate Sale, Serial Number Missing, Product Model Missing, **Product Model Mismatch**, Tally Sync Completed, Synchronization Failure |
| **V1 exclusions** | Returns, refunds, credit notes, cancellation, auto inventory creation from Tally |

#### 14.3.1 Invoice Line Decision Workflow

For each line on a **new** (not yet processed) invoice:

| Step | Condition | Action |
|------|-----------|--------|
| 1 | Serial found in **`available`** inventory | Mark **sold**; create `sale`; audit (`TALLY_SYNC`) — **serial is authoritative** |
| 1a | After step 1 — normalized invoice model genuinely differs from IMS | **`product_model_mismatch`** notification (informational); **does not** reverse sale |
| 2 | Serial found in **`sold`** inventory | **Duplicate Sale** notification; no inventory/audit change |
| 3 | Product model exists in IMS; serial not found | **Serial Number Missing** notification |
| 4 | Serial exists in IMS (non-available); invoice product model not in catalog | **Product Model Missing** notification |
| 5 | Neither serial nor model in IMS | **Ignore** — accessory/service; no notification |

**Matching priority:** (1) Serial Number — authoritative; (2) Product Model — verification only. Product model names **must never** prevent a successful serial match from marking inventory sold.

Multiple laptops on one invoice share invoice number, sale date, and customer name; each line is evaluated independently.

#### 14.3.2 Invoice Processing Status and Completion

| `processing_status` | Definition |
|-----------------------|------------|
| **SUCCESS** | All inventory-related lines completed. Fully processed — future syncs skip (log: `skipped`). |
| **PARTIAL_SUCCESS** | Some lines completed; some failed. Successful lines committed; failed lines retried. **Not** fully processed. |
| **FAILED** | Zero inventory updates. Entire invoice eligible for full retry. |
| **SKIPPED** | Log-only outcome when invoice already **SUCCESS**. |

**Completion rule:** Never set `processing_status = success` before all inventory-related lines finish. Promote to SUCCESS only when every such line reaches a terminal completed state.

#### 14.3.3 Partial Retry and Crash Recovery

| Prior state | After restart |
|-------------|---------------|
| SUCCESS | Skip — sync log `skipped` |
| PARTIAL_SUCCESS | Retry **failed lines only** — completed lines never reprocessed |
| FAILED | Retry entire invoice |

Tolerates application crash, database restart, server shutdown, and network interruption without duplicate inventory updates.

#### 14.3.4 Table Responsibilities

| Table | Role |
|-------|------|
| `tally_processed_invoices` | Invoice-level state and idempotency |
| `tally_processed_invoice_lines` | Per-line status for partial retry |
| `tally_sync_logs` | Execution history per attempt (diagnostics) |

Every sync run writes a `tally_sync_log` referencing the processed invoice where applicable.

#### 14.3.5 Tally Sync Log vs Audit Log

| Store | Purpose | Examples |
|-------|---------|----------|
| **Tally Sync Log** | Execution history per attempt — sync run ID, duration, retry count, statistics |
| **Audit Log** | Business state changes | Inventory sold, manual sale, location changed, inventory created |
| **Tally Integration Event** | Optional line-level diagnostic detail | Per-line outcome for reconciliation UI |

Synchronization statistics **must not** be written to the Audit Log.

#### 14.3.6 Notification Center

| Type | Trigger |
|------|---------|
| **Duplicate Sale Detected** | Serial already sold when Tally invoice line processed |
| **Serial Number Missing** | Model in IMS; serial from line not found |
| **Product Model Missing** | Serial in IMS; model not in catalog |
| **Tally Sync Completed** | Invoice or sync cycle completed (informational) |
| **Synchronization Failure** | Connection or company-level failure |

Lifecycle: **Unread** → **Read** → **Resolved** (resolved records retained permanently).

### 14.3.1 Tally POC Acceptance Checklist

**Tally integration implementation is blocked** until this checklist is completed against the production Tally ERP 9 instance.

| # | Criterion | Pass Required |
|---|-----------|---------------|
| 1 | Tally HTTP/XML API enabled and reachable from server IP | Yes |
| 2 | Sales voucher type(s) for laptop billing identified | Yes |
| 3 | Serial number Reliably extracted from voucher (field or narration pattern documented) | Yes |
| 4 | Duplicate voucher re-submission is idempotent (no double sale in API) | Yes |
| 5 | Poll interval measured; p95 latency within acceptable window **TBD** | Yes |
| 6 | Tally configuration steps documented for store IT | Yes |
| 7 | Recorded XML fixtures added to `packages/testing/fixtures/tally/` | Yes |
| 8 | POC report published in `docs/research/tally-poc-report.md` | Yes |

**Gate:** [ADR-0011](../adr/ADR-0011-tally-integration-strategy.md) Accepted only after all criteria pass.

### 14.4 Scheduling

| Service | Scheduler | Config |
|---------|-----------|--------|
| Excel Sync | APScheduler in worker process | Cron from settings table |
| Tally Sync | APScheduler | `tally_sync_interval_seconds` from settings — default **1800** (30 min) |
| DB Backup | Windows Task Scheduler | External script |

### 14.5 Retries

| Failure | Retry Policy |
|---------|--------------|
| API unreachable (sync worker) | Exponential backoff: 1m, 2m, 5m, 15m — max 5 attempts per cycle |
| Tally unreachable | Continue next poll interval; log warning |
| Excel locked | Skip cycle; retry next schedule |
| Sale mapping — serial not in available | Serial Number Missing notification; no retry |
| Product model missing on line | Product Model Missing notification; no retry |
| Duplicate sale (serial already sold) | Duplicate Sale notification; no retry |
| Invoice already SUCCESS | Skip — sync log `skipped`; no retry |
| Company sync failure | Log; create Synchronization Failure notification; continue other companies |

### 14.6 Failure Isolation

- Excel sync failure does **not** affect API or Tally sync
- Tally sync failure does **not** affect inventory reads or Excel export
- API remains available during sync failures — staff continue operations

### 14.7 Conflict Handling

| Conflict | Resolution |
|----------|------------|
| Excel vs PostgreSQL | PostgreSQL wins always — Excel is overwritten on next sync |
| Tally invoice already SUCCESS | Skip — sync log `skipped` |
| Tally invoice PARTIAL_SUCCESS | Retry failed lines only |
| Tally invoice FAILED | Full invoice retry |
| Tally line — serial already **sold** | Duplicate Sale notification; no inventory or audit change |
| Tally line — model exists, serial missing | Serial Number Missing notification |
| Tally line — serial exists, model missing | Product Model Missing notification |
| Tally line — neither serial nor model in IMS | Ignore; no notification (accessory/non-laptop) |
| Tally line — serial in **available** | Mark sold; sale + audit |
| Manual sale vs later Tally import (same invoice + serial) | Same transaction — no duplicate sale (FR-TLY-14) |
| Manual sale vs pending Tally sync | First successful write wins; duplicate path creates notification only |

---

## 15. Barcode Integration

### 15.1 Design Principle

**Barcode scanner input is equivalent to keyboard input** (BR-21, BC-02). No proprietary SDK, no separate scanner service, no Bluetooth pairing logic in V1.

### 15.2 Input Flow

```mermaid
flowchart LR
    SCAN[Scanner keystrokes] --> FIELD[Serial Number input field]
    FIELD --> SUBMIT{Auto-submit\non Enter?}
    SUBMIT -->|Yes| API[Submit form / search]
    SUBMIT -->|No| WAIT[Wait for user Enter]
    WAIT --> API
```

### 15.3 Supported Behaviour

| Behaviour | Detail |
|-----------|--------|
| **Wired USB** | HID keyboard wedge — plug and play |
| **Wireless** | Bluetooth keyboard wedge — no app changes |
| **Auto-focus** | Serial field focused on Add Inventory open (FR-BCD-02) |
| **Immediate populate** | Characters appear as scanned (FR-BCD-03) |
| **Auto-submit** | Configurable — scanner sends Enter suffix (FR-SET-07) |
| **Search** | Global search accepts scanner input (FR-SRH-09) |
| **Manual fallback** | Keyboard entry always available (BC-07) |

### 15.4 Validation

| Layer | Validation |
|-------|------------|
| Client | Trim whitespace; length hint |
| Server | Serial format rules **TBD**; uniqueness on create; existence on search |

### 15.5 Error Handling

| Scenario | UX |
|----------|-----|
| Duplicate serial on add | 409 — "Serial number already exists" |
| Serial not found in search | Empty state — "No laptop found" |
| Partial scan | User can backspace and rescan |
| Scanner not working | Manual entry — no workflow change |

### 15.6 Android

Barcode wedge keyboards work on Android when supported by device. Camera-based scanning is **out of scope V1**.

---

## 16. Security Architecture

### 16.1 Security Principles

| Principle | V1 Implementation | Future |
|-----------|---------------------|--------|
| **Least privilege** | RBAC; `webstudio_app` DB user; service accounts | Fine-grained permissions |
| **Defense in depth** | HTTPS + JWT + firewall + LAN isolation + Electron hardening | VPN + MFA |
| **Fail secure** | Deny on auth failure; no anonymous inventory access | — |
| **No secrets in Git** | Environment variables only | Secret manager |
| **Validate all input** | Pydantic + service rules + parameterized SQL | — |
| **Audit sensitive actions** | All mutations and admin actions logged | SIEM integration |
| **Isolate integrations** | Separate processes; untrusted external input | — |
| **Assume LAN is not authorization** | JWT required on every request | — |

### 16.2 Transport Security

| Aspect | Production | Development |
|--------|------------|---------------|
| **Client ↔ API** | **HTTPS only** — TLS at Uvicorn with internal CA server certificate | HTTP on `localhost` permitted |
| **API ↔ PostgreSQL** | localhost TCP — no network exposure | Same |
| **Sync ↔ Tally** | HTTP on LAN — Tally native protocol | Same |
| **Certificates** | Internal CA — root installed on all clients (see §1.4) | Self-signed or HTTP localhost |

**Production rule:** Plain HTTP to the API is **rejected** in production configuration.

**Future remote access:** Public CA or VPN-terminated TLS; optional reverse proxy per ADR-0012 (reserved — not authored).

### 16.3 JWT Security

- Short-lived access tokens
- Refresh rotation with reuse detection
- Validate `iss`, `aud`, `exp`, `sub` on every request
- Service accounts for sync workers — separate credentials, scoped permissions
- No JWT in URLs or logs

### 16.4 Password Security

- **bcrypt** cost ≥ 12 (approved V1)
- Argon2id documented as future improvement — not V1 unless ADR amended
- No plaintext passwords in logs, audit, or error messages
- Force password change on first login and after admin reset

### 16.5 Secrets Management

| Secret | Storage |
|--------|---------|
| JWT signing key | Server environment variable |
| Database password | Server environment variable |
| Service account credentials | Server environment variable |
| Tally connection parameters | Server environment variable |
| Client config (server URL) | Installer config / admin settings — no secrets |

### 16.6 Input Validation & Injection Prevention

| Threat | Mitigation |
|--------|------------|
| SQL injection | SQLAlchemy parameterized queries exclusively |
| XML injection / XXE | `defusedxml` for Tally parsing |
| XSS (desktop) | React escaping; CSP; no `dangerouslySetInnerHTML` |
| CSRF | Not applicable — Bearer token API, no cookie auth |
| Rate limiting | `slowapi` — login 10/min/IP; API limits **TBD** |

### 16.7 Electron Hardening

| Control | Setting |
|---------|---------|
| contextIsolation | `true` |
| nodeIntegration | `false` |
| sandbox | `true` |
| webSecurity | `true` |
| remote module | disabled |
| IPC | whitelist only |
| Token storage | OS keychain |

### 16.8 Android Security

| Control | Detail |
|---------|--------|
| Token storage | Android Keystore + EncryptedSharedPreferences |
| Certificate pinning | Optional V1; mandatory before internet |
| Root detection | Warning only V1 |
| Backup | `android:allowBackup="false"` for app data |

### 16.9 Database Security

| Control | Detail |
|---------|--------|
| Application user | Least privilege — no DDL in production |
| Network | localhost only |
| Backups | Encrypted at rest on backup volume |
| Audit table | Append-only grants |

### 16.10 Windows Security

| Control | Detail |
|---------|--------|
| Firewall | API port **8443** inbound from store subnet only |
| Service accounts | Dedicated accounts per service — not interactive |
| Antivirus exclusions | PostgreSQL data dir if latency observed |
| Updates | Scheduled off-peak; verify service recovery |
| Interactive use | Prohibited on dedicated server |

### 16.11 LAN Security

| Control | Detail |
|---------|--------|
| Network scope | Office Wi-Fi only — no port forwarding |
| Wi-Fi | WPA2/WPA3; guest network segregated **recommended** |
| Static IP | Server uses static local IP — clients configured |
| Future internet | VPN or Zero Trust required — ADR mandatory |

### 16.12 Audit Logging

| Event | Logged | Enrichment Fields |
|-------|--------|-------------------|
| Login success/failure | Yes | IP, client platform, request ID |
| Permission denied | Yes | IP, user, attempted action |
| Inventory mutations | Yes | User, before/after, reason, request ID, IP, platform |
| User management | Yes | Actor, target user, before/after |
| Settings changes | Yes | Actor, setting key, before/after |
| Sync results | Yes | Service account, job ID, outcome |

All audit records include: **user**, **timestamp (UTC)**, **request ID**, **client platform**, **IP address**, **device information** (user-agent / app version), **before/after values**, and **reason** where applicable — per §12.5.

### 16.13 Future Internet Deployment

When remote access is required:

1. ADR for reverse proxy (Caddy vs nginx) if TLS termination moves off API process
2. Public CA certificate or VPN with existing internal CA
3. Certificate pinning on Android (mandatory)
4. Penetration test before exposure

### 16.14 Threat Model (Version 1)

Concise STRIDE-oriented threat model for on-premise LAN deployment with HTTPS.

| Threat | Description | Mitigation | Residual Risk |
|--------|-------------|------------|---------------|
| **Malicious client** | Custom HTTP client bypassing UI | JWT + RBAC on every endpoint; server-side validation | Low — requires stolen credentials |
| **Stolen JWT** | Access or refresh token intercepted on LAN | HTTPS encrypts transit; short access token TTL; refresh rotation; session invalidation by Main Admin | Low with HTTPS |
| **Office network attack** | ARP spoofing, rogue Wi-Fi AP | WPA2/WPA3; guest network segregation; HTTPS | Low-Medium — physical LAN access |
| **Rogue Tally data** | Crafted XML voucher | `defusedxml`; schema validation; `SaleService` idempotency; serial existence check | Medium — depends on POC mapping |
| **Excel tampering** | Staff edits Excel file | Excel is non-authoritative; next sync overwrites; file ACLs on server | Low — business process |
| **Insider misuse** | Admin abuses privileges | RBAC; immutable audit with IP/platform; Main Admin audit log review | Medium — trust model |
| **Ransomware / disk encryption** | Server data encrypted | Off-server backups; tested restore | Medium — ops dependent |
| **Stolen server** | Physical theft of server PC | Disk encryption; backups off-server; no internet exposure | Low-Medium |

**Attack surface summary:** HTTPS API on LAN (port 8443); PostgreSQL localhost only; Tally XML port; Excel file share (optional). No public internet exposure in V1.

---

## 17. Logging & Observability

### 17.1 Structured Logs

| Aspect | Standard |
|--------|----------|
| Format | JSON in production (Loguru) |
| Fields | `timestamp`, `level`, `service`, `correlation_id`, `user_id`, `message`, `context` |
| Location | File per service under `D:\WEBSTUDIO-IMS\logs\` |
| Rotation | Size-based rotation — 100MB **TBD** |
| Secrets | Never logged |

### 17.2 Audit Logs vs Operational Logs

| Type | Storage | Purpose |
|------|---------|---------|
| **Audit** | PostgreSQL `audit_log` table | Compliance, inventory history, admin accountability |
| **Operational** | Log files | Debugging, integration diagnostics |

### 17.3 Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness — process running |
| `GET /health/ready` | Readiness — DB connected, migrations current, disk space ≥ 20% on data volume |
| `GET /health/integrations` | Last sync timestamps, failure counts — Main Admin |

### 17.4 Diagnostics

- Main Admin settings screen shows: service status, last Excel sync, last Tally poll, DB connection, disk space warning
- Log viewer: **TBD** — tail last N lines via admin UI or file access on server

### 17.5 Metrics (Future)

| Metric | Tool |
|--------|------|
| Request latency | Prometheus + Grafana **Future** |
| Error rate | Sentry **Future** |
| Disk space | Windows perf counters + alert **TBD** |

### 17.6 Correlation

`X-Request-ID` generated at API boundary — propagated to audit entries, sync worker logs, and outbound API calls from Excel/Tally workers.

---

## 18. Failure & Recovery

### 18.1 Failure Matrix

| Failure | Impact | Detection | Recovery |
|---------|--------|-----------|----------|
| **Database unavailable** | All mutations fail | `/health/ready` fails; API returns 503 | PostgreSQL service restart; restore from backup if corrupted |
| **Server reboot** | Brief outage | Clients show connection error | Windows Services auto-start; verify post-reboot checklist |
| **Power failure** | Unclean shutdown | Services down | UPS recommended; BIOS auto-power-on; verify DB integrity |
| **Network outage** | Clients cannot reach API | Client error UI | Staff wait; no local queue V1 |
| **Excel file locked** | Sync skipped | Sync log warning | Retry next schedule; notify Main Admin |
| **Tally unavailable** | Sales not auto-reflected | Tally sync log + Synchronization Failure notification | Manual mark-as-sold (Admin/Main Admin); Sync Now when Tally returns |
| **Client disconnected** | Single user affected | Client retry | Reconnect; refresh token or re-login |
| **Disk full** | DB and sync fail | Health check disk monitor | Alert; expand volume; prune logs/backups |

### 18.2 Recovery Procedures

| Scenario | Runbook Location |
|----------|------------------|
| Database restore | `docs/deployment/database/` |
| Service restart | `docs/deployment/server/` |
| Full disaster recovery | `docs/operations/` |
| Integration failure | `docs/integrations/` |

All procedures tested before production go-live (NFR-REC-02).

### 18.3 Data Integrity Guarantees

- Transactions prevent partial mutations
- Idempotent Tally processing prevents duplicate sales
- Atomic Excel writes prevent corrupted exports
- Backups enable point-in-time recovery (with WAL)

### 18.4 Backup Recovery Principle

> **A backup is not considered valid unless it has been successfully restored and verified.** Monthly automated restore tests are mandatory before production go-live and ongoing in operations (NFR-REC-02).

---

## 19. Configuration Management

### 19.1 Configuration Layers

```mermaid
flowchart TB
    ENV[Environment Variables\nsecrets, bind address]
    DB[Database Settings\nbusiness configurable]
    CLIENT[Client Config\nserver URL, theme]
    INSTALL[Installer Defaults\nfirst-run wizard]

    ENV --> API[Backend API]
    DB --> API
    INSTALL --> CLIENT
    CLIENT --> DESKTOP[Desktop / Android]
```

### 19.2 Environment Variables (Server)

| Variable | Example | Secret |
|----------|---------|--------|
| `DATABASE_URL` | `postgresql://webstudio_app:***@localhost/webstudio` | Yes |
| `JWT_SECRET_KEY` | — | Yes |
| `API_HOST` | `0.0.0.0` | No |
| `API_PORT` | `8443` | No |
| `SSL_CERT_FILE` | `D:\WEBSTUDIO-IMS\certs\server.pem` | No |
| `SSL_KEY_FILE` | `D:\WEBSTUDIO-IMS\certs\server-key.pem` | Yes |
| `LOG_LEVEL` | `INFO` | No |
| `EXCEL_OUTPUT_PATH` | `D:\WEBSTUDIO-IMS\exports\` | No |
| `TALLY_HOST` | `192.168.1.50` | No |
| `TALLY_PORT` | `9000` | No |

### 19.3 Database-Managed Settings

| Setting | Key | Configurable By | Notes |
|---------|-----|-----------------|-------|
| System initialized | `system_initialized` | First-Time Setup only | `boolean` — **not** inferred from Main Admin existence; controls setup wizard |
| Company name | `company_name` | First-Time Setup | Set during initialization |
| Excel sync schedule | `excel_sync_cron` | Main Admin | |
| Tally poll interval | `tally_poll_interval_seconds` | Main Admin | |
| Session timeout | `session_timeout_minutes` | Main Admin | |
| Lockout threshold | `lockout_threshold` | Main Admin | |
| Barcode auto-submit | `barcode_auto_submit` | Main Admin | |
| Business display name | `business_display_name` | Main Admin | May mirror `company_name` after setup |

### 19.4 Client Settings

| Setting | Storage | Notes |
|---------|---------|-------|
| Server HTTPS URL | Encrypted local config | Set via discovery confirmation or manual configuration |
| Theme preference | Local + API user preference | |
| Window size/position | Local | Desktop only |

**First launch:** automatic LAN server discovery → confirm single server / select among multiple / fall back to manual URL with Test Connection. After connection, client calls `GET /api/v1/setup/status` before Login or Setup Wizard.

**Future:** mDNS / Bonjour or equivalent for discovery — **TBD** in ADR.

### 19.5 Versioning

| Artifact | Versioning |
|----------|------------|
| API | `/api/v1/` URL prefix |
| Client | Semver in app manifest; minimum API version check **TBD** |
| Database | Alembic migration version |
| Config schema | Backward-compatible settings additions only |

---

## 20. Deployment Architecture

### 20.1 Production Topology

```
Office Wi-Fi LAN
└── Dedicated Windows 11 Pro Server PC (static IP)
    ├── PostgreSQL 16          [Windows Service — Automatic]
    ├── WEBSTUDIO API          [Windows Service — NSSM — Automatic]
    ├── WEBSTUDIO Excel Sync   [Windows Service — NSSM — Automatic]
    └── WEBSTUDIO Tally Sync   [Windows Service — NSSM — Automatic]

Store Desktops / Android → https://{server-host}:8443/api/v1/
```

### 20.2 Windows Services

| Service | Executable | Recovery | Depends On |
|---------|------------|----------|------------|
| PostgreSQL | Official installer service | Restart on failure | — |
| WEBSTUDIO API | `uvicorn apps.backend.main:app --ssl-certfile ... --ssl-keyfile ...` | Restart on failure × 3 | PostgreSQL |
| WEBSTUDIO Excel Sync | `apps.server.excel_worker` | Restart on failure × 3 | WEBSTUDIO API |
| WEBSTUDIO Tally Sync | `apps.server.tally_worker` | Restart on failure × 3 | WEBSTUDIO API |

**Preferred:** NSSM for Python workers unless ADR documents `pywin32` equivalent.

All services: **Automatic (Delayed Start)**; run under dedicated service accounts (not interactive users).

### 20.3 Client Installation

| Platform | Method |
|----------|--------|
| Windows | `.msi` via Electron Builder — LAN share |
| macOS | `.dmg` — manual install |
| Android | Signed `.apk` — sideload V1 |

First-run: install internal CA root; automatic server discovery or manual HTTPS URL configuration; `GET /api/v1/setup/status`; First-Time Setup Wizard or login. Client installations **never** create users.

### 20.4 Network Configuration

| Setting | Value |
|---------|-------|
| Server IP / hostname | Static local IP or `webstudio-server.local` — e.g., `192.168.1.100` |
| API port | `8443` (HTTPS — configurable) |
| PostgreSQL | `localhost:5432` only — not exposed to LAN |
| Firewall | Allow **8443/TCP** inbound from store subnet only (e.g., `192.168.1.0/24`) |
| NTP | Server synchronized to reliable time source — required for audit and JWT |

### 20.5 HTTPS & Internal CA (Production)

HTTPS is **mandatory** for all production deployments. See [§1.4](#14-transport--tls-policy) for full certificate policy.

| Step | Action |
|------|--------|
| 1 | Create or designate internal CA |
| 2 | Issue server certificate with SAN for hostname + static IP |
| 3 | Configure Uvicorn TLS via `SSL_CERT_FILE` and `SSL_KEY_FILE` |
| 4 | Distribute CA root to Windows, macOS, and Android clients |
| 5 | Verify `https://{server}:8443/health` from each client platform |

**Future remote access:** Public CA or VPN; optional reverse proxy per ADR-0012 (reserved — not authored).

### 20.6 Backups & Recovery

| Asset | Method | Location |
|-------|--------|----------|
| PostgreSQL | `pg_dump` daily (Windows Scheduled Task) + manual trigger via admin | `D:\WEBSTUDIO-IMS\backups\` |
| Excel archive | Copy before overwrite | `D:\WEBSTUDIO-IMS\exports\archive\` |
| Configuration | Export script (env templates, settings snapshot) | `D:\WEBSTUDIO-IMS\backups\config\` |
| TLS certificates | Secure copy of server cert, key, and CA root | `D:\WEBSTUDIO-IMS\backups\certs\` |
| Off-server | Robocopy to NAS **recommended** | LAN NAS path |

**Retention:** Minimum 30 days online; policy **TBD** with business.

**Verification rule:** A backup is **not considered valid** until a monthly automated restore test succeeds against an isolated database instance. Failed verification alerts Main Admin and blocks reliance on that backup set.

**Recovery workflow:**

1. Stop WEBSTUDIO API and sync services
2. Restore latest verified `pg_dump` to PostgreSQL
3. Run `alembic upgrade head` if schema drift
4. Verify row counts and serial spot-checks
5. Start services in [startup order](#209-service-startup--shutdown-order)
6. Smoke test from desktop client

### 20.7 Future Cloud Migration

The architecture supports cloud migration without redesign:

1. PostgreSQL → managed RDS or equivalent
2. API + workers → containers or VM
3. Add reverse proxy + TLS
4. Clients point to new URL via config update
5. No business logic changes — deployment packaging only

### 20.8 Installation & Deployment Workflow

Official sequence for fresh production deployment:

| Step | Action | Verification |
|------|--------|--------------|
| **1** | Prepare Windows 11 Pro dedicated server PC; static IP; UPS connected | Pingable on LAN |
| **2** | Install PostgreSQL 16; create `webstudio` DB and `webstudio_app` role | `psql` connect test |
| **3** | Create directory structure: `D:\WEBSTUDIO-IMS\{certs,logs,backups,exports}` | Paths exist; NTFS permissions set |
| **4** | Establish internal CA; issue server certificate; store in `certs\` | OpenSSL verify |
| **5** | Deploy Python venv; install backend + worker packages from release artifact | Import test |
| **6** | Configure `.env` from `config/env/.env.example` (no secrets in Git) | Settings load |
| **7** | Run `alembic upgrade head` (includes `pg_trgm` extension) | Migrations current |
| **8** | Register PostgreSQL Windows Service — Automatic start | Service running |
| **9** | Register WEBSTUDIO API via NSSM with TLS flags — Automatic start | `https://server:8443/health` returns 200 |
| **10** | Register Excel Sync and Tally Sync services — Automatic start | Services running; logs clean |
| **11** | Configure Windows Firewall — 8443 from store subnet only | Port scan from LAN |
| **12** | Schedule backup task + monthly restore verification script | Test dump created |
| **13** | Install desktop clients (.msi / .dmg); distribute internal CA root | HTTPS connectivity and setup status check succeed |
| **14** | Install Android APK; configure network security config with CA | HTTPS connectivity and setup status check succeed |
| **15** | Complete First-Time Setup Wizard from any connected client (if `system_initialized = false`) | Main Admin created; `system_initialized = true`; login succeeds |
| **16** | Run system verification checklist (health, search, add inventory, sync job, backup) | All pass — see `docs/deployment/server/` |

### 20.9 Service Startup & Shutdown Order

**Startup order** (after reboot or maintenance):

1. **PostgreSQL** — database must be available first
2. **WEBSTUDIO API** — all clients and workers depend on API
3. **WEBSTUDIO Excel Sync** — depends on API
4. **WEBSTUDIO Tally Sync** — depends on API

Configure Windows Service **dependencies** where supported. Post-reboot verification: run health check from one desktop client within 5 minutes of boot.

**Shutdown order** (planned maintenance):

1. **WEBSTUDIO Tally Sync** — stop accepting new polls
2. **WEBSTUDIO Excel Sync** — complete or cancel pending jobs
3. **WEBSTUDIO API** — drain in-flight requests (graceful shutdown)
4. **PostgreSQL** — last, after all connections closed

### 20.10 Update Strategy

| Component | V1 Approach | Rollback |
|-----------|-------------|----------|
| **Server (API + workers)** | Stop services → backup DB → deploy new Python artifact → `alembic upgrade head` → restart in startup order | Restore previous artifact + DB backup if migration fails |
| **Database migrations** | Alembic forward-only in production; test on copy first | Restore from pre-upgrade verified backup |
| **Desktop (Windows/macOS)** | Distribute new `.msi`/`.dmg` via LAN share; manual install | Reinstall previous installer version |
| **Android** | Distribute new signed `.apk`; sideload | Reinstall previous APK |
| **TLS certificates** | Renew before expiry; distribute updated CA if rotated | Restore cert backup from `backups\certs\` |

**Version compatibility:** Clients declare `X-Client-Version` header; API returns minimum supported version in `/health`. Breaking API changes require `/api/v2/` — not mixed silently.

**Future automatic updates:** Electron auto-update and Android Play distribution deferred — see §22.6. V1 uses manual distribution.

### 20.11 Server Initialization & Client Onboarding

#### 20.11.1 Server Initialization (One-Time)

The Dedicated Server PC is installed once. On startup the Backend reads `system_initialized` from `system_settings`. **Do not** treat Main Admin user existence as the initialization signal.

| State | Backend behaviour | Client behaviour |
|-------|-------------------|------------------|
| `system_initialized = false` | Accept `POST /api/v1/setup/initialize`; reject login and inventory mutations requiring users | Show First-Time Setup Wizard after connection |
| `system_initialized = true` | Reject duplicate initialize; enforce authentication on business endpoints | Show Login screen after connection |

**First-Time Setup Wizard** collects: Company Name, Main Admin Name, Username, Password, Confirm Password. On success:

1. Create Main Admin user (password stored as **bcrypt** hash only)
2. Set `system_initialized = true`
3. Persist `company_name`

The wizard must not appear again unless the database is intentionally reinitialized (restore/migration reset — operator procedure only).

#### 20.11.2 Client Installation & Discovery

Client installations (desktop, Android) **never create users**. First launch:

```mermaid
flowchart TD
    A[Client first launch] --> B[Attempt LAN server discovery]
    B --> C{Servers found?}
    C -->|One| D[Show server info — confirm]
    C -->|Multiple| E[User selects server]
    C -->|None / failed| F[Manual Server Configuration]
    F --> G[HTTPS URL + Test Connection + Save]
    D --> H[GET /api/v1/setup/status]
    E --> H
    G --> H
    H --> I{system_initialized?}
    I -->|true| J[Login screen]
    I -->|false| K[First-Time Setup Wizard]
```

**Manual configuration** fields: Server HTTPS URL, Test Connection, Save Configuration.

**Future:** automatic discovery may use mDNS / Bonjour or equivalent — protocol **TBD**; workflow is binding for V1.

#### 20.11.3 User Management Authority

Only **Main Admin** may: create users, disable users, reset passwords, assign roles. All user records and credential hashes live in PostgreSQL via the Backend API. Clients authenticate against the Backend only and do not store business data locally.

---

## 21. Performance Strategy

### 21.1 Expected Workload

| Dimension | V1 Estimate |
|-----------|-------------|
| Locations | 3 |
| Concurrent users | 5–15 |
| Inventory volume | **TBD** — estimate 500–5,000 laptops |
| Daily transactions | **TBD** — estimate 10–50 sales, 20–100 movements |
| Search queries | High — continuous during business hours |

### 21.2 Concurrency

- FastAPI async for I/O-bound request handling
- SQLAlchemy connection pool: size 10–20 **TBD** based on load test
- Uvicorn single worker sufficient V1; multiple workers if CPU-bound profiling warrants
- PostgreSQL handles concurrent readers + writers at this scale without replication

### 21.3 Search Performance

- Serial exact: unique index — sub-millisecond DB time
- Product specification search: target < 200ms at 5K units
- Dashboard aggregates: SQL `COUNT` with indexes — cache 30s **optional TBD**
- Client-side: debounce search input 300ms; show loading skeleton

### 21.4 Caching

| Cache | V1 | Future |
|-------|-----|--------|
| API response cache | No | Redis for dashboard aggregates |
| Client cache | Minimal | Offline cache Android |
| CDN | N/A on-premise | Cloud deployment |

### 21.5 Future Scaling

| Trigger | Response |
|---------|----------|
| > 10K laptops | Review query plans; add read replica **Future** |
| > 50 concurrent users | Multiple Uvicorn workers; connection pool tuning |
| Multi-branch | Location partitioning; possible read replicas per region |
| Cloud | Horizontal API scaling behind load balancer |

---

## 22. Future Evolution

The architecture is designed for **extension, not reinvention**. New modules add packages, API namespaces, and UI screens — they do not bypass the Backend API or introduce parallel data stores.

### 22.1 Extension Model

```mermaid
flowchart TB
    CORE[Core Platform\nInventory + Auth + Search + Audit]
    CORE --> W[Warranty Module V2+]
    CORE --> S[Service Center V2+]
    CORE --> A[Accessories Category]
    CORE --> P[Printers Category]
    CORE --> B[Multi-Branch]
    CORE --> C[Cloud Hosting]

    W & S & A & P & B & C --> API[Same Backend API Pattern]
    API --> PG[(Same PostgreSQL)]
```

### 22.2 Module Addition Pattern

| Step | Action |
|------|--------|
| 1 | PRD for new module |
| 2 | ADR if new technology or integration |
| 3 | Database migration — additive tables |
| 4 | Service layer additions — new services, same layers |
| 5 | API namespace `/api/v1/warranty/` etc. |
| 6 | UI screens in desktop and mobile |
| 7 | No changes to core inventory invariants |

### 22.3 Specific Future Modules

| Module | Architectural Approach |
|--------|------------------------|
| **Warranty** | New `WarrantyService`; links to inventory by serial; new lifecycle states via ADR |
| **Service Center** | `Under Service` state; repair ticket entity; separate UI section |
| **Accessories** | New category with quantity-based model — **requires ADR** for departure from serial-only |
| **Printers** | Same as accessories or serial-tracked — **TBD** |
| **Multi-Branch** | `branch_id` on locations; API filters; possible read replicas |
| **Cloud Hosting** | Containerize API; managed PostgreSQL; TLS; same OpenAPI contract |

### 22.4 What Does Not Change

- PostgreSQL as single source of truth
- Backend API as sole database gateway
- Thin clients
- Integration at edges
- Audit on mutations
- OpenAPI contract discipline

### 22.5 Engineering Conventions

Naming and structural rules for all Version 1 implementation:

| Artifact | Convention | Example |
|----------|------------|---------|
| **Services** | `{Domain}Service` in `apps/backend/services/` | `InventoryService`, `SaleService` |
| **Repositories** | `{Entity}Repository` in `infrastructure/repositories/` | `InventoryRepository` |
| **Routers** | `{domain}.py` in `api/routers/`; URL paths `snake_case` plural | `inventory.py` → `/api/v1/inventory` |
| **DTOs (API)** | `{Action}{Entity}Request/Response` Pydantic models | `CreateInventoryRequest` |
| **Domain types** | PascalCase nouns in `packages/shared-kernel/domain/` | `InventoryItem`, `LifecycleState` |
| **Validation** | Pydantic for API; service methods for business rules; Zod for client UX only | — |

**Architectural rules (mandatory):**

1. **Routers never access repositories directly** — routers → services → repositories only.
2. **Business rules live only in services** — not in routers, repositories, clients, or integrations.
3. **Services never depend on UI** — no imports from `apps/desktop` or `apps/mobile`.
4. **Integrations never bypass services** — workers call API endpoints; API delegates to services.
5. **No ORM models in services** — domain types at service boundary (see §7.11).

Reference implementation guides: `docs/development/platform-guides/backend.md` (**TBD**).

### 22.6 Deferred Future Enhancements

The following are **explicitly out of Version 1 scope**. Do not implement without ADR:

| Enhancement | Rationale for Deferral |
|-------------|------------------------|
| **Domain Events** (in-process or bus) | Polling + sync jobs sufficient for V1 scale |
| **Background Job Abstraction** (`JobRunner` interface) | APScheduler in two workers is adequate |
| **WebSockets** | No real-time requirement for 5–20 users |
| **File Storage Abstraction** | Excel path constant sufficient; images module future |
| **Secret Rotation automation** | Manual rotation documented in ops runbook first |
| **Settings change notifications to workers** | Workers poll settings on interval V1; restart acceptable |
| **Native Android networking module** | JS token handling acceptable with HTTPS + short TTL |
| **mDNS / Bonjour server discovery** | Manual URL + workflow defined V1; protocol selection **TBD** |
| **Redis / caching layer** | PostgreSQL performance sufficient at V1 scale |
| **Audit cold archival** | Monitor growth; archive when retention policy requires |

---

## 23. Architecture Decision Summary

### 23.1 Major Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| AD-01 | Backend framework | FastAPI | OpenAPI-native; async; Python ecosystem for integrations |
| AD-02 | Database | PostgreSQL 16 | ACID; trigram search; mandated by Project Bible |
| AD-03 | Desktop shell | Electron | Team productivity; shadcn/ui fit; acceptable with hardening |
| AD-04 | Mobile | React Native (Android) | TypeScript shared patterns; not shared UI |
| AD-05 | Backend structure | Layered + hexagonal integrations | Testable; clear; appropriate for team size |
| AD-06 | Deployment | Windows 11 Pro on-premise | Business environment; Tally alignment |
| AD-07 | Process model | 3 Windows Services + PostgreSQL | Failure isolation; auto-start |
| AD-08 | Transport (production) | HTTPS with internal CA | NFR-SEC-01; TLS at API; dev HTTP localhost only |
| AD-09 | Auth | JWT + bcrypt + RBAC | Approved stack; stateless API |
| AD-10 | Excel direction | One-way export via Sync Jobs | BR-07; API never writes Excel |
| AD-11 | Tally direction | Read billing; mutate via SaleService API | N4; billing not replaced |
| AD-12 | Offline | Online-first V1 | Simplicity; avoids conflict resolution |
| AD-13 | Search | PostgreSQL trigram + indexes | No Elasticsearch V1 |
| AD-14 | Monorepo | pnpm + Python apps/packages | Shared contracts; ADR-0001 |
| AD-15 | Sync orchestration | Sync Job table; worker execution | Manual trigger safety |
| AD-16 | Domain mapping | ORM ↔ domain ↔ DTO separation | §7.11 |

### 23.2 ADR Index

| ADR | Title | Priority | Status |
|-----|-------|----------|--------|
| ADR-0001 | Monorepo structure | — | Proposed — [0001-monorepo-structure.md](../adr/records/0001-monorepo-structure.md) |
| ADR-0002 | Backend stack (FastAPI + PostgreSQL + SQLAlchemy) | Critical | **Consolidated** — [TECH_STACK.md](TECH_STACK.md) §4–5 |
| ADR-0003 | Desktop stack (Electron + React + Vite) | Critical | **Consolidated** — [TECH_STACK.md](TECH_STACK.md) §6 |
| ADR-0004 | Mobile stack (React Native Android) | Critical | **Consolidated** — [TECH_STACK.md](TECH_STACK.md) §7 |
| ADR-0005 | Authentication & security (JWT + bcrypt + HTTPS internal CA) | Critical | **Superseded by ADR-0010** |
| ADR-0006 | Windows deployment (services, firewall, backup) | High | **Consolidated** — §20, [DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md) |
| ADR-0007 | Tally integration mechanism | Critical | **Superseded by ADR-0011** |
| ADR-0008 | Excel sync schedule and file format | High | **Consolidated** — §14, [DATABASE_DESIGN.md](database/DATABASE_DESIGN.md) §10 |
| ADR-0009 | Search indexing strategy (pg_trgm) | High | **Consolidated** — [DATABASE_DESIGN.md](database/DATABASE_DESIGN.md), [TECH_STACK.md](TECH_STACK.md) |
| ADR-0010 | Authentication & Initialization | Critical | **Accepted** — [ADR-0010](../adr/ADR-0010-authentication-and-initialization.md) |
| ADR-0011 | Tally Integration Strategy | Critical | **Accepted** — [ADR-0011](../adr/ADR-0011-tally-integration-strategy.md) |
| ADR-0012 | Reverse proxy / TLS (future remote access) | Medium | **Reserved** — not authored |

See [adr/README.md](../adr/README.md) for the authoritative index.

### 23.3 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tally XML mapping failure | High | High | POC checklist §14.3.1; manual fallback |
| Internal CA distribution failure | Medium | Medium | Installer bundles CA; documented install steps |
| Electron memory on old PCs | Low | Medium | Min spec document; monitor |
| Excel file lock conflicts | Medium | Low | Atomic writes; retry; user guidance |
| Single server failure | Medium | High | UPS; verified backups; tested restore |
| FastAPI unstructured growth | Medium | Medium | Engineering conventions §22.5; code review |
| Android token in JS heap | Low | Low | HTTPS + short TTL; native module deferred §22.6 |

---

## 24. Architecture Readiness Assessment

### 24.1 Readiness Verdict

| Phase | Ready? | Conditions |
|-------|--------|------------|
| **Database schema design** | **Yes** | Proceed; resolve lifecycle default on add (Received vs Available) with business |
| **OpenAPI specification** | **Yes** | Derive from PRD + this architecture |
| **Backend implementation** | **Yes** | [ADR-0010](../adr/ADR-0010-authentication-and-initialization.md) Accepted; TECH_STACK Active; follow §22.5 conventions |
| **Desktop implementation** | **Conditional** | TECH_STACK §6; internal CA in installer; OpenAPI client generated |
| **Android implementation** | **Conditional** | TECH_STACK §7; network security config with CA |
| **Excel Sync implementation** | **Yes** | After SyncJob schema defined |
| **Tally Sync implementation** | **No — blocked** | Tally POC checklist §14.3.1 must pass |
| **Production deployment** | **No** | Full installation workflow §20.8; backup restore verified; security checklist |

**Overall:** Architecture is **frozen for Version 1**. Database design and core API implementation may begin immediately. Tally integration remains blocked on POC.

### 24.2 Remaining Open Decisions

| Item | Owner | Blocks |
|------|-------|--------|
| Tally XML POC (§14.3.1) | Engineering | Tally Sync service only |
| Default lifecycle on add: Received vs Available | Business + Product | Inventory create default |
| Configuration field structure (free text vs structured) | Product | **Resolved** — structured fields on `product_model` |
| Excel sync schedule default | Business | Scheduler config |
| Tally serial number field mapping | Business + Engineering | Tally integration spec |
| Numeric performance targets | Product + Engineering | SLA documentation |
| Salesperson movement permission | Product | **Resolved** — PRD §17.2; API RBAC |
| Internal CA tooling choice (step-ca vs OpenSSL vs AD CS) | Operations | Certificate install docs |

### 24.3 Recommended Next Artifacts

| Order | Artifact | Path |
|-------|----------|------|
| 1 | Tally integration POC report | `docs/research/` — gate for [ADR-0011](../adr/ADR-0011-tally-integration-strategy.md) |
| 2 | Database schema specification | `database/schema/` |
| 3 | OpenAPI v1 specification | `docs/api/openapi/` |
| 4 | Excel sync specification | `docs/integrations/excel/` |
| 5 | Backend platform guide | `docs/development/platform-guides/backend.md` |
| 6 | Security threat model | `docs/security/` — implements §16.14 |
| 7 | Deployment runbook | `docs/deployment/server/` |

### 24.4 Architecture Quality Checklist

- [x] All PRD mandatory requirements architecturally supported
- [x] Project Bible non-negotiable rules (N1–N18) respected
- [x] TECH_STACK approved technologies used (HTTPS refines transport per [ADR-0010](../adr/ADR-0010-authentication-and-initialization.md))
- [x] Business logic location defined (Backend service layer)
- [x] Integration boundaries isolated; API-only data access enforced
- [x] Security architecture and threat model documented
- [x] Failure modes and recovery defined
- [x] Deployment workflow and update strategy documented
- [x] Engineering conventions defined
- [x] Future enhancements explicitly deferred (§22.6)
- [x] ADR-0010 and ADR-0011 Accepted; ADR-0002–0009 consolidated per [adr/README.md](../adr/README.md)
- [ ] Tally POC completed
- [ ] Open product decisions resolved

---

## References

| Document | Path |
|----------|------|
| Project Bible | [docs/PROJECT_BIBLE.md](PROJECT_BIBLE.md) |
| Product Requirements | [docs/product/PRODUCT_REQUIREMENTS.md](product/PRODUCT_REQUIREMENTS.md) |
| Technology Stack | [docs/TECH_STACK.md](TECH_STACK.md) |
| ADR Index | [adr/README.md](../adr/README.md) |
| Architecture Domain Overviews | [docs/architecture/](architecture/README.md) |
| Integration Specs | [docs/integrations/](integrations/README.md) |
| Security Documentation | [docs/security/](security/README.md) |
| Deployment Documentation | [docs/deployment/](deployment/README.md) |

---

> **Document Authority:** This architecture is binding for WEBSTUDIO IMS implementation structure. Deviations require an ADR. Read alongside PROJECT_BIBLE.md, PRODUCT_REQUIREMENTS.md, and TECH_STACK.md before writing code or database schemas.

*WEBSTUDIO IMS Team — 2026*
