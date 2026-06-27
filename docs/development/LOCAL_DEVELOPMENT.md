---
Title: Local Development
Version: 1.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/IMPLEMENTATION_GUIDE.md, docs/TECH_STACK.md
---

# Local Development

## Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- Python 3.12+
- Node.js 20 LTS + pnpm 9.x

## 1. Environment file

Copy the template to the repository root (used by Docker Compose and the backend):

```bash
cp config/env/.env.example .env
```

Edit `.env` only if you need non-default credentials or ports. `DATABASE_URL` must match `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and `POSTGRES_PORT`.

## 2. Start PostgreSQL (Docker)

From the repository root:

```bash
docker compose up -d
```

Wait until the container is healthy:

```bash
docker compose ps
```

Expected: `webstudio-ims-postgres` status **healthy**.

Stop PostgreSQL:

```bash
docker compose down
```

Stop and remove the data volume (destructive):

```bash
docker compose down -v
```

## 3. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e "apps/backend[dev]"
bash tools/scripts/dev-backend.sh
```

Verify readiness (requires PostgreSQL healthy):

```bash
curl http://127.0.0.1:8000/health/ready
```

Run Alembic (after PostgreSQL is up):

```bash
bash tools/scripts/alembic.sh upgrade head
```

## 4. Desktop

```bash
pnpm install
pnpm desktop:dev
```

## 5. Mobile

```bash
pnpm --filter @webstudio/mobile start
```

Android emulator API base URL: `http://10.0.2.2:8000` (host machine).
