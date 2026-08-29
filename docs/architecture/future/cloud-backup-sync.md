---
Title: Future — Google Drive Cloud Backup Sync
Version: 0.1.0
Status: Spec — ready to implement
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-08-16
Related Documents:
  - docs/internal/BACKUP_RESTORE.md
  - docs/milestones/m14/BACKUP_MANUAL.md
  - docs/operations/SERVER_RECOVERY_RUNBOOK.md
---

# Future — Google Drive Cloud Backup Sync

**Read this whole document before writing any code.** It was written after a real production incident (server hardware died; the only backups were local to that machine) exposed exactly the gap this feature closes. Everything below is grounded in the actual current codebase, not assumptions — file paths and line numbers are real as of `feature/database-core` commit `c61ba30`. If a referenced line number has drifted, re-find the function by name; the surrounding logic described should still be accurate.

**Hand this file to a fresh Claude Code session and say: "implement the spec in `docs/architecture/future/cloud-backup-sync.md`."** It's self-contained. Do not require the implementing session to have any memory of the incident that produced it.

---

## 0. The one rule that matters more than any other

**Local backup must keep working exactly as it does today, completely unaffected by this feature, including when this feature is broken, misconfigured, offline, or not yet set up.**

Concretely:
- `BackupEngine.create_backup()`'s existing logic (dump → copy assets → tar.gz → manifest → checksum → `mark_completed` → local retention) must not be modified in its core path. It's fine to add something *after* a backup already exists in `backup_runs` — see §3 for exactly where.
- If Google Drive is unreachable, the OAuth token expired, the quota is exceeded, or the feature was never configured — **the local backup must still succeed**, with no error surfaced to the user beyond an informational notification that cloud sync is behind.
- If this feature has a bug, worst case is that cloud backups stop happening. It must never be able to cause a local backup to fail, corrupt, or not be retained locally.
- Existing settings keys, existing API routes, and the existing `backup_storage_backend` values (`local`, `nas`, `external_drive`, `cloud`) must not be renamed or removed. Add `google_drive` as a new value; don't repurpose the generic `cloud` placeholder.

Given this, **the recommended architecture is a fully decoupled, independent background scheduler that reads `backup_runs` history and uploads what's pending — not a hook inline inside `create_backup()`.** This means implementing this feature end-to-end should require **zero changes** to `backup_engine.py`'s `create_backup` method itself. If you find yourself editing that method's core dump/copy/manifest logic, stop and reconsider — you're probably about to violate §0.

---

## 1. What to build (scope for v1)

1. One-time OAuth connection to a Google Drive account (the shop's own free personal account — no paid subscription required, see §7).
2. Every local backup that completes successfully gets uploaded to a dedicated Drive folder, automatically, on its own schedule — no user action after initial setup.
3. Drive-side retention: keep the most recent N uploaded backups (default **25**, admin-configurable, matching the user's ask of "20-30"), auto-delete older ones on Drive. This is independent from local retention (`_apply_retention()`, already exists, untouched).
4. Admin can **disconnect and reconnect a different Google account** later (e.g., if the shop's Google Workspace/account changes) — from Settings, no code changes needed.
5. If cloud sync fails for any reason, it's visible (status + last error in Settings, an in-app notification), but never blocking.

**Explicitly out of scope for v1** (note these, don't build them, don't let scope creep in):
- OneDrive / Dropbox real implementations — leave those stub classes as-is.
- Restoring directly from Drive without downloading the file first (existing "Import backup file" flow already handles a manually-downloaded archive — that's enough for v1).
- Multi-account / multi-folder / per-location cloud targets.
- Encrypting the archive contents beyond what already exists (`backup_encryption.py` is a no-op today; not this feature's job to change that).

---

## 2. Current state (verified, not assumed)

- `apps/backend/src/webstudio_backend/services/backup_storage.py` — `GoogleDriveBackupStorage` class already exists but is a stub: its inherited `upload()`/`download()` just `raise NotImplementedError`, and critically **`upload()` is never called anywhere in the codebase today**. Selecting a cloud backend in Settings currently does nothing different from `local` — it silently resolves to the same local path. This is the gap.
- `apps/backend/src/webstudio_backend/services/backup_engine.py`, `create_backup()` (~lines 92-301): dump → `_copy_managed_assets` → tar.gz written → **line ~189-197: manifest gets patched into the already-written archive (this is the point the archive's final bytes are locked)** → **line ~209-210: checksum + final `stat()` computed — this is the exact point where the archive is complete, immutable, and its path/checksum/size are all known** → `mark_completed()` (~line 212) → local `_apply_retention()` (~line 745) → alerts → commit → return `BackupResult`.
- Encrypted secret storage already exists and should be reused, not reinvented: `apps/backend/src/webstudio_backend/infrastructure/security/secret_encryption.py` — `encrypt_secret(plain_text, *, secret)` / `decrypt_secret(cipher_text, *, secret)`, Fernet symmetric encryption, key derived via SHA-256 of `Settings.jwt_secret` (env `JWT_SECRET`). The real reference consumer of this pattern is `apps/backend/src/webstudio_backend/services/integration_key_service.py` (`create_key`/`update_key`), which encrypts a value and stores it alongside a `mask_secret()` hint in the `integration_api_keys` table (model: `apps/backend/src/webstudio_backend/infrastructure/database/models/integration_api_key.py`). **Before deciding on a new table, read that model's full schema — if it already has a generic `provider`/`name` + `encrypted_value` + `key_hint` shape, store the Drive refresh token as a row there (`provider="google_drive_refresh_token"`) instead of creating a new table.** Only create a dedicated table (e.g. `cloud_backup_connections`) if that table's schema is too narrow (e.g. hardcoded to a fixed enum of known integrations) to extend safely.
- Background scheduler pattern to copy: `apps/backend/src/webstudio_backend/services/backup_scheduler.py` (whole file is the template — `maybe_run_scheduled_backup()` + `backup_scheduler_loop()`). Startup wiring lives in `apps/backend/src/webstudio_backend/app.py`'s `lifespan()` — env-gated (`settings.webstudio_backup_scheduler`), launched via `asyncio.create_task(...)`, cancelled on shutdown. Env flag pattern: `apps/backend/src/webstudio_backend/core/config.py` (`webstudio_backup_scheduler: bool`, parsed by `parse_scheduler_env_flag`). Interval/next-run persistence: `apps/backend/src/webstudio_backend/services/scheduler_runtime_service.py` — `DEFAULT_INTERVALS` dict, `record_run()`, module-level `sleep_until_next_run()` (reused as-is by every scheduler, don't reinvent it).
- Desktop UI: `apps/desktop/src/components/settings/SettingsPanels.tsx`, `BackupPanel` component, storage backend `<select>` at ~lines 1502-1519 currently offers `local` / `nas` / `external_drive` / `cloud` with **no conditional UI for any of them** (contrast with the `retention_policy === 'custom'` conditional at ~line 1489, which *does* show an extra field when selected — that's the pattern to copy for a new `storage_backend === 'google_drive'` block). Type union to extend: `apps/desktop/src/services/api/SettingsService.ts` (`storage_backend: 'local' | 'cloud' | 'nas' | 'external_drive'` → add `'google_drive'`).
- Permissions: reuse existing `backup:manage` (create/configure) and `backup:view` (status only) — documented in `docs/internal/BACKUP_RESTORE.md`.
- Notifications: reuse `services/backup_alert_service.py`'s existing pattern (backup completed/failed/low-storage alerts already flow through it) — add cloud-sync failed/succeeded events the same way, don't build a parallel notification path.

---

## 3. Backend design

### 3.1 Data model additions (new Alembic migration)

Additive only — nothing existing changes shape.

1. **Connection/credentials storage** — either a new row in `integration_api_keys` (preferred if its schema supports an arbitrary provider name — verify first) or a new small table if not:
   ```
   cloud_backup_connections
     id, provider ('google_drive'), account_email (plain, for display),
     encrypted_refresh_token, drive_folder_id, status ('connected'|'disconnected'|'error'),
     connected_at, connected_by_user_id, last_sync_at, last_sync_status, last_error,
     created_at, updated_at
   ```
2. **Per-backup upload tracking** — add nullable columns to the existing `backup_runs` table (do not touch any existing column): `cloud_uploaded_at`, `cloud_upload_status` (`pending`/`uploaded`/`failed`/`skipped`), `cloud_file_id` (the Drive file ID, for retention deletion later). Nullable + no default-required-value means every existing row and every existing query against `backup_runs` is unaffected.

### 3.2 OAuth flow — read this carefully, it's the part most likely to be gotten wrong

The WEBSTUDIO server runs plain HTTP on a LAN IP (e.g. `192.168.29.100:8000`), deliberately, with no public HTTPS endpoint (`TLS_CERT_PATH`/`TLS_KEY_PATH` stay empty by design — see `docs/operations/SERVER_RECOVERY_RUNBOOK.md` Part C5). Google's OAuth redirect URI rules require HTTPS for any "Web application" client type, except for `localhost`/`127.0.0.1`. **You cannot register `http://192.168.29.100:8000/...` as an OAuth redirect URI.** Don't attempt a server-side redirect flow — it will not pass Google's client registration validation.

**Use the standard installed-app "loopback" pattern instead**, run from the **desktop Electron app**, not the server:

1. Register a Google Cloud OAuth Client ID of type **"Desktop app"** (see §7 for the human setup steps — this is a one-time thing the shop owner does in Google Cloud Console, not something the code does).
2. In the desktop app, "Connect Google Drive" triggers the **Electron main process** (find the entry point — it builds to `dist-electron/main.js`, source is under `apps/desktop/electron/`) to:
   - Start a temporary local HTTP listener on `http://127.0.0.1:<ephemeral port>` (Node's built-in `http` module is enough — no new dependency needed).
   - Open the system browser (`shell.openExternal`) to Google's OAuth consent URL, with `redirect_uri` pointing at that loopback listener and the Drive scope (`https://www.googleapis.com/auth/drive.file` — this scope is enough; it only grants access to files the app itself creates, not the user's whole Drive, which is both more secure and avoids Google's stricter verification requirements for broader scopes).
   - When Google redirects back to the loopback listener with an authorization code, exchange it for tokens by calling Google's token endpoint directly from the Electron process (using the Desktop client ID + secret — for installed apps, Google does not treat this secret as fully confidential, but still don't commit it in plaintext to the public repo; load it from a config/env value, same pattern as `WEBSTUDIO_GITHUB_TOKEN`).
   - Send the resulting **refresh token** and the connected account's email up to the backend over the existing authenticated API (new endpoint, see §3.4) — the backend encrypts it immediately using `encrypt_secret()` and never returns it in plaintext again.
   - Close the loopback listener.

This is exactly how the `gh` CLI and `gcloud` CLI do OAuth for installed apps — it's a well-established, Google-supported pattern, and it sidesteps the "no public HTTPS endpoint" constraint entirely because the redirect target is the admin's own machine, not the server.

**OAuth consent screen mode:** set it up in "Testing" mode in Google Cloud Console with the shop's own Google account added as a test user (see §7) — this avoids Google's app-verification review process (unnecessary for a single-account internal tool) while still issuing long-lived refresh tokens to that specific test-user account.

### 3.3 Upload + retention scheduler

New file: `apps/backend/src/webstudio_backend/services/cloud_backup_sync_scheduler.py`, structured exactly like `backup_scheduler.py`:

- `maybe_run_cloud_backup_sync()`: 
  1. Read the connection row; if not connected or disabled, return early (no-op, no error).
  2. Query `backup_runs` for rows where `status='completed'` and `cloud_upload_status` is `NULL` or `pending`, oldest-first, capped at a small batch (e.g. 5 per cycle — don't try to upload everything at once if catching up after downtime).
  3. For each: upload the archive file (already on local disk at its known path) to the Drive folder via the Drive API's resumable upload (files can be tens of MB+; use `google-api-python-client`'s `MediaFileUpload` with `resumable=True`). On success, set `cloud_uploaded_at`, `cloud_upload_status='uploaded'`, `cloud_file_id=<drive file id>`. On failure, set `cloud_upload_status='failed'`, log a warning, **do not raise** — move to the next row, retry on the next scheduled cycle.
  4. After uploads, run Drive-side retention: list files in the target folder ordered by creation time, delete anything beyond the configured retention count (mirror the counting logic in `BackupEngine._apply_retention()` — read it, don't reinvent the policy).
  5. Update the connection row's `last_sync_at`/`last_sync_status`/`last_error`.
  6. Route completion/failure through `BackupAlertService`, same as the existing backup scheduler does.
- `cloud_backup_sync_scheduler_loop()`: identical shape to `backup_scheduler_loop()` — `sleep_until_next_run("cloud_backup_sync", ...)`, try/except around the maybe-run call, never let an exception escape the loop.
- Add `"cloud_backup_sync": 900` (or similar) to `DEFAULT_INTERVALS` in `scheduler_runtime_service.py`.
- Add `webstudio_cloud_backup_sync_scheduler: bool` to `config.py` next to `webstudio_backup_scheduler`, registered in the same `parse_scheduler_env_flag` validator list.
- Wire it into `app.py`'s `lifespan()` exactly like the existing backup scheduler task (gate check → `asyncio.create_task` → cancel on shutdown). Three small additions, nothing existing touched.

New backend dependencies (add to `apps/backend/pyproject.toml` or equivalent): `google-api-python-client`, `google-auth`, `google-auth-oauthlib` (the last one may not even be needed server-side if token exchange happens in Electron — only add what's actually used server-side, likely just `google-api-python-client` + `google-auth` for making authenticated Drive API calls using the stored refresh token).

### 3.4 New API routes

Under the existing `/api/v1/settings/backups/cloud/...` prefix, alongside existing backup routes in `apps/backend/src/webstudio_backend/api/routers/settings.py`. Permission: `backup:manage` for connect/disconnect/retention changes, `backup:view` for status.

- `POST /api/v1/settings/backups/cloud/google-drive/connect` — body: `{refresh_token, account_email}` (sent by the Electron loopback flow after token exchange). Encrypts and stores the token, creates/reuses the "WEBSTUDIO Backups" Drive folder, sets status `connected`.
- `POST /api/v1/settings/backups/cloud/google-drive/disconnect` — clears the stored token, sets status `disconnected`. Does **not** delete anything already uploaded to Drive (out of reach anyway once disconnected) and does **not** touch local backups or local history rows.
- `GET /api/v1/settings/backups/cloud/status` — connection status, masked account email, last sync time/status/error, current retention count.
- `PATCH /api/v1/settings/backups/cloud/retention` — body: `{retention_count: int}`, admin-adjustable (default 25, sane range e.g. 5–100 — don't hardcode 20-30 as a hard limit, that was the user's suggested default, not a ceiling).

### 3.5 Reconnecting to a different account (the "future should be able to change the Drive" requirement)

No special code path beyond disconnect + connect again — that's the whole design. On a fresh connect, always create-or-reuse a "WEBSTUDIO Backups" folder in whichever account is currently authorized. Backups already uploaded to the previous account stay there (the app has no way to reach them post-disconnect, which is correct — they were that account's data). New backups going forward upload to the newly connected account. Make sure the Settings UI account-email display updates immediately after a successful reconnect so it's obvious which account is currently active.

---

## 4. Desktop UI changes

In `SettingsPanels.tsx`'s `BackupPanel`:
- Add `'google_drive'` to the storage backend `<select>` options and to the `SettingsService.ts` type union.
- Add a conditional block when `storage_backend === 'google_drive'` (same pattern as the existing `retention_policy === 'custom'` conditional), showing:
  - If not connected: a **"Connect Google Drive"** button that triggers the Electron loopback OAuth flow (§3.2) via IPC to the main process.
  - If connected: the connected account's email, last sync time + status (with a clear failed/pending indicator, not just silence), a retention-count input (`PATCH .../cloud/retention`), and a **"Disconnect"** button (with a confirmation dialog, since it stops future uploads — but make clear in the dialog copy that it does not delete existing local or already-uploaded backups).
- Surface cloud upload status per-backup in `BackupAdminCenter.tsx`'s history list too (a small "Synced to Drive" / "Pending" / "Failed" indicator per row), if that list already renders per-row status for other fields — follow its existing formatting conventions rather than introducing a new visual pattern.

---

## 5. Failure handling checklist (verify all of these before considering this done)

- [ ] Google Drive never connected/configured → local backups run exactly as today, no errors, no notifications about cloud sync (nothing to report yet).
- [ ] Drive connected, then network drops → local backup still succeeds; cloud sync scheduler logs a failure, retries next cycle, does not crash the scheduler loop or the app.
- [ ] Refresh token revoked/expired (e.g. admin revoked app access from their Google account settings) → sync scheduler detects the auth failure specifically, sets connection `status='error'` with a clear `last_error` message (not a raw stack trace), surfaces a "reconnect needed" state in Settings, and stops retrying every cycle (back off — don't hammer a dead credential every 15 minutes forever; maybe try once per hour once in `error` state).
- [ ] Drive storage quota exceeded → same graceful degradation as above, distinct error message if the API response makes that distinguishable.
- [ ] Uploading a large backup archive (tens of MB, growing over time with more product images) → uses resumable upload, doesn't block the scheduler loop for other work, has a reasonable timeout.
- [ ] Retention deletion on Drive only ever deletes files inside the app's own "WEBSTUDIO Backups" folder (the `drive.file` scope already guarantees this structurally — the app literally cannot see or touch anything else in the user's Drive).
- [ ] Disconnecting mid-upload doesn't leave the connection row or a `backup_runs` row in a stuck/inconsistent `pending` state forever — either the in-flight upload completes and then respects the disconnect for future cycles, or it's cleanly abandoned and marked `failed`, not left ambiguous.

---

## 6. Testing requirements

Mock the Google API client in backend unit tests — never call the real Drive API from the test suite. Cover: successful upload updates `backup_runs` correctly; a failed upload doesn't raise past the scheduler loop; retention deletion picks the correct (oldest-beyond-count) files; disconnect clears credentials but not history; connect with a fresh account creates/reuses the folder correctly.

**Before this is considered ready to ship, all of the following must pass — these are the exact commands this project's CI runs, verified working as of tonight's incident fixes (commit `c61ba30`):**

```bash
# Backend
ruff check apps/backend/src apps/backend/tests database/migrations
black --check apps/backend/src apps/backend/tests database/migrations
pytest apps/backend/tests -q   # needs a local Postgres 16 matching CI's service container config, see ci-backend.yml

# Frontend (desktop + packages)
pnpm format:check
pnpm lint
pnpm typecheck
pnpm --filter @webstudio/desktop test
pnpm --filter @webstudio/desktop build

# Mobile (only relevant if this touches mobile — likely not for v1, but verify nothing broke)
cd apps/mobile_flutter && flutter analyze --no-fatal-infos && flutter test
```

If any of these fail, fix them before proposing a release build — do not push a version tag with a known-red pipeline. See `docs/operations/SERVER_RECOVERY_RUNBOOK.md`'s Appendix for the exact incident this constraint comes from — a previous cut corner here directly caused a production data-recovery emergency.

---

## 6a. Before proposing a build: the CI gate is not optional

Do not tell the user this feature is "ready" or suggest cutting a release until every command in §6 has actually been run and shown green in this exact session — not assumed, not "should pass." Tonight's incident happened in part because a corner like this got cut once already. Concretely, before saying "ready for a build":

1. Run every command listed in §6, in order, and paste/report the real output.
2. If backend tests need a local Postgres and none is running, start one (`docker run --name webstudio-ci-postgres -e POSTGRES_USER=webstudio_app -e POSTGRES_PASSWORD=webstudio_app -e POSTGRES_DB=webstudio_test -p 5432:5432 -d postgres:16-alpine`, or reuse this project's own dev container if one is already running via `compose.yaml` — check `docker ps` first) rather than skipping the backend suite.
3. If `flutter analyze`/`flutter test` need to run and this change didn't touch mobile code at all, still run them once to confirm nothing regressed — don't assume "I didn't touch that app" is the same as "it still passes."
4. Only once all of §6 is genuinely green should you tell the user it's ready to tag and build.

## 6b. How to actually trigger a build on GitHub (read this before pushing anything)

This repo has **two remotes**, and mixing them up cost real time during the incident this spec came out of. Confirm before doing anything:

```bash
git remote -v
```

You should see:
- **`origin`** → `https://github.com/Smarthsingh/WEBSTUDIO-IMS` — the real, canonical repo. This is what the production server's auto-update GitHub sync (`WEBSTUDIO_GITHUB_REPO=Smarthsingh/WEBSTUDIO-IMS`) actually points at, and what shows up if you browse to GitHub and look at the "real" project.
- **`gptsmarth`** → `https://github.com/gptsmarth/Webstudio-IMS.git` — a fork. This is the repo where release builds actually got triggered from during the incident, because that's the remote this local checkout's `feature/database-core` branch is set up to push to by default, and because the Actions workflows (which exist identically in both repos, since the fork has the same file history) were run from there. **`main` in either repo is an unrelated, essentially-empty 3-commit stub — it has never been used for a real release.** Every real release tag (`v1.0.0` through the latest) lives on `feature/database-core`, not `main`. Don't push to `main` expecting anything to happen; it won't.

**Push commits (code changes) to both, so neither drifts out of sync:**
```bash
git push origin feature/database-core
git push gptsmarth feature/database-core
```
Plain branch pushes like this never trigger a build — the release workflow only fires on a version tag. This is safe to do freely; it can't accidentally kick off a release.

**Trigger an actual build**, only once §6a's checks are all green, by pushing a **new** version tag (git tags are immutable — reusing an existing tag number requires a destructive force-push, which is a deliberate, separate decision, not a default):
```bash
git tag vX.Y.Z && git push gptsmarth vX.Y.Z
```
Pick the next unused tag — check first with `git tag -l "v*"` so you don't collide with one that already exists. This feature is a genuinely new capability, not a bugfix, so a minor version bump (e.g. the next `vX.(Y+1).0`) fits better than a patch bump — but that's a judgment call for whoever's cutting the release, not a hard rule.

The tag push triggers **Enterprise Release** (`.github/workflows/release.yml`) automatically on `gptsmarth/Webstudio-IMS` — no manual workflow click needed. Watch it at `https://github.com/gptsmarth/Webstudio-IMS/actions`. **Do not run this command yourself if you're an AI agent implementing this spec — it triggers a real production build.** Hand the exact command to the human and let them run it, the same way every tag push and force-push in the incident that produced this spec was handed to the user to execute, never run automatically by the assistant.

**Which account/credentials "push" runs as:** whatever this machine's git is already configured with (check `git config user.name` / `git config user.email`, and note it isn't necessarily the same as either GitHub account name — it's just commit-author metadata; actual push authorization comes from whatever credential helper or SSH key this machine already has set up for these two remotes, which was already working throughout the incident this spec came from, so nothing new needs configuring here).

---

## 7. Setup guide (what the shop owner does, once, by hand)

This happens in Google Cloud Console, before the "Connect Google Drive" button in the app will work. None of it requires a paid plan.

1. Go to [console.cloud.google.com](https://console.cloud.google.com), create a new project (any name, e.g. "WEBSTUDIO Backups").
2. **APIs & Services → Library** → search "Google Drive API" → Enable.
3. **APIs & Services → OAuth consent screen**:
   - User type: **External**.
   - App name: "WEBSTUDIO IMS Backups" (or similar), your own email as support contact.
   - Scopes: add `.../auth/drive.file` (only files this app creates — not full Drive access).
   - Publishing status: leave as **Testing**.
   - Test users: add the Google account (Gmail) you want backups to go to.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Desktop app**.
   - Name it, create it, note the **Client ID** and **Client Secret**.
5. Provide the Client ID/Secret to the WEBSTUDIO Desktop app's configuration (exact mechanism is an implementation detail — e.g. an env value baked into the installer, or a one-time Settings field — the implementing session should pick whichever fits the existing config-distribution pattern, consistent with how `WEBSTUDIO_GITHUB_TOKEN` is handled).
6. In the WEBSTUDIO desktop app: **Settings → Backup → Storage backend → Google Drive → Connect Google Drive**. A browser window opens, log into the Google account added as a test user in step 3, approve access. It closes automatically once done.
7. Confirm in Settings: the connected account's email shows, and "Run manual backup" followed by a wait for the next cloud sync cycle (or a manual "Sync now" if you build one) shows a successful upload in the status.
8. Storage: the free Google account tier includes 15GB, which comfortably fits a rolling 25-30 backups of a typical shop's database + product images. No payment needed unless that's ever exceeded (Google One paid tiers exist if so, but this isn't expected).

**To change the connected Drive account later:** Settings → Backup → **Disconnect**, then **Connect Google Drive** again and sign into the new account. Nothing else needs to change.

---

## 8. Open questions for the implementing session to resolve (not blocking, but worth a deliberate choice rather than a default)

- Exact storage location for the OAuth Client ID/Secret (env var on server vs. baked into desktop installer config vs. entered once in Settings) — pick whichever matches this project's existing convention most closely once you've looked at how `WEBSTUDIO_GITHUB_TOKEN`/`GEMINI_API_KEY` are actually distributed to installs today.
- Whether `integration_api_keys` table's existing schema is generic enough to reuse for the refresh token, or a dedicated table is cleaner — read the model first, decide based on what's actually there, don't guess.
- Exact retry backoff timing once a connection enters `error` state (a reasonable starting point is suggested above — once per hour instead of every 15 minutes — but tune based on what's least annoying without being silent for too long).
