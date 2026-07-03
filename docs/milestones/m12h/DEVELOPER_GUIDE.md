---
Title: Developer Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Developer Guide

Build, test, and extend WEBSTUDIO IMS.

---

## 1. Repository structure

```
WEBSTUDIO IMS/
├── apps/backend/          # FastAPI (Python 3.12+)
├── apps/desktop/          # Electron + React
├── apps/mobile_flutter/   # Flutter mobile
├── database/migrations/   # Alembic (head: 0036)
├── packages/              # Shared TypeScript
├── config/env/            # Environment profiles
├── scripts/release/       # Release engineering
└── docs/                  # Specifications
```

Read [AGENTS.md](../../../AGENTS.md) and [.ai/CONTEXT.md](../../../.ai/CONTEXT.md) before coding.

---

## 2. Local development

```bash
# Dependencies
pnpm install
python3 -m venv .venv && source .venv/bin/activate
pip install -e apps/backend

# Database (Docker Postgres)
docker compose up -d

# Backend
bash tools/scripts/dev-backend.sh

# Desktop
pnpm desktop:dev
```

See [LOCAL_DEVELOPMENT.md](../../development/LOCAL_DEVELOPMENT.md)

**Never run** `fresh-dev.sh` or `docker compose down -v` unless explicitly wiping data.

---

## 3. Testing

```bash
# Backend
cd apps/backend && pytest

# Desktop
pnpm --filter @webstudio/desktop test

# Flutter
pnpm mobile:flutter:test
```

---

## 4. Database migrations

```bash
cd apps/backend
alembic -c ../../database/migrations/alembic.ini revision -m "description"
alembic -c ../../database/migrations/alembic.ini upgrade head
```

Document in `database/schemas/` and migration doc.

---

## 5. API development

1. Extend [OpenAPI spec](../../api/openapi/webstudio-ims-api-v1.yaml)
2. Update [API-001](../../api/API_SPECIFICATION.md)
3. Implement router in `api/routers/`
4. Add Pydantic schemas
5. Add tests in `tests/`

**Never invent endpoints** without spec update.

---

## 6. Tally integration

| Module | Path |
|--------|------|
| Sync service | `services/tally_sync_service.py` |
| XML client | `integrations/tally/xml_client.py` |
| Developer XML | [xml-developer-guide.md](../../integrations/tally-erp9/xml-developer-guide.md) |

---

## 7. Release build

```bash
pnpm release:prepare    # Manifest, checksums, migrations bundle
pnpm desktop:package:win
```

[M12G Release Engineering](../m12g/RELEASE_ENGINEERING_REPORT.md)

---

## 8. Conventions

- Naming: [style-guide.md](../../meta/style-guide.md)
- Commits: reference ADR/spec IDs
- No secrets in git
- Update docs with code changes

---

## 9. Key documents

| Doc | ID |
|-----|-----|
| Architecture | ARCH-001 |
| Database | DATABASE_DESIGN |
| Implementation | IMPLEMENTATION_GUIDE |
| Project rules | PROJECT_BIBLE |

---

## 10. IDE setup

- Python: `.venv`, Ruff, mypy
- TypeScript: ESLint, Prettier (pnpm format)
- Flutter: stable channel, `flutter_launcher_icons`
