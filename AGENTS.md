---
Title: AI Agent Instructions
Version: 0.1.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: None
---

# WEBSTUDIO IMS — Agent Instructions

Instructions for AI assistants (Cursor, ChatGPT, Antigravity, and others) working on this repository.

## Read Before Any Task

1. [docs/PROJECT_BIBLE.md](docs/PROJECT_BIBLE.md) — Project constitution (highest authority)
2. [docs/product/PRODUCT_REQUIREMENTS.md](docs/product/PRODUCT_REQUIREMENTS.md) — Product requirements (PRD)
3. [docs/TECH_STACK.md](docs/TECH_STACK.md) — Approved technology stack
4. [.ai/CONTEXT.md](.ai/CONTEXT.md) — Project overview and boundaries
3. [.ai/GLOSSARY.md](.ai/GLOSSARY.md) — Domain and business terminology
4. [.ai/CONSTRAINTS.md](.ai/CONSTRAINTS.md) — Non-negotiable rules
5. [docs/ai/context-guide.md](docs/ai/context-guide.md) — Repository navigation guide
6. [adr/records/](adr/records/) — Binding architectural decisions

## Task-Specific Entry Points

| Task | Start Here |
|------|------------|
| Backend API | [docs/api/openapi/](docs/api/openapi/) |
| Database | [database/schemas/](database/schemas/) and [docs/database/](docs/database/) |
| Desktop | [docs/development/platform-guides/desktop.md](docs/development/platform-guides/desktop.md) |
| Mobile | [docs/development/platform-guides/mobile.md](docs/development/platform-guides/mobile.md) |
| Tally Integration | [docs/integrations/tally-erp9/](docs/integrations/tally-erp9/) |
| Excel Sync | [docs/integrations/excel/](docs/integrations/excel/) |
| **M14 Production (FINAL)** | [docs/milestones/m14/M14_GLOBAL_RULES.md](docs/milestones/m14/M14_GLOBAL_RULES.md) — deployment & handover only; no new features |

## Rules

- Never invent API endpoints — extend OpenAPI spec first
- Never invent database tables — add migration and schema doc
- Match naming conventions in [docs/meta/style-guide.md](docs/meta/style-guide.md)
- Update documentation in the same change as code
- Reference spec and ADR IDs in commits and PRs
- **Never run `fresh-dev.sh` or `docker compose down -v`** unless the user explicitly asks to wipe local data. Code edits, backend `--reload`, and `pnpm desktop:dev` do **not** require a database reset.
