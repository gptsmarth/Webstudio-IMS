---
Title: WEBSTUDIO IMS — Technology Stack Decision Document
Version: 1.1
Status: Proposed
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/PROJECT_BIBLE.md, docs/product/PRODUCT_REQUIREMENTS.md, adr/README.md, docs/research/README.md
---

# WEBSTUDIO IMS — Technology Stack (TECH_STACK)

| Attribute | Value |
|-----------|-------|
| **Document ID** | TS-001 |
| **Version** | 1.1 |
| **Status** | Proposed — pending formal approval |
| **Governing Documents** | [PROJECT_BIBLE.md](PROJECT_BIBLE.md), [PRODUCT_REQUIREMENTS.md](product/PRODUCT_REQUIREMENTS.md) |
| **Purpose** | Freeze the official technology stack for architecture and implementation |

> **Authority:** This document is the authoritative source for approved technologies in WEBSTUDIO IMS. Implementation must not introduce frameworks, libraries, or runtimes not approved here without an ADR amendment.
>
> Technologies marked **Approved** may be used. Technologies marked **Conditional** require ADR or spec before use. Technologies marked **Rejected** must not be introduced.

---

## Version History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.1 | 2026-06-27 | WEBSTUDIO IMS Team | Windows Server revision. Production server changed to Windows 11 Pro; removed V1 reverse proxy requirement; added Windows Services, deployment philosophy, and Windows maintenance guidance. |
| 1.0 | 2026-06-27 | WEBSTUDIO IMS Team | Initial technology stack decision document. Critical review of candidate stack, security architecture, Electron vs Tauri evaluation, compatibility matrix, environments, risks, and approval checklist. |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Final Approved Technology Stack](#2-final-approved-technology-stack)
3. [Technology Review — Backend & Data](#3-technology-review--backend--data)
4. [Technology Review — Desktop](#4-technology-review--desktop)
5. [Technology Review — Mobile](#5-technology-review--mobile)
6. [Technology Review — Frontend Libraries](#6-technology-review--frontend-libraries)
7. [Technology Review — Integrations](#7-technology-review--integrations)
8. [Technology Review — Quality & Tooling](#8-technology-review--quality--tooling)
9. [Electron vs Tauri — Decision](#9-electron-vs-tauri--decision)
10. [Overall Stack Evaluation](#10-overall-stack-evaluation)
11. [Technology Compatibility Matrix](#11-technology-compatibility-matrix)
12. [Development Workflow](#12-development-workflow)
13. [Local Development Environment](#13-local-development-environment)
14. [Production Environment](#14-production-environment)
    - [14.1 Deployment Philosophy (Version 1)](#141-deployment-philosophy-version-1)
    - [14.2 Windows Dedicated Server](#142-windows-dedicated-server)
    - [14.3 Windows Services](#143-windows-services)
    - [14.4 Windows Maintenance](#144-windows-maintenance)
    - [14.5 Platform Flexibility (Future)](#145-platform-flexibility-future)
15. [Security Architecture](#15-security-architecture)
16. [Future Scalability](#16-future-scalability)
17. [Technology Risks](#17-technology-risks)
18. [Architecture Readiness](#18-architecture-readiness)
19. [Security Deployment Checklist](#19-security-deployment-checklist)
20. [Final Approval Checklist](#20-final-approval-checklist)
21. [References](#21-references)

---

## 1. Executive Summary

WEBSTUDIO IMS is an on-premise inventory management system for a laptop retail business. The stack must support:

- A **Backend API** as the sole gateway to PostgreSQL
- **Windows and macOS** desktop clients with premium SaaS-quality UX
- **Android** mobile access
- **Tally ERP 9** and **Excel** integrations
- **Search-first**, serial-number-tracked inventory
- **10+ year** maintainability by a small team with AI-assisted development

After critical review, the recommended stack is **internally consistent**, **appropriately conservative**, and **well-suited** to a one-developer team building commercial on-premise software for a **Windows-based retail environment**. The backend (Python/FastAPI/PostgreSQL) is a strong fit. The desktop choice is **Electron** over Tauri — not because Electron is newer, but because it maximizes developer productivity, AI assistance quality, and ecosystem maturity for a React/TypeScript UI while accepting higher memory use mitigated by security hardening.

**Production deployment:** Version 1 runs entirely on a **dedicated Windows 11 Pro server PC** within the office Wi-Fi network. No cloud deployment. No reverse proxy in V1 — FastAPI serves the API directly on the trusted LAN. The architecture remains cloud-ready for future expansion without redesign.

**Mobile:** **React Native (TypeScript)** is approved for Android, sharing language and patterns with the desktop frontend without pretending to share UI code.

**Key simplifications applied:**
- One backend language (Python) for API, integrations, and server jobs
- One frontend language (TypeScript) across desktop and mobile
- OpenAPI as the contract between all clients and backend
- No additional ORM, no second HTTP client library beyond Axios where needed
- Structured logging in production (JSON) — Loguru approved with production configuration requirements

**Not ready until:** ADRs recorded, exact version pins defined, Tally integration mechanism validated, and security checklist signed off.

---

## 2. Final Approved Technology Stack

### 2.1 Summary Table

| Layer | Technology | Status | Version Target |
|-------|------------|--------|----------------|
| **Backend language** | Python | **Approved** | 3.12.x |
| **Backend framework** | FastAPI | **Approved** | Latest stable |
| **ASGI server** | Uvicorn | **Approved** | Latest stable |
| **Database** | PostgreSQL | **Approved** | 16.x LTS |
| **ORM** | SQLAlchemy 2.x | **Approved** | 2.x |
| **Migrations** | Alembic | **Approved** | Latest stable |
| **Desktop shell** | Electron | **Approved** | Latest stable LTS |
| **Desktop UI** | React + TypeScript | **Approved** | React 18+, TS 5.x |
| **Desktop build** | Vite | **Approved** | 5.x |
| **Desktop packaging** | Electron Builder | **Approved** | Latest stable |
| **Mobile** | React Native + TypeScript | **Approved** | Latest stable |
| **Styling** | Tailwind CSS | **Approved** | 3.x |
| **UI components** | shadcn/ui | **Approved** | Pin at adoption |
| **State management** | Zustand | **Approved** | Latest stable |
| **Forms** | React Hook Form | **Approved** | Latest stable |
| **Validation (client)** | Zod | **Approved** | Latest stable |
| **Validation (API)** | Pydantic (FastAPI native) | **Approved** | Bundled with FastAPI |
| **HTTP client** | Axios | **Approved** | Latest stable |
| **Auth — tokens** | JWT (access + refresh) | **Approved** | — |
| **Auth — passwords** | bcrypt | **Approved** | Cost factor ≥ 12 |
| **Excel** | openpyxl | **Approved** | Latest stable |
| **Tally** | XML over HTTP (Tally API) | **Conditional** | Pending integration validation |
| **Logging (dev)** | Loguru | **Approved** | Latest stable |
| **Logging (prod)** | Loguru → JSON structured stdout | **Approved** | Required configuration |
| **API documentation** | OpenAPI 3.1 / Swagger UI | **Approved** | FastAPI native |
| **Backend testing** | pytest | **Approved** | Latest stable |
| **E2E testing** | Playwright | **Approved** | Latest stable |
| **Version control** | Git | **Approved** | — |
| **Monorepo package manager** | pnpm | **Approved** | 9.x |
| **Python package manager** | uv or pip + venv | **Approved** | Team choice at init |
| **Production server OS** | Windows 11 Pro | **Approved** | Dedicated Server PC — V1 official platform |
| **Process manager (prod)** | Windows Services (NSSM or equivalent) | **Approved** | Auto-start on boot |
| **Reverse proxy (prod)** | None (V1) | **Not required V1** | Caddy/nginx **Future** — remote access / TLS termination |

### 2.2 Explicitly Rejected for Version 1

| Technology | Reason |
|------------|--------|
| **Tauri** (desktop) | See [Section 9](#9-electron-vs-tauri--decision) — rejected for V1; revisit if memory becomes blocking |
| **Django** | Heavier than needed; FastAPI + explicit structure fits API-first design |
| **MongoDB / SQLite as primary store** | Violates PROJECT_BIBLE — PostgreSQL only |
| **Direct client DB access** | Violates PROJECT_BIBLE — Backend API only |
| **Kotlin-native Android (V1)** | Rejected for V1 to preserve TypeScript velocity; revisit if React Native limits emerge |
| **Redux** | Unnecessary complexity vs Zustand for this application scope |
| **Prisma** | Python backend — SQLAlchemy is the correct ORM choice |
| **GraphQL** | REST/OpenAPI sufficient; adds complexity without PRD requirement |

### 2.3 Conditional / Pending Validation

| Technology | Condition |
|------------|-----------|
| **Tally XML/SOAP** | Approved pattern pending proof-of-concept against live Tally ERP 9 instance |
| **Redis** | Not required V1; approve via ADR if caching/queue needed |
| **Celery** | Not required V1; background jobs via APScheduler or FastAPI BackgroundTasks initially |
| **Caddy / nginx** | Not required V1; approve via ADR when remote access or TLS termination needed |
| **Sentry / APM** | Recommended post-V1; optional for V1 with structured logs |

---

## 3. Technology Review — Backend & Data

### 3.1 Python

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Backend API, integration services, sync jobs, business logic |
| **Why selected** | Mature ecosystem for APIs and data processing; excellent AI-assisted development corpus; readable for long-term maintenance; strong PostgreSQL libraries |
| **Advantages** | Fast iteration; Pydantic validation; vast hiring and documentation base; works well for XML/Excel integrations |
| **Disadvantages** | Runtime performance below compiled languages (irrelevant at retail scale); GIL limits CPU parallelism (mitigated by async I/O) |
| **Alternatives** | **Node.js/NestJS** — viable but splits backend from integration scripting culture; **Go** — excellent performance but slower AI-assisted productivity for small team; **C#/.NET** — strong on Windows but adds friction for Tally/Excel scripting |
| **Recommendation** | **Approved** |

### 3.2 FastAPI

| Aspect | Assessment |
|--------|------------|
| **Purpose** | REST API framework; OpenAPI generation; request validation; dependency injection |
| **Why selected** | Native OpenAPI aligns with PRD traceability; Pydantic models enforce contracts; async support; automatic Swagger UI for development |
| **Advantages** | Type hints; performance adequate for on-premise retail; enforces Backend API as authority |
| **Disadvantages** | Less opinionated than Django — requires discipline for project structure |
| **Alternatives** | **Django REST Framework** — heavier; **Flask** — lacks native OpenAPI and validation ergonomics |
| **Recommendation** | **Approved** — project structure must be defined in SYSTEM_ARCHITECTURE.md |

### 3.3 Uvicorn

| Aspect | Assessment |
|--------|------------|
| **Purpose** | ASGI server hosting FastAPI |
| **Why selected** | Standard FastAPI deployment server; supports HTTP/2 with appropriate workers |
| **Advantages** | Simple; well-documented; runs natively on Windows |
| **Disadvantages** | Single-process dev; production may use multiple Uvicorn instances or workers per service |
| **Alternatives** | **Hypercorn** — viable; **Gunicorn** — not available on Windows (Linux only) |
| **Recommendation** | **Approved** — production on Windows: Uvicorn bound to LAN interface; one instance per Windows Service where isolation is needed |

### 3.4 PostgreSQL

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Authoritative datastore for all inventory, users, audit, and configuration |
| **Why selected** | Mandated by PROJECT_BIBLE; ACID compliance; JSON support for flexible fields; excellent search (full-text, trigram for configuration search per PRD FR-SRH-05/06) |
| **Advantages** | 10+ year track record; robust backup tooling; enforces serial uniqueness at DB level |
| **Disadvantages** | Requires dedicated server administration |
| **Alternatives** | None permitted as primary store |
| **Recommendation** | **Approved** — use PostgreSQL 16.x; enable `pg_trgm` for configuration search |

### 3.5 SQLAlchemy 2.x

| Aspect | Assessment |
|--------|------------|
| **Purpose** | ORM and query builder; database abstraction |
| **Why selected** | Python standard for PostgreSQL; mature; supports migrations via Alembic; 2.x style is modern and explicit |
| **Advantages** | Fine-grained control; works with Alembic; AI tooling well-trained |
| **Disadvantages** | Learning curve; raw SQL sometimes needed for complex search |
| **Alternatives** | **SQLModel** — thinner but less flexible; **Raw SQL only** — unmaintainable at scale |
| **Recommendation** | **Approved** — use 2.x declarative style consistently |

### 3.6 Alembic

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Database schema migrations |
| **Why selected** | De facto standard with SQLAlchemy; immutable migration files per PROJECT_BIBLE |
| **Advantages** | Versioned migrations; rollback support |
| **Disadvantages** | Manual merge discipline required in team workflows |
| **Alternatives** | None worth switching |
| **Recommendation** | **Approved** |

---

## 4. Technology Review — Desktop

### 4.1 Electron

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Cross-platform desktop shell for Windows and macOS retail clients |
| **Why selected** | See [Section 9](#9-electron-vs-tauri--decision) |
| **Advantages** | Full React/TypeScript/Vite/shadcn stack; largest ecosystem; best AI training data; proven in retail/enterprise internal tools |
| **Disadvantages** | Memory footprint; security requires explicit hardening; Chromium bundle size |
| **Alternatives** | **Tauri** — rejected V1; **WPF/WinUI + SwiftUI** — two codebases |
| **Recommendation** | **Approved** with mandatory security configuration (Section 15.5) |

### 4.2 React + TypeScript + Vite

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Desktop UI implementation |
| **Why selected** | Industry standard; shadcn/ui compatibility; fast HMR via Vite; TypeScript catches errors across large UI |
| **Advantages** | Shared skill with React Native patterns; excellent component ecosystem |
| **Disadvantages** | Bundle size; requires discipline to avoid unnecessary dependencies |
| **Alternatives** | **Vue/Svelte** — would break shadcn/ui alignment |
| **Recommendation** | **Approved** |

### 4.3 Electron Builder

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Package and distribute Windows (.exe/.msi) and macOS (.dmg) installers |
| **Why selected** | Standard Electron packaging; supports auto-update (future) |
| **Advantages** | Integrated with Electron ecosystem |
| **Disadvantages** | Code signing configuration complexity on macOS/Windows |
| **Alternatives** | **electron-forge** — viable equivalent |
| **Recommendation** | **Approved** |

---

## 5. Technology Review — Mobile

### 5.1 React Native (TypeScript)

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Android mobile client for floor search, movement, and sale verification |
| **Why selected** | TypeScript parity with desktop team skills; adequate for API-driven CRUD + search app; faster delivery for small team |
| **Advantages** | One language across clients; large ecosystem; AI assistance strong |
| **Disadvantages** | Does not share UI code with Electron; bridge performance irrelevant for this API-bound app; Android-only still requires RN Android toolchain |
| **Alternatives** | **Kotlin (Jetpack Compose)** — better native Android fidelity and long-term Google alignment; higher separate codebase cost; **Flutter** — third UI paradigm, rejected |
| **Recommendation** | **Approved for Android V1** — document Kotlin migration path in roadmap if React Native blocks native requirements |

> **Note:** PRD requires Android only. iOS is out of scope. Do not add React Native iOS dependencies in V1.

---

## 6. Technology Review — Frontend Libraries

### 6.1 Tailwind CSS

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Utility-first styling for rapid, consistent UI |
| **Why selected** | Pairs with shadcn/ui; supports Light/Dark themes (PRD mandatory); fast iteration |
| **Recommendation** | **Approved** |

### 6.2 shadcn/ui

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Accessible, customizable component primitives (tables, dialogs, forms, command palette for search) |
| **Why selected** | Premium SaaS aesthetic without heavy component lock-in; copies into codebase — 10-year maintainability |
| **Disadvantages** | Manual updates when upstream changes |
| **Alternatives** | **MUI** — heavier; **Ant Design** — opinionated look |
| **Recommendation** | **Approved** |

### 6.3 Zustand

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Lightweight client state (auth session, UI preferences, cached lists) |
| **Why selected** | Minimal boilerplate; sufficient for PRD scope |
| **Alternatives** | **Redux Toolkit** — overkill |
| **Recommendation** | **Approved** |

### 6.4 React Hook Form + Zod

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Form state and client-side validation |
| **Why selected** | Performance on inventory forms; Zod schemas align conceptually with API contracts |
| **Note** | Server validation is authoritative via Pydantic — client validation is UX only |
| **Recommendation** | **Approved** |

### 6.5 Axios

| Aspect | Assessment |
|--------|------------|
| **Purpose** | HTTP client for Backend API calls |
| **Why selected** | Interceptors for JWT refresh; mature error handling |
| **Alternatives** | **Native fetch** — viable; Axios justified for interceptor patterns |
| **Recommendation** | **Approved** — generate typed client from OpenAPI in `packages/api-client/` |

---

## 7. Technology Review — Integrations

### 7.1 openpyxl (Excel)

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Generate synchronized Excel export from PostgreSQL inventory state |
| **Why selected** | Pure Python; no Excel installation required on server; adequate for export/sync |
| **Disadvantages** | File locking must be handled in application layer |
| **Alternatives** | **xlsxwriter** — write-only; sufficient for export-only direction |
| **Recommendation** | **Approved** — read-back from Excel not authoritative |

### 7.2 Tally ERP 9 — XML over HTTP

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Receive billing events; reflect sales in inventory |
| **Why selected** | Tally exposes XML request/response API on local network |
| **Disadvantages** | Tally version variance; serial mapping **TBD** (PRD risk BRK-02) |
| **Alternatives** | **ODBC** — fragile; **Manual CSV** — unacceptable |
| **Recommendation** | **Conditional Approved** — POC required before architecture freeze |

---

## 8. Technology Review — Quality & Tooling

### 8.1 pytest

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Backend unit and integration tests |
| **Recommendation** | **Approved** — focus on business rules per PRD |

### 8.2 Playwright

| Aspect | Assessment |
|--------|------------|
| **Purpose** | E2E tests for desktop (Electron) and critical API flows |
| **Recommendation** | **Approved** |

### 8.3 Loguru

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Application logging |
| **Why selected** | Developer-friendly; structured JSON output configurable |
| **Production requirement** | JSON to stdout; correlation IDs on integration events |
| **Recommendation** | **Approved** |

### 8.4 OpenAPI / Swagger

| Aspect | Assessment |
|--------|------------|
| **Purpose** | API contract documentation and client generation |
| **Recommendation** | **Approved** |

### 8.5 Git

| Aspect | Assessment |
|--------|------------|
| **Purpose** | Version control |
| **Recommendation** | **Approved** |

---

## 9. Electron vs Tauri — Decision

### 9.1 Comparison Matrix

| Criterion | Electron | Tauri 2.x | Weight for WEBSTUDIO IMS |
|-----------|----------|-----------|--------------------------|
| **Security** | Good when hardened (contextIsolation, no nodeIntegration); larger attack surface (Chromium) | Stronger default sandbox; smaller native surface; Rust backend | High — mitigated by discipline on Electron |
| **Performance** | Adequate for form/search UI; heavier cold start | Faster startup; lower idle memory | Medium — retail PCs are capable |
| **Memory usage** | 150–300+ MB baseline | ~30–80 MB baseline | Medium — not blocking on store hardware |
| **Development complexity** | Low — pure web stack | Medium — Rust + web + IPC | **Critical** for 1-dev team |
| **macOS support** | Excellent | Good (improved in v2) | Required |
| **Windows support** | Excellent | Good | Required |
| **AI-assisted development** | Excellent corpus | Growing but thinner | **Critical** |
| **Community / ecosystem** | Massive | Growing | High for 10-year maintainability |
| **shadcn/ui + Tailwind** | Native fit | Works in webview | Required |
| **Long-term maintainability** | Proven 10+ years (VS Code, Slack, etc.) | Newer; less retail IMS precedent | High |

### 9.2 Decision

**Recommendation: Electron for Version 1.**

**Reasoning:**

1. **Team reality:** A single developer with AI assistance will ship faster on Electron. The PRD prioritizes minimal training, search-first UX, and rapid iteration — not minimal RAM usage.
2. **Stack coherence:** Approved UI stack (React, TypeScript, Vite, shadcn/ui, Tailwind) is Electron-native. Tauri introduces Rust for desktop shell concerns the team does not otherwise use.
3. **Security is manageable:** Electron's security model is adequate when `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, and IPC is strictly typed. A trusted retail LAN deployment does not eliminate the need for hardening — but it does not require Tauri by default. TLS becomes mandatory when remote or internet access is added.
4. **Memory is acceptable:** Shop floor machines handling laptop sales have sufficient RAM for Electron. Monitor in production; revisit if problematic.
5. **Tauri remains a future option:** If V2 requires materially smaller footprint or security audit demands smaller surface, migrate via ADR — API-first architecture makes UI shell replaceable.

**Tauri rejected for V1 — not because it is inferior, but because it is the wrong tradeoff for this team, timeline, and product.**

---

## 10. Overall Stack Evaluation

### 10.1 Is it internally consistent?

**Yes.** Python owns all server-side logic. TypeScript owns all client UI. PostgreSQL owns all persistent state. OpenAPI connects layers. Integrations are isolated packages.

### 10.2 Unnecessary technologies?

| Item | Verdict |
|------|---------|
| Zustand + RHF + Zod | Justified — different concerns |
| Axios + generated OpenAPI client | Minor overlap — generate client wrapping Axios in `packages/api-client/` |
| Loguru only | Sufficient V1 if JSON production config enforced |

**No major fat to cut.**

### 10.3 Can anything be simplified?

- **Unified TypeScript monorepo** for `apps/desktop`, `apps/mobile`, `packages/ui-components` via pnpm workspaces
- **Single OpenAPI spec** generates types for desktop and mobile
- **Defer Redis/Celery** — use PostgreSQL + in-process scheduling until proven insufficient

### 10.4 Duplication concerns?

| Duplication | Mitigation |
|-------------|------------|
| Desktop vs mobile UI | Acceptable — shared `packages/api-client`, `packages/shared-kernel` types |
| Validation Zod vs Pydantic | Acceptable — server is authoritative; duplicate schemas documented |
| Windows vs macOS Electron | Single codebase — platform-specific packaging only |

### 10.5 Suitable for one developer + AI?

**Yes.** Python and React/TypeScript are the highest-signal languages for AI coding tools. OpenAPI enables spec-first development. Monorepo keeps context in one repository.

### 10.6 Maintainable for 10+ years?

**Yes, with conditions:** pin dependencies; record ADRs; avoid experimental libraries; prefer shadcn (owned code) over opaque UI kits; PostgreSQL and Python have decade-scale stability.

---

## 11. Technology Compatibility Matrix

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
├──────────────────────┬──────────────────────┬───────────────────┤
│  Electron (Win/Mac)  │  React Native (Android) │  (No iOS V1)   │
│  React + TS + Vite   │  TypeScript          │                   │
│  Tailwind + shadcn   │  NativeWind or equiv │                   │
│  Zustand + RHF + Zod │  Zustand + RHF + Zod │                   │
│  Axios → API         │  Axios → API         │                   │
└──────────┬───────────┴──────────┬───────────┴───────────────────┘
           │                      │
           │   HTTP + JWT (V1 LAN) │
           ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│           WINDOWS 11 PRO — DEDICATED SERVER PC (V1)            │
│  FastAPI + Uvicorn (direct, no reverse proxy in V1)             │
│  Windows Services: API · Excel Sync · Tally Sync                │
│  SQLAlchemy 2.x · Alembic · Loguru (JSON)                       │
├──────────┬──────────────────────────────┬───────────────────────┤
│          │                              │                       │
▼          ▼                              ▼                       │
┌──────────────────────┐    ┌────────────────────────────────────┐
│     PostgreSQL 16    │    │         INTEGRATIONS               │
│  (sole datastore)    │    │  openpyxl → Excel file (export)    │
│  app user (least priv)│    │  HTTP/XML → Tally ERP 9 (LAN)     │
└──────────────────────┘    └────────────────────────────────────┘

DEPLOYMENT TARGETS:
  Dev:      macOS or Windows → local PostgreSQL → local FastAPI
  Server:   Windows 11 Pro → PostgreSQL + FastAPI + Windows Services
  Desktop:  Electron Builder → .msi (Win) / .dmg (macOS)
  Mobile:   Gradle → .apk (Android)

FUTURE (not V1): Reverse proxy (Caddy/nginx) · TLS termination · cloud hosting
```

### 11.1 Interaction Rules

| From | To | Protocol | Notes |
|------|-----|----------|-------|
| Desktop | Backend API | HTTP + JSON + JWT (V1 LAN) | Never PostgreSQL direct; HTTPS **Future** when remote access |
| Android | Backend API | HTTP + JSON + JWT (V1 LAN) | Never PostgreSQL direct; HTTPS **Future** when remote access |
| Backend | PostgreSQL | TCP (localhost/LAN) | Dedicated app user |
| Backend | Excel file | Filesystem (openpyxl) | Export only; file permissions locked |
| Backend | Tally | HTTP XML (LAN) | Read billing; no write to Tally from IMS |
| Integration jobs | Backend API | Internal Python calls | Same process V1; separate worker if scaled |

---

## 12. Development Workflow

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. DEVELOP (macOS primary — Windows secondary)                    │
│    Cursor IDE · local PostgreSQL · FastAPI dev server             │
│    Vite dev server for Electron · React Native Metro for Android  │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. VERSION CONTROL (Git)                                          │
│    Feature branches · Conventional Commits · PR review              │
│    Reference PRD IDs + ADR IDs in commits                           │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. CI (GitHub Actions — when configured)                          │
│    pytest · lint · typecheck · Playwright smoke · OpenAPI diff    │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. SERVER DEPLOY (Windows 11 Pro Dedicated Server PC)             │
│    Alembic migrate · Windows Services restart · firewall verify    │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. DESKTOP PACKAGE                                                │
│    electron-builder → Windows installer + macOS dmg               │
│    Distribute via LAN share or USB — auto-update Future           │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 6. ANDROID BUILD                                                  │
│    Gradle release APK → sideload or internal distribution         │
└──────────────────────────────────────────────────────────────────┘
```

**Platform note:** Primary development on **macOS** is recommended (Unix tooling, iOS-not-needed, good Electron/RN support). Windows VM or hardware required for Windows installer testing.

---

## 13. Local Development Environment

| Tool | Recommendation |
|------|----------------|
| **Development OS** | macOS (primary) + Windows machine/VM for testing |
| **IDE** | Cursor (AI-assisted) with Python, ESLint, Prettier, Ruff |
| **Python** | 3.12.x via pyenv or official installer |
| **Node.js** | 20.x LTS via fnm or nvm |
| **Package managers** | `uv` or `pip` + `venv` (Python); `pnpm` 9.x (JavaScript monorepo) |
| **Database** | PostgreSQL 16 local instance (Postgres.app on macOS or Docker) |
| **DB tools** | pgAdmin 4 or DBeaver (dev only — not production pattern) |
| **API testing** | Bruno or Hoppscotch (git-friendly collections); Swagger UI from FastAPI |
| **Git** | Git 2.x + GitHub |
| **Android** | Android Studio (SDK, emulator, Gradle) |
| **Container (optional)** | Docker Compose for PostgreSQL + API — `infra/docker/` when created |

---

## 14. Production Environment

### 14.1 Deployment Philosophy (Version 1)

WEBSTUDIO IMS Version 1 is an **on-premise application operating entirely within the office Wi-Fi network**.

| Principle | Version 1 |
|-----------|-----------|
| **Deployment model** | On-premise only — dedicated server on store LAN |
| **Cloud deployment** | **Not planned** for Version 1 |
| **Internet exposure** | **None** — API bound to LAN; not reachable from public internet |
| **Reverse proxy** | **Not required** — FastAPI serves API directly |
| **TLS termination** | **Future** — when remote or internet access is required |
| **Cloud-ready architecture** | **Yes** — backend is cross-platform Python; clients use OpenAPI contract; no redesign required to add cloud hosting later |

The business operates in a **Windows-based retail environment**. All store systems — desktops, server, and Tally — run on Windows. The production server is a **dedicated Windows PC**, not a general-purpose workstation.

### 14.2 Windows Dedicated Server

| Component | Recommendation |
|-----------|----------------|
| **Server OS** | **Windows 11 Pro** (Dedicated Server PC) |
| **Server role** | Hosts WEBSTUDIO IMS backend only — **not used as a normal workstation** |
| **Hosted services** | PostgreSQL 16 · FastAPI Backend API · Excel Synchronization Service · Tally Integration Service · Windows Service(s) for process management |
| **Runtime** | Python 3.12 venv; Uvicorn serving FastAPI |
| **Database** | PostgreSQL 16 installed natively on same server (V1 scale) |
| **API binding** | FastAPI/Uvicorn listens on LAN interface (e.g., `0.0.0.0:8000`) — **no reverse proxy in V1** |
| **Network** | Office Wi-Fi LAN only; static local IP recommended |
| **Excel output path** | Dedicated directory with restricted NTFS permissions |
| **Logging** | JSON logs to file + Windows Event Log **optional** |
| **Monitoring** | Health check endpoint; disk space alert; sync failure alert — full APM **Future** |

**Why Windows 11 Pro:** The business is entirely Windows-based. A Windows server simplifies administration for a non-Linux IT environment, aligns with Tally ERP 9 (Windows-native), and allows consistent tooling across store desktops and server. PostgreSQL and Python run reliably on Windows 11 Pro for the expected retail workload.

### 14.3 Windows Services

The following backend components **must run as Windows Services** (or an equivalent Windows service manager such as **NSSM** — Non-Sucking Service Manager) and **start automatically when the server boots**:

| Service | Responsibility | Auto-start |
|---------|----------------|------------|
| **WEBSTUDIO API** | FastAPI + Uvicorn — Backend API, JWT auth, RBAC, all inventory business logic | **Required** |
| **WEBSTUDIO Excel Sync** | Scheduled and on-demand Excel export/sync via openpyxl | **Required** |
| **WEBSTUDIO Tally Sync** | Poll/receive Tally billing events; call Backend API to update inventory | **Required** |
| **PostgreSQL** | Database engine | **Required** — PostgreSQL Windows service |

**Service requirements:**

- Services recover automatically on failure (Windows Service recovery policy)
- Services run under dedicated Windows service accounts — not interactive user sessions
- Service accounts use least-privilege NTFS permissions on data directories
- Deployment scripts document install, start, stop, and restart procedures in `docs/deployment/server/`

**Alternative:** Python `pywin32` Windows Service wrapper — acceptable if NSSM is not used; behavior must be equivalent (auto-start, recovery, logging).

### 14.4 Windows Maintenance

Operational guidance for the dedicated Windows server:

| Topic | Recommendation |
|-------|----------------|
| **Automatic startup after reboot** | All WEBSTUDIO and PostgreSQL services set to **Automatic (Delayed Start)**; verify after every Windows Update reboot |
| **Backup location** | Dedicated local drive or NAS path on LAN — e.g., `D:\WEBSTUDIO-IMS\backups\` for `pg_dump` files, Excel archive copies, and configuration exports; **off-server copy recommended** |
| **Windows Update** | Schedule updates outside business hours; test service recovery after reboot; defer feature updates during peak retail periods |
| **Firewall configuration** | Windows Defender Firewall — allow API port (e.g., 8000) **inbound from store Wi-Fi subnet only**; block inbound from internet; allow PostgreSQL localhost only |
| **Antivirus exclusions** | Add PostgreSQL data directory (e.g., `C:\Program Files\PostgreSQL\16\data\` or custom path) and WEBSTUDIO log directories to Windows Defender exclusions if real-time scanning causes database latency — **document exact paths after install** |
| **Recovery after power failure** | UPS (uninterruptible power supply) **strongly recommended**; BIOS set to auto-power-on after AC restore; verify all services start after unplanned shutdown |
| **Disk space** | Monitor PostgreSQL and backup volumes; alert below 20% free |
| **Interactive use** | **Prohibited** on dedicated server — no browsing, no store software; reduces attack surface and reboot disruption |

### 14.5 Platform Flexibility (Future)

| Platform | Status |
|----------|--------|
| **Windows 11 Pro server** | **Officially supported** deployment platform for Version 1 |
| **Linux server (Ubuntu LTS)** | **Technically possible** — Python, FastAPI, PostgreSQL, and Uvicorn are cross-platform; would use systemd instead of Windows Services |
| **Cloud hosting** | **Future** — same backend codebase; add reverse proxy, TLS, and ADR before deployment |

Linux deployment is **not rejected** as a technical option. It is **not the official V1 platform** because the business environment is Windows-based and operational support is simpler on a homogeneous Windows stack. A future ADR may approve Linux or cloud hosting without changing application code — only deployment packaging changes.

---

## 15. Security Architecture

Security is a **first-class design goal**. All enforcement occurs in the **Backend API** per PROJECT_BIBLE and PRD.

### 15.1 Authentication

| Control | Recommendation |
|---------|----------------|
| **Password hashing** | **bcrypt** with cost factor **12** minimum (approved); evaluate **argon2id** via ADR for V1.1 |
| **Password policy** | Minimum 10 characters; complexity rules **TBD** with business; disallow common passwords |
| **JWT strategy** | Short-lived **access token** (15 minutes default) + **refresh token** (7 days, rotatable) |
| **Access token storage (desktop)** | In-memory primary; refresh token in OS keychain via `keytar` / `safeStorage` — never `localStorage` plain text |
| **Access token storage (Android)** | Android Keystore / EncryptedSharedPreferences |
| **Session timeout** | Configurable idle timeout (PRD FR-AUTH-03) — default 30 minutes |
| **Refresh tokens** | **Approved** — stored httpOnly-style equivalent on clients; revocable server-side |
| **Secure login flow** | HTTP on trusted office LAN (V1); HTTPS mandatory when remote access is enabled; generic error messages; no user enumeration |
| **Account lockout** | Lock after 5 failed attempts (configurable); 15-minute lockout; Main Admin unlock |
| **First-time password change** | Force change on first login for new accounts |
| **Password reset** | Main Admin reset only V1; self-service **Future** |

### 15.2 Authorization (RBAC)

| Control | Recommendation |
|---------|----------------|
| **Model** | Role-Based Access Control enforced in FastAPI dependencies |
| **V1 roles** | Main Admin, Admin, Salesperson — per PRD Section 17 |
| **Extensibility** | Permissions as enum/constants in `packages/auth/` — roles map to permission sets; new roles add mapping without schema redesign |
| **Enforcement** | **Backend API only** — desktop and Android are display layers |
| **Permission checks** | Every endpoint declares required permissions; unit tests per role |

### 15.3 API Security

| Control | Recommendation |
|---------|----------------|
| **Transport (V1)** | HTTP on trusted office LAN — API not internet-exposed; JWT auth still required |
| **HTTPS / TLS** | **Future** — mandatory when remote or internet access is enabled; terminate at reverse proxy (Caddy/nginx) via ADR |
| **JWT validation** | Validate signature, expiry, issuer, audience on every request |
| **Token expiration** | Short access token; refresh rotation with reuse detection |
| **Request validation** | Pydantic models on all inputs |
| **Rate limiting** | `slowapi` — login endpoint: 10/min/IP; API: 100/min/user **TBD** |
| **API versioning** | URL prefix `/api/v1/` |
| **CORS** | Restrict to known desktop origins in dev; production LAN clients use explicit allowlist |
| **CSRF** | Not applicable to Bearer JWT API; relevant only if cookie auth added — **do not use cookie auth for API** |
| **Input sanitization** | Pydantic + parameterized SQLAlchemy queries only — no raw SQL string concatenation |

### 15.4 Database Security

| Control | Recommendation |
|---------|----------------|
| **Least privilege** | Dedicated `webstudio_app` PostgreSQL user — SELECT/INSERT/UPDATE/DELETE on app schema only |
| **Superuser** | **Never** used by application |
| **Backups** | Encrypted at rest; tested restore monthly |
| **Encryption at rest** | OS-level disk encryption on server; PostgreSQL TDE **Future** |
| **Encryption in transit** | V1: API clients over HTTP on trusted LAN; PostgreSQL via localhost socket (no network exposure); **Future:** TLS for API and `hostssl` when remote access enabled |
| **SQL injection** | SQLAlchemy parameterized queries exclusively |
| **Connection pooling** | SQLAlchemy pool with bounded size; connection timeout |
| **Transactions** | All inventory mutations in transactions with audit insert |

### 15.5 Desktop Security (Electron)

| Control | Recommendation |
|---------|----------------|
| **contextIsolation** | `true` — mandatory |
| **nodeIntegration** | `false` in renderer — mandatory |
| **sandbox** | `true` for renderer processes |
| **IPC** | Whitelist channels only; validate all IPC payloads |
| **Remote module** | Disabled |
| **webSecurity** | `true` |
| **Token storage** | OS keychain via `safeStorage` / `keytar` |
| **Auto-update** | Future — when enabled, code signing mandatory on Win/Mac |
| **CSP** | Content Security Policy restricting script sources |
| **Navigation** | `window.open` and external URL handling blocked or allowlisted |

**Electron risk acceptance:** Approved with above controls documented in ADR and verified in security review checklist.

### 15.6 Android Security

| Control | Recommendation |
|---------|----------------|
| **Token storage** | Android Keystore-backed encrypted storage |
| **Certificate pinning** | **Recommended** for production LAN server cert — optional V1, mandatory before internet exposure |
| **Offline cache** | If implemented, encrypt with device-specific keys; minimal cache V1 |
| **Root detection** | Optional warning — do not block V1 |
| **Integrity** | Play Integrity **Future** (sideload distribution V1) |

### 15.7 Excel Synchronization Security

| Control | Recommendation |
|---------|----------------|
| **File permissions** | OS-level ACL — only sync service user writes |
| **File locking** | Exclusive lock during write; retry on conflict |
| **Concurrent access** | Warn if Excel file open by user during sync; log and skip or queue |
| **Corruption recovery** | Write to temp file then atomic rename; keep last known good copy |
| **Unauthorized modification** | Excel is derived — never imported as authority; file hash logged |

### 15.8 Tally Integration Security

| Control | Recommendation |
|---------|----------------|
| **Network** | Tally port accessible only from server IP on LAN firewall |
| **XML validation** | Parse with defusedxml; reject unexpected payloads |
| **Trust boundary** | Tally is external input — validate all voucher data before API call |
| **Replay** | Idempotent sale processing by voucher number + serial |
| **Error handling** | Log failures; never partially apply sale state |

### 15.9 Network Security

| Control | Recommendation |
|---------|----------------|
| **V1 assumption** | Store Wi-Fi LAN; not internet-exposed; dedicated Windows server |
| **Firewall** | Windows Defender Firewall — allow API port (e.g., 8000) from store subnet only; block inbound from internet |
| **Wi-Fi** | WPA2/WPA3 required; segregate guest network from inventory VLAN **recommended** |
| **Future internet** | VPN or Zero Trust required before cloud exposure — ADR mandatory |

### 15.10 Audit & Monitoring

| Event | Logged |
|-------|--------|
| Login success/failure | Yes — FR-AUTH, PRD audit |
| Permission denied | Yes |
| User management changes | Yes |
| Inventory create/update/move/sale | Yes — PRD FR-AUD |
| Settings changes | Yes |
| Integration sync results | Yes |
| Correlation ID | All requests — `X-Request-ID` |

### 15.11 Backup & Disaster Recovery

| Asset | Strategy |
|-------|----------|
| **PostgreSQL** | Daily `pg_dump` + WAL archiving **recommended**; RPO/RTO per PRD **TBD** |
| **Excel file** | Copy before overwrite; versioned backup directory |
| **Configuration** | `config/env/` templates in Git; secrets outside Git |
| **Recovery** | Documented runbook in `docs/deployment/`; tested before go-live |

### 15.12 Secrets Management

| Secret | Storage |
|--------|---------|
| JWT signing key | Environment variable / `.env` on server — never in Git |
| Database password | Environment variable — `webstudio_app` user |
| Tally connection config | Environment variable |
| Encryption keys (if used) | Environment variable or OS secret store |
| Development | `.env.example` only in Git; local `.env` gitignored |

**Hardcoded secrets: forbidden** — CI secret scanning when configured.

### 15.13 Security Verdict

**The proposed stack is secure enough for production when the controls in this section are implemented and verified.** Electron is acceptable with hardening. The highest risks are operational (LAN trust, Tally mapping, Excel file conflicts) — not framework choice.

**Required before go-live:** Windows Services auto-start verified after reboot, bcrypt passwords, JWT refresh rotation, RBAC tests, Electron security config review, PostgreSQL least-privilege user, firewall restricted to store LAN, backup restore test.

**Required before remote/internet access:** TLS termination (reverse proxy ADR), VPN or Zero Trust, certificate pinning review on Android.

---

## 16. Future Scalability

| Dimension | Stack Support | Notes |
|-----------|---------------|-------|
| **Multiple stores (same building)** | ✓ | Location model in PRD; no stack change |
| **Multiple branches** | ✓ | PostgreSQL + API scale vertically; read replicas **Future** |
| **Cloud deployment** | ✓ | Same backend codebase; add reverse proxy, TLS, and ADR — **not planned V1** |
| **More inventory categories** | ✓ | Schema extension; backend rules pattern unchanged |
| **Additional integrations** | ✓ | `packages/integrations/` pattern |
| **Larger user base** | ✓ | Multiple Uvicorn workers or service instances; connection pooling; Redis cache **Future** |
| **10x inventory volume** | ✓ | PostgreSQL + trigram indexes; pagination on all lists |

**Bottleneck prediction:** Search performance and Tally sync latency — address with PostgreSQL indexing and async workers, not framework replacement.

---

## 17. Technology Risks

| Technology | Risk | Likelihood | Impact | Mitigation |
|------------|------|------------|--------|------------|
| **FastAPI** | Unstructured codebase growth | Medium | Medium | Enforce `apps/backend` layout in architecture doc; code review |
| **PostgreSQL** | Single server failure | Medium | High | Backups; documented restore; UPS on server |
| **Electron** | Memory on old PCs | Low | Medium | Monitor; min spec document; Tauri ADR if needed |
| **Electron** | Security misconfiguration | Medium | High | Security checklist; lint rules; ADR for Electron config |
| **React Native** | Android fragmentation | Medium | Low | Test on 2–3 target devices |
| **Tally XML** | Mapping failures | High | High | POC; manual fallback per PRD |
| **openpyxl** | File lock conflicts | Medium | Medium | Atomic writes; retry; user guidance |
| **JWT** | Token theft on LAN | Low | High | Short expiry; refresh rotation; TLS when remote access enabled |
| **Windows Services** | Service fails to start after reboot | Medium | High | Auto-start policy; post-update verification; UPS for power loss |
| **Python deps** | Supply chain vulnerability | Medium | Medium | Pin versions; Dependabot; audit |
| **Single developer** | Bus factor | High | High | Documentation; ADRs; AI context files |

---

## 18. Architecture Readiness

### 18.1 Ready for SYSTEM_ARCHITECTURE.md?

**Conditionally yes** — proceed after:

| # | Gate | Status |
|---|------|--------|
| 1 | TECH_STACK.md approved (this document) | **Pending** |
| 2 | ADR-0002: Backend stack (FastAPI + PostgreSQL) | **Required** |
| 3 | ADR-0003: Desktop stack (Electron + React) | **Required** |
| 4 | ADR-0004: Mobile stack (React Native Android) | **Required** |
| 5 | ADR-0005: Authentication (JWT + bcrypt + RBAC) | **Required** |
| 6 | Tally integration POC | **Required** |
| 7 | PRD TBD items (lifecycle default, config field structure) | **Recommended** |

### 18.2 Recommended Changes Before Architecture

| Change | Priority |
|--------|----------|
| Record ADRs 0002–0005 mirroring this document | Critical |
| Define monorepo workspace layout (`pnpm` + Python project) | Critical |
| Validate Tally XML POC on production Tally version | Critical |
| ADR-0006: Windows Server deployment (services, firewall, backup paths) | High |
| Document reverse proxy / TLS strategy ADR when remote access is required | Medium |
| Define OpenAPI-first vs code-first generation policy | High |
| Pin exact dependency versions at project init | High |
| Update PROJECT_BIBLE Product Identity — Primary Language | Medium |

**No stack replacement recommended.** The candidate stack is sound.

---

## 19. Security Deployment Checklist

### 19.1 Critical (V1 Go-Live)

- [ ] Windows 11 Pro dedicated server — not used as a workstation
- [ ] WEBSTUDIO API, Excel Sync, and Tally Sync installed as Windows Services with **Automatic** start
- [ ] PostgreSQL Windows service set to **Automatic** start
- [ ] Services verified running after reboot (post Windows Update test)
- [ ] API served directly by Uvicorn on LAN — firewall allows API port from store subnet only
- [ ] PostgreSQL `webstudio_app` user — not superuser
- [ ] Secrets in environment variables only — not in Git
- [ ] bcrypt password hashing — cost ≥ 12
- [ ] JWT access + refresh with rotation
- [ ] RBAC enforced on every API endpoint with tests
- [ ] Electron: `contextIsolation`, `nodeIntegration: false`, `sandbox: true`
- [ ] Android: encrypted token storage
- [ ] Audit logging for inventory mutations and auth events
- [ ] Firewall: API port restricted to store LAN subnet
- [ ] Backup directory configured (e.g., `D:\WEBSTUDIO-IMS\backups\`) with tested restore
- [ ] Default Main Admin password changed on first deploy

### 19.2 Recommended (V1)

- [ ] Rate limiting on login endpoint
- [ ] `pg_trgm` indexes for configuration search
- [ ] JSON structured logging with correlation IDs
- [ ] Excel sync atomic write pattern
- [ ] Tally XML input validation (defusedxml)
- [ ] Dependabot / dependency audit in CI
- [ ] Playwright smoke tests on critical paths
- [ ] OS disk encryption on server

### 19.3 Future Improvements

- [ ] Reverse proxy (Caddy or nginx) with TLS termination for remote access
- [ ] Argon2id password hashing
- [ ] Certificate pinning on Android
- [ ] Redis for session/cache
- [ ] Sentry or equivalent APM
- [ ] Electron auto-update with code signing
- [ ] MFA for Main Admin
- [ ] VPN for remote access
- [ ] PostgreSQL replication / failover

---

## 20. Final Approval Checklist

| # | Item | Owner | Status |
|---|------|-------|--------|
| 1 | TECH_STACK.md reviewed by technical lead | WEBSTUDIO IMS Team | **Pending** |
| 2 | Business owner accepts Electron memory tradeoff | Business Owner | **Pending** |
| 3 | Tally POC successful on live instance | Engineering | **Pending** |
| 4 | ADR-0002 through ADR-0005 created and Accepted | Architecture | **Pending** |
| 5 | Security checklist Critical items planned | Engineering | **Pending** |
| 6 | PROJECT_BIBLE updated — technologies no longer TBD | Documentation | **Pending** |
| 7 | PRD non-functional security requirements mapped to stack | QA | **Pending** |
| 8 | Dedicated Windows 11 Pro Server PC hardware spec agreed | Operations | **Pending** |

**Upon completion:** Change this document status from **Proposed** to **Active** and version to **1.0 (Frozen)**.

---

## 21. References

| Document | Path |
|----------|------|
| Project Bible | [docs/PROJECT_BIBLE.md](PROJECT_BIBLE.md) |
| Product Requirements | [docs/product/PRODUCT_REQUIREMENTS.md](product/PRODUCT_REQUIREMENTS.md) |
| ADR Index | [adr/README.md](../adr/README.md) |
| FastAPI Research | [docs/research/fastapi-research.md](research/fastapi-research.md) |
| PostgreSQL Research | [docs/research/postgresql-research.md](research/postgresql-research.md) |
| Electron Research | [docs/research/electron-research.md](research/electron-research.md) |
| Android Research | [docs/research/android-research.md](research/android-research.md) |
| Tally Research | [docs/research/tally-erp9-research.md](research/tally-erp9-research.md) |
| Excel Research | [docs/research/excel-sync-research.md](research/excel-sync-research.md) |
| Security Documentation | [docs/security/README.md](security/README.md) |

---

> **Document Authority:** Approved technologies in this document are binding for WEBSTUDIO IMS implementation. Deviations require an ADR. This document should be read alongside PROJECT_BIBLE.md and PRODUCT_REQUIREMENTS.md before writing SYSTEM_ARCHITECTURE.md.

*WEBSTUDIO IMS Team — 2026*
