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

**Data is preserved** when you stop without `-v`. Your setup, users, and inventory remain in the Docker volume `webstudio_pg_data`.

### Database safety (read this)

| Action | Data preserved? |
|--------|-----------------|
| `docker compose up` / `down` | Yes |
| Restart Docker Desktop | Yes |
| `docker compose down -v` | **No — volume deleted** |
| `I_UNDERSTAND_DATA_WILL_BE_DELETED=1 bash tools/scripts/fresh-dev.sh` | **No — intentional reset** |

If login suddenly fails with “system not initialized”, the database was reset or never completed setup — **not** a wrong password. The desktop app will redirect you to the Setup Wizard automatically.

### Code changes do NOT erase your data

| Safe (data kept) | Destructive (data lost) |
|------------------|-------------------------|
| Editing TypeScript / Python / CSS | `docker compose down -v` |
| Backend auto-reload (`dev-backend.sh`) | `fresh-dev.sh` |
| Desktop hot reload (`pnpm desktop:dev`) | Dropping the Docker volume manually |
| Restarting Docker Desktop | `pytest` against `webstudio_dev` (tests use `webstudio_test`) |
| `docker compose down` then `up` | Restoring an empty backup over live data |

Your inventory lives in the PostgreSQL Docker volume `webstudio_pg_data`. It survives restarts until you explicitly delete that volume.

### Backend tests use a separate database

`pytest` **must not** touch your dev data. Tests run against **`webstudio_test`**, not `webstudio_dev`.

Create the test database once (PostgreSQL must be running):

```bash
bash tools/scripts/ensure-test-db.sh
```

Run backend tests:

```bash
source .venv/bin/activate
pytest
```

**Never** point `DATABASE_URL` at `webstudio_dev` and run `pytest` — test fixtures `TRUNCATE` tables and will wipe users, setup, and inventory.

**Before risky operations**, back up:

```bash
bash tools/scripts/backup-db.sh
```

Backups are written to `backups/` at the repository root.

**Restore a backup** (PostgreSQL must be running):

```bash
docker compose exec -T postgres psql -U webstudio webstudio_ims < backups/your-backup.sql
```

Stop and remove the data volume (destructive):

```bash
docker compose down -v
```

Prefer the guarded reset script (backs up first, requires explicit confirmation):

```bash
I_UNDERSTAND_DATA_WILL_BE_DELETED=1 bash tools/scripts/fresh-dev.sh
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

## 6. Gemini auto-fetch (optional)

Add Laptop can auto-fill specifications using Google Gemini. Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey), then add to `.env` or `config/env/.env.local`:

```bash
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-flash-lite-latest
```

Restart the backend after changing environment variables. Without a key, specs are entered manually in the wizard.
