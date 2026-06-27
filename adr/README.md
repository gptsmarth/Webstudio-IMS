---
Title: Architecture Decision Records — README
Version: 1.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/PROJECT_BIBLE.md, docs/SYSTEM_ARCHITECTURE.md
---

# Architecture Decision Records

## Purpose

Immutable record of significant architectural decisions. ADRs are superseded by new ADRs — never silently amended after **Accepted**.

## ADR Index

| ADR | Title | Status | Location |
|-----|-------|--------|----------|
| ADR-0001 | Monorepo structure | **Proposed** | [records/0001-monorepo-structure.md](records/0001-monorepo-structure.md) |
| ADR-0002 | Backend stack (FastAPI + PostgreSQL + SQLAlchemy) | **Consolidated** | Decisions in [TECH_STACK.md](../docs/TECH_STACK.md) §4–5 |
| ADR-0003 | Desktop stack (Electron + React + Vite) | **Consolidated** | [TECH_STACK.md](../docs/TECH_STACK.md) §6 |
| ADR-0004 | Mobile stack (React Native Android) | **Consolidated** | [TECH_STACK.md](../docs/TECH_STACK.md) §7 |
| ADR-0005 | Authentication & security (JWT + bcrypt + HTTPS) | **Superseded** | Superseded by **ADR-0010** |
| ADR-0006 | Windows deployment (services, firewall, backup) | **Consolidated** | [SYSTEM_ARCHITECTURE.md](../docs/SYSTEM_ARCHITECTURE.md) §20, [DEPLOYMENT_GUIDE.md](../docs/deployment/DEPLOYMENT_GUIDE.md) |
| ADR-0007 | Tally integration mechanism | **Superseded** | Superseded by **ADR-0011** |
| ADR-0008 | Excel sync schedule and file format | **Consolidated** | [SYSTEM_ARCHITECTURE.md](../docs/SYSTEM_ARCHITECTURE.md) §14, [DATABASE_DESIGN.md](../docs/database/DATABASE_DESIGN.md) §10 |
| ADR-0009 | Search indexing strategy (pg_trgm) | **Consolidated** | [DATABASE_DESIGN.md](../docs/database/DATABASE_DESIGN.md), [TECH_STACK.md](../docs/TECH_STACK.md) |
| ADR-0010 | Authentication and Initialization | **Accepted** | [ADR-0010-authentication-and-initialization.md](ADR-0010-authentication-and-initialization.md) |
| ADR-0011 | Tally Integration Strategy | **Accepted** | [ADR-0011-tally-integration-strategy.md](ADR-0011-tally-integration-strategy.md) |
| ADR-0012 | Reverse proxy / TLS (future remote access) | **Reserved** | Not authored — deferred until remote access is required |

**Consolidated:** Decision captured in governing documents; standalone ADR file not required for Version 1.

## Guidelines

- ADRs are immutable once **Accepted**. Supersede with a new ADR; never delete.
- Use [template.md](template.md) for new records.
- Number sequentially; reserve IDs before authoring (`ADR-0012` is reserved).

## Audience

Architects, senior developers, AI assistants.
