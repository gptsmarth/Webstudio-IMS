---
Title: Server Recovery Runbook — Replacing a Dead Server PC
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Related Documents:
  - docs/milestones/m14/DISASTER_RECOVERY_GUIDE.md
  - docs/milestones/m14/RESTORE_CHECKLIST.md
  - docs/milestones/m14/BACKUP_MANUAL.md
  - docs/milestones/m14/FIRST_TIME_SETUP_MASTER_GUIDE.md
  - docs/internal/BACKUP_RESTORE.md
  - docs/network/NETWORK_REQUIREMENTS.md
  - docs/integrations/tally-erp9/troubleshooting.md
  - docs/milestones/m14/TALLY_PRODUCTION_GUIDE.md
  - docs/milestones/m12/TALLY_CONNECTIVITY_HARDENING_REPORT.md
---

# Server Recovery Runbook — Replacing a Dead Server PC

Your production server (`WEBSTUDIO-SERVER`) died. You bought a new PC and have a copy of the old server's `D:\` drive. This document is the complete, in-order procedure to build the replacement and bring every piece of your data back — including the part everyone gets stuck on: **what to do the first time the new install asks you to run "Setup" instead of just logging in.**

Every step below is verified against this project's own documentation *and* its backend source code (not just the docs — the actual Python that runs the restore), so you can follow it with confidence that "restore" really does mean "everything comes back," not "some of it comes back."

**Read this whole document once before touching anything**, then work through it top to bottom.

---

## Contents

1. [What "fully recovered" actually means](#1-what-fully-recovered-actually-means)
2. [Before you start — gather this](#2-before-you-start--gather-this)
3. [Part A — Build the new server PC](#part-a--build-the-new-server-pc)
4. [Part B — Install PostgreSQL](#part-b--install-postgresql)
5. [Part C — Install the WEBSTUDIO Server software](#part-c--install-the-webstudio-server-software)
6. [Part D — The first-run Setup Wizard (read this carefully)](#part-d--the-first-run-setup-wizard-read-this-carefully)
7. [Part E — Restore your real data](#part-e--restore-your-real-data)
8. [Part F — Firewall and network reachability](#part-f--firewall-and-network-reachability)
9. [Part G — Reconnecting desktop apps and phones](#part-g--reconnecting-desktop-apps-and-phones)
10. [Part H — Reconnecting Tally](#part-h--reconnecting-tally)
11. [Part I — Verification checklist](#part-i--verification-checklist)
12. [Part J — Troubleshooting](#part-j--troubleshooting)
13. [Appendix — your site's documented values](#appendix--your-sites-documented-values)

---

## 1. What "fully recovered" actually means

Before the steps, it's worth knowing **why** this procedure works, because it explains a confusing moment you'll hit in Part D.

Every backup file WEBSTUDIO IMS creates (`webstudio-backup-*.tar.gz` in `D:\WEBSTUDIO-IMS\backups\`) contains a full data export of **every single table** in the application database — not a curated subset. Checked directly in the backend source (`services/backup_completeness.py`), that list is:

| Category | Tables included |
|---|---|
| Inventory & catalog | `inventory_items`, `product_models`, `brands`, `locations` |
| Sales | `sales` |
| People & access | `users`, `login_events`, `password_history`, `refresh_tokens` |
| System | `system_settings` (every setting, including company profile, branding, and the Gemini AI key), `audit_logs`, `notifications` |
| Integrations | `integration_api_keys`, `tally_company_sync`, `tally_processed_invoice`, `tally_processed_invoice_line`, `tally_sync_log`, `tally_sync_history` |
| Backup/restore history | `backup_runs`, `restore_runs` |

Plus, outside the database, the archive also carries your **brand logos, product images, company uploads, and a settings-registry snapshot**.

When you restore this archive, the backend doesn't merge it into whatever is already there — it runs `TRUNCATE ... CASCADE` on **every table in the schema** first (see `services/backup_completeness.py::truncate_webstudio_data`, called from `services/restore_engine.py`), then loads the backup's data straight into the now-empty schema. That means restore is not additive and not selective: whatever state the new install was in before you restored is completely discarded, and the old server's exact state — every user, every password, every sale, every setting — takes its place.

**This is exactly why Part D matters.** The fresh install *forces* you through a temporary setup step before it will let you log in at all (confirmed in `services/authentication_service.py`: login is refused outright while the system is "not initialized"). You have to get through that temporary setup just far enough to reach the restore screen — and then the restore **completely erases and replaces** what that temporary setup created. Nothing from the temporary setup survives; you're not merging two systems, you're using it as a doorway.

---

## 2. Before you start — gather this

- [ ] The copied `D:\WEBSTUDIO-IMS` folder from the dead server, reachable from the new PC (external drive, network share, or copied onto the new PC under a **different** folder name so it doesn't collide with the fresh install)
- [ ] Confirm that folder actually has a `backups\` subfolder containing `.tar.gz` files — that's the thing you're really here to recover. If it's missing or empty, stop and look for backups elsewhere (off-site USB/NAS copy) before proceeding — see [Part J](#part-j--troubleshooting).
- [ ] Internet access on the new PC (for downloading PostgreSQL and the WEBSTUDIO installer)
- [ ] Your shop router's admin login (to move the server's reserved IP address to the new PC)
- [ ] The **old** Main Admin username. You do not need the old password — it comes back automatically with the restore.
- [ ] 60–90 minutes uninterrupted. Nothing here is fast to undo once you're mid-restore, so don't start this the last hour before closing.

---

## Part A — Build the new server PC

**Goal:** the replacement machine should look identical to the old one from the network's point of view, so every desktop app, phone, and the Tally connection all keep working without being touched.

### A1. Install and update Windows

Windows 11 Pro, fully updated, with an administrator account.

### A2. Give it the old server's computer name

`Settings → System → About → Rename this PC` → set it to `WEBSTUDIO-SERVER` (or whatever the old server was named — check the Appendix) → reboot.

### A3. Connect it to the shop network and set the profile to Private

Ethernet or Wi-Fi, whichever the old server used. When Windows asks whether this is a public or private network, choose **Private**. A public profile blocks the inbound firewall rules you'll add in Part F.

### A4. Move the server's IP reservation to the new PC

The old server almost certainly had a **fixed IP address** reserved for it on your router (documented for this site as `192.168.29.100`, reserved by MAC address on the Jio router). Every client points at that fixed IP — not at "whatever IP the server happens to have today" — so the new PC needs to inherit it.

1. Find the new PC's MAC address:
   ```powershell
   ipconfig /all
   ```
   Look under the adapter you're actually using (Wi-Fi or Ethernet) for **Physical Address**.
2. Log into your router's admin page (`http://192.168.29.1` for this site).
3. Find the existing DHCP reservation/address-reservation entry that points the old MAC address at `.100`, and change the MAC address on that entry to the new PC's MAC. Keep the IP the same.
4. On the new PC, reconnect the network adapter (or reboot), then confirm:
   ```powershell
   ipconfig
   ```
   IPv4 address should now read `192.168.29.100`, gateway `192.168.29.1`.

> **If you'd rather not touch the router:** you can instead set a manual static IP directly on the new PC (`Settings → Network & Internet → [your adapter] → IP assignment → Manual`) using the same IP/mask/gateway. A router reservation is preferred because it survives OS reinstalls and adapter swaps.

**Why this step earns its place:** every desktop app, the mobile app, and the Tally sync all have `192.168.29.100:8000` (or your site's equivalent) hardcoded as the server address, either typed in once or baked into a saved connection. Give the new server a different IP and you'll be manually reconfiguring every single client afterward — this one router change avoids all of that.

---

## Part B — Install PostgreSQL

The database engine has to exist and be running before the WEBSTUDIO installer runs, because the installer needs to connect to it.

### B1. Install PostgreSQL

Download from [postgresql.org/download/windows](https://www.postgresql.org/download/windows/). Any of PostgreSQL 16, 17, or 18 is supported (auto-detected by the installer). Matching the old server's version exactly is nice-to-have, not required — restores are **data-only** dumps applied on top of a schema that gets freshly migrated on the new install, so the PostgreSQL major version doesn't need to match.

During install, set and **write down** the `postgres` superuser password — you'll need it once, in the next step.

### B2. Confirm the service is running

```powershell
Get-Service postgresql-x64-18
```

(Use `-16` or `-17` if that's what you installed.) Status must read **Running**.

### B3. Create the application database and login role

Open **pgAdmin** (installed alongside PostgreSQL) or `psql`, connect as the `postgres` superuser, and run:

```sql
CREATE USER webstudio_app WITH LOGIN PASSWORD 'YourStrongPassword123!';
CREATE DATABASE webstudio OWNER webstudio_app;
GRANT ALL PRIVILEGES ON DATABASE webstudio TO webstudio_app;
```

If you're using pgAdmin's GUI to create the role instead, make sure **Can login?** is checked when you create it — a role that can't log in will make every later step fail with an unhelpful authentication error.

**Write this password down.** You'll be prompted for it during the WEBSTUDIO installer in Part C, and it is *not* the same as the `postgres` superuser password from B1.

---

## Part C — Install the WEBSTUDIO Server software

### C1. Download the installer

From your GitHub Releases page (`https://github.com/Smarthsingh/WEBSTUDIO-IMS/releases` for this project), download the latest release's `WEBSTUDIO Server Setup.exe` asset. Always use the newest release available — older server installers had known post-install bugs (missing TLS handling, incomplete `.env` sync) that later releases fixed.

### C2. Run it as Administrator

Right-click → **Run as administrator**. When asked for an install path, use `D:\WEBSTUDIO-IMS`.

If you already copied the old data folder onto this PC's `D:` drive, **move it out of the way first** — e.g. rename it to `D:\WEBSTUDIO-IMS-OLD` — so the installer has a clean, empty target. Installing on top of the old folder is exactly the "copy the whole old folder over" mistake this runbook is steering you away from (see the intro note in your prior guide — old Python runtime paths, an old Windows service registration, and machine-specific bindings all live in that folder).

### C3. Let post-install finish

A PowerShell window stays open while it:

- Installs a bundled Python runtime and NSSM (the Windows service manager) — you don't install either of these yourself
- Prompts you for the `webstudio_app` password from Part B3
- Runs the database schema migrations
- Registers and starts the `WEBSTUDIO Server` Windows service

Log file, if you need it: `D:\WEBSTUDIO-IMS\logs\install-post.log`.

### C4. If the password prompt was missed, or setup closed early

Run this once, as Administrator:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\WEBSTUDIO-IMS\infra\windows\finalize-server-setup.ps1"
```

It re-prompts for the database password, fixes PostgreSQL's location on the service's PATH (needed for backups to work later), clears any leftover TLS certificate paths (this deployment runs plain HTTP), re-syncs the `.env` file, and restarts the service.

### C5. Verify both services are healthy

```powershell
Get-Service postgresql-x64-18
Get-Service "WEBSTUDIO Server"
curl.exe http://127.0.0.1:8000/health/live
curl.exe http://127.0.0.1:8000/health/ready
```

Both services should read **Running**, and both `curl` calls should return `200 OK`. Do not move on until this is true — everything after this point depends on the API actually being reachable.

---

## Part D — The first-run Setup Wizard (read this carefully)

This is the part that trips people up, so read it slowly. It's short.

### D1. Why the app makes you do this

A brand-new install has an empty database — no company, no admin user, nobody who could possibly log in. The backend refuses every login attempt outright until a one-time initialization step has completed (this is enforced in code, not just in the UI — there is no way to skip it or bypass it from the login screen).

So on a fresh install, opening the desktop app or browsing to the server doesn't show a login screen — it shows a **Setup Wizard**. You have to get through it, because doing so is the *only* way to unlock the login screen and reach the Restore Center where your real data lives.

**Everything you type into this wizard is temporary.** The restore in Part E wipes it out completely and replaces it with your real company name, real users, and real password — so don't worry about getting it "right." Use anything memorable enough to type twice in the next ten minutes.

### D2. Install the desktop app

On any admin laptop: install `WEBSTUDIO Desktop Setup.exe` (same GitHub release), launch it, and point it at your server:

```text
http://192.168.29.100:8000
```

### D3. Walk through the wizard

| Screen | What to enter | Why it doesn't matter long-term |
|---|---|---|
| Company name | Anything, e.g. `Temp Setup` | Overwritten by the real company name during restore |
| Main Admin — display name, username, password | Anything you can remember for the next few minutes, e.g. `temp` / `TempPass123!` | This account is deleted outright during restore |
| Recovery key | The app generates and displays one — click through/acknowledge it | Discarded; your real recovery key (tied to your real admin account) comes back with the restore |
| Confirm recovery key | Confirm as prompted | This is the step that actually flips the system into "initialized" and unlocks login — **don't skip it** |

### D4. Log in with the temporary account

Use the temporary username/password from D3. You should land in an empty, freshly-initialized WEBSTUDIO IMS — no inventory, no sales, no old users. That's expected; you haven't restored anything yet.

---

## Part E — Restore your real data

### E1. Find your latest good backup

On the copied old drive, open `D:\WEBSTUDIO-IMS\backups\` (or wherever you have it — an off-site USB/NAS copy is even better if the on-server copy is suspect). Files are named:

```text
webstudio-backup-YYYYMMDD-HHMMSS.tar.gz
```

Sort by name (the timestamp sorts naturally) and take the **newest** file — that's the freshest snapshot of your business.

### E2. Copy it to the new server

Copy that `.tar.gz` into the new install's backup folder:

```text
D:\WEBSTUDIO-IMS\backups\
```

It costs nothing to also bring the two or three backups before it, as a fallback in case the newest one turns out damaged or incomplete.

### E3. Open the Restore Center

In the desktop app, logged in as the temporary admin from Part D: `Settings → Backup → Restore Center`. The archive you just copied in should already appear in the list. If it doesn't show up, use **Import backup file** and browse to it directly.

### E4. Validate, then preview

- Select the archive. The system checks archive integrity, checksum, and schema compatibility automatically.
- Click **Preview** — this shows you the manifest: company name, backup date, inventory/sales/user counts. This is your chance to confirm you picked the right file before anything is touched.

### E5. Restore — full scope

Choose **entire database** as the restore scope (this is the scope you want — it's the one that brings back everything described in [Section 1](#1-what-fully-recovered-actually-means)). Confirm the warning dialog.

Behind the scenes, the system automatically creates an **emergency backup** of the current (temporary) state before it does anything destructive — so if something goes wrong mid-restore, there's a rollback point. You don't need to do anything for this to happen; it's automatic for full-database restores.

Wait for it to finish. For a normal shop-sized database this takes well under a minute; larger catalogs with many years of sales history may take a few minutes.

<a id="e5a-known-failure"></a>
> **Known issue (present in server builds up to and including v1.0.3 — check whether your installed server predates the fix noted in the Appendix):** the Restore Center can fail with a generic **"Restore failed. Your emergency backup may still be available for rollback."** message that gives no real reason, and afterward the app may even show the **Setup Wizard again** instead of a login screen. This is two compounding bugs, not data loss:
>
> 1. If your system has any **custom access roles** (`Settings → Users → Roles`), the backup archive contains a circular reference between the `users` and `custom_access_roles` tables that a plain data-only restore cannot load in any single order — it fails partway through, before all your data is back.
> 2. Separately, the code path that records *why* a restore failed can itself crash (a stale reference to whichever admin account clicked "Restore" — including a temporary Setup Wizard account, which is often gone by the time this runs). That crash overwrites and hides the real error, leaving you with the unhelpful generic message and no clue what actually happened.
>
> Both are fixed in the source as of **2026-08-16**, but the fix only takes effect once a server build that includes it is installed — see the Appendix. **If you hit this exact symptom on a server that predates the fix, skip to [E8 — Manual restore fallback](#e8-manual-restore-fallback) below** rather than repeatedly retrying through the UI; retrying alone won't get past bug #1.

### E6. Restart the WEBSTUDIO Server service

The restore explicitly requires a service restart afterward:

```powershell
Restart-Service "WEBSTUDIO Server"
```

### E7. Log back in — with your OLD credentials

The temporary admin account no longer exists — it was deleted by the restore, along with its login session. Log out (or you'll likely already be logged out automatically), and log back in with your **real, old** Main Admin username and password. Both came back exactly as they were, because the `users` table was part of the restored data.

If you don't remember the old password, that's fine — it's the same password it always was; nothing about the recovery changes it. If you've genuinely forgotten it, that's a separate password-recovery flow (uses your old recovery key), not something this runbook needs to solve.

<a id="e8-manual-restore-fallback"></a>
### E8. Manual restore fallback (if Restore Center fails with the generic error from E5)

This bypasses the app entirely and talks to PostgreSQL directly with `psql`. It's more hands-on than the normal flow, but it's the same operation the app performs internally, done step by step so any real error is visible instead of hidden. **Run every command as Administrator, on the server.**

1. **Stop the service** so nothing else touches the database while you work:
   ```powershell
   Stop-Service "WEBSTUDIO Server"
   ```

2. **Extract the backup archive** (the one from E1/E2 — adjust the filename):
   ```powershell
   cd D:\WEBSTUDIO-IMS\backups
   New-Item -ItemType Directory -Force -Path manual-restore-check | Out-Null
   tar -xzf "webstudio-backup-YYYYMMDD-HHMMSS.tar.gz" -C manual-restore-check
   ```

3. **Write a clean truncate script** — this empties every table in the schema, the same first step the app itself takes before loading a backup:
   ```powershell
   @'
   DO $do$
   DECLARE
       r RECORD;
   BEGIN
       FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'webstudio' AND tablename <> 'alembic_version')
       LOOP
           EXECUTE 'TRUNCATE TABLE webstudio.' || quote_ident(r.tablename) || ' RESTART IDENTITY CASCADE';
       END LOOP;
   END
   $do$;
   '@ | Set-Content -Path "D:\WEBSTUDIO-IMS\backups\truncate-all.sql" -Encoding ASCII
   ```
   Use `-Encoding ASCII`, not `utf8` — PowerShell's `utf8` writes an invisible byte-order-mark that `psql` can't parse, producing a confusing `syntax error at or near "ï»¿DO"`.

4. **Run the truncate** (adjust the PostgreSQL version in the path if yours differs):
   ```powershell
   $env:PGPASSWORD = "your_webstudio_app_password"
   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 127.0.0.1 -p 5432 -U webstudio_app -d webstudio -f "D:\WEBSTUDIO-IMS\backups\truncate-all.sql"
   ```

5. **If your system has any custom access roles**, drop the constraint that causes the circular-reference failure described in E5a — otherwise skip straight to step 6:
   ```powershell
   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 127.0.0.1 -p 5432 -U webstudio_app -d webstudio -c "ALTER TABLE webstudio.users DROP CONSTRAINT fk_users_custom_access_role;"
   ```

6. **Run the actual restore, watching live:**
   ```powershell
   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 127.0.0.1 -p 5432 -U webstudio_app -v ON_ERROR_STOP=1 -d webstudio -f "manual-restore-check\database.sql"
   ```
   - **All `COPY N` lines with no `ERROR` anywhere, ending in a handful of `setval` blocks** → it worked. The `setval` lines are `pg_dump` resetting ID sequences to match the restored data — normal, not errors.
   - **It stops with an `ERROR:` line** → that's the real reason, unmasked. If it names a different foreign key than step 5's, that table has the same kind of ordering problem; drop the named constraint the same way, re-run step 4 (truncate again — this attempt partially loaded data), then retry step 6. Send the exact error to WEBSTUDIO engineering if it's not one of the two known issues in E5a.

7. **If you dropped a constraint in step 5, put it back now** — only after step 6 finished completely clean:
   ```powershell
   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 127.0.0.1 -p 5432 -U webstudio_app -d webstudio -c "ALTER TABLE webstudio.users ADD CONSTRAINT fk_users_custom_access_role FOREIGN KEY (custom_access_role_id) REFERENCES webstudio.custom_access_roles(id) ON DELETE SET NULL;"
   ```

8. **Copy the managed asset files back** — the manual restore only touches the database. Product images, brand logos, and uploads live as plain files inside the backup archive and need copying separately:
   ```powershell
   $src = "D:\WEBSTUDIO-IMS\backups\manual-restore-check\assets"
   $dst = "D:\WEBSTUDIO-IMS\assets"
   foreach ($sub in "brand-logos","product-images","company","uploads") {
       $s = Join-Path $src $sub
       if (Test-Path $s) {
           New-Item -ItemType Directory -Force -Path (Join-Path $dst $sub) | Out-Null
           Copy-Item "$s\*" (Join-Path $dst $sub) -Force -Recurse
       }
   }
   ```

9. **Start the service and continue at E6** (restart) **and E7** (log in with your real old credentials) above.

10. **Once you're confirmed back in with real data**, run a fresh manual backup immediately (`Settings → Backup → Run manual backup`) to establish a new known-good baseline, then clean up:
    ```powershell
    Remove-Item -Recurse -Force "D:\WEBSTUDIO-IMS\backups\manual-restore-check"
    Remove-Item "D:\WEBSTUDIO-IMS\backups\truncate-all.sql"
    ```

There will be no Restore Center history entry for a manual restore performed this way — that's cosmetic, not a data problem.

---

## Part F — Firewall and network reachability

This section explains **exactly what talks to what** on your network, so when something doesn't connect, you know which of these four things to check.

### F1. The three things that need to reach the server

| Traffic | Protocol / Port | Direction | Purpose |
|---|---|---|---|
| API | TCP **8000** | Client → Server | Desktop app, mobile app, browser health checks |
| Auto-discovery | UDP **5353** (mDNS) | Bidirectional, LAN only | Lets desktop/mobile apps find the server automatically instead of you typing the IP everywhere |
| PostgreSQL | TCP **5432** | — | **Server-local only.** Never expose this to the LAN, ever. |
| Tally XML | TCP **9000** (typical) | **Server → Tally PC** (outbound from the server, inbound on the Tally laptop) | The server calls out to Tally, not the other way around — see Part H |

### F2. Run the firewall script

PowerShell, as Administrator, on the server, adjusting the subnet to match your LAN:

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\configure-firewall.ps1 -ApiPort 8000 -Subnet 192.168.29.0/24
```

This opens exactly TCP 8000 and UDP 5353, scoped to your LAN subnet — nothing wider.

### F3. Validate

```powershell
.\validate-production-network.ps1 -ApiPort 8000
```

### F4. Test reachability from an actual client

From a staff laptop's browser, on the shop Wi-Fi/LAN:

```text
http://192.168.29.100:8000/health/live
```

Must return `OK`. Test this from every floor/AP your shop has — if it works from one location but not another, that's an access-point isolation problem (see F6), not a WEBSTUDIO problem.

### F5. What auto-discovery actually is

The desktop and mobile apps don't strictly need you to type an IP address. The backend advertises itself on the LAN via mDNS/Bonjour under the service name `_webstudio-ims._tcp.local.`, broadcasting its name, port, and version. Clients on the same subnet can "browse" for this and connect automatically — this is what's happening when the mobile app's Connect screen says it's "searching."

Auto-discovery **requires**:
- Client and server on the same LAN subnet
- UDP 5353 open both directions (handled by F2)
- No AP client isolation between them (next section)

If any of those aren't true, discovery silently fails and clients fall back to whatever URL was typed in manually — which is exactly why every client screen also has a manual "Server address" field. It always works as a fallback even when discovery doesn't.

### F6. The most common reachability killer: AP client isolation

If your shop has more than one Wi-Fi access point (a router plus a repeater/extender, common in two-floor shops), each AP typically has a setting called **client isolation** or **AP isolation**, meant to stop devices on a guest network from seeing each other. If it's on, devices connected to different APs — even on the same SSID and same subnet — cannot reach each other at all, and no firewall rule fixes that; it's blocked before it ever reaches the server's network stack.

- Turn **client/AP isolation off** on every access point serving WEBSTUDIO clients.
- Never use a **guest Wi-Fi network** for WEBSTUDIO devices — guest networks almost always have isolation on by design and usually block mDNS entirely, even when isolation is nominally off.
- If you can't guarantee isolation is off everywhere (e.g. enterprise Wi-Fi you don't control), fall back to a fixed internal DNS hostname or manually-entered IP on every client instead of relying on auto-discovery.

---

## Part G — Reconnecting desktop apps and phones

### G1. If the new server kept the same IP (Part A4) — nothing to do

Every staff desktop app and phone reconnects automatically. This is the entire reason Part A4 exists — do it, and this section is a no-op.

### G2. If the IP changed

**Desktop app**, each staff laptop: the app will sit on "Connecting to server" until it can reach the configured address. Reinstalling isn't necessary — but if there's no in-app way to change the server address on your build, uninstall and reinstall `WEBSTUDIO Desktop Setup.exe` and enter the new URL when prompted.

**Phone (Android)**: `Settings → API server` (after login) or the **Change** option on the Connect screen, then enter:

```text
http://<new-server-ip>:8000
```

Never use `10.0.2.2` on a real phone — that address only works inside the Android emulator and will hang forever on a physical device.

### G3. First install on a phone that's never connected before

1. Copy `WEBSTUDIO IMS.apk` to the phone and install it (allow "unknown apps" if Android asks).
2. Join the shop Wi-Fi — the **same network as the server**, not mobile data.
3. Open the app. It starts automatic discovery (mDNS + LAN scan, see F5). If the server is found, it connects on its own.
4. If discovery doesn't find it (or you'd rather not wait), the **Server address** field is visible immediately — type the URL and tap **Connect to server** any time, even mid-scan.

---

## Part H — Reconnecting Tally

This is the part with the most moving pieces, so it gets its own full walkthrough — from what the Tally laptop needs on the network side, through to the exact settings inside Tally itself, and how to prove the connection works before you rely on it.

Two machines are involved: the **WEBSTUDIO server** (which initiates the connection) and the **Tally PC** (which has to be sitting there, listening, ready to answer).

### H1. The direction of the connection — get this right first

The WEBSTUDIO server **calls out to** the Tally PC. The Tally PC never calls the server. This single fact explains almost every rule below:

- The Tally PC needs an **inbound** firewall rule for port 9000.
- The WEBSTUDIO server needs **no inbound rule for Tally at all** — it only makes outbound calls, which Windows allows by default.
- The Tally PC does **not** need to be on the same floor, or even the same access point, as the server — only on the **same subnet** (or a subnet the server can route to).
- Nothing about Tally connectivity depends on the desktop or mobile apps — they never talk to Tally directly. They only ever read a sync-status summary from the server.

### H2. Network compatibility the Tally PC needs, before you touch Tally's own settings

Get these right first — Tally's own XML settings are pointless if the network underneath them is wrong.

| Requirement | Why | How to check |
|---|---|---|
| Same LAN subnet as the WEBSTUDIO server (or a subnet the server's router can route to) | The server resolves the Tally PC's hostname and opens a raw TCP connection to it — it has to be network-reachable, not just "on Wi-Fi somewhere" | On the Tally PC: `ipconfig` — compare the network portion of the IP and the gateway against the server's |
| Windows network profile set to **Private**, not Public | A Public profile blocks the inbound firewall rule from H5 even if it exists | `Settings → Network & Internet → [your connection] → Network profile type` |
| No **AP / client isolation** on whichever access point the Tally PC is connected to | Isolation blocks LAN traffic between devices on the same Wi-Fi even though they're technically on the same subnet — this looks identical to a firewall problem but no firewall rule fixes it | See Part F6 — same rule applies here, on whichever floor/AP the Tally PC is using |
| Not on a **guest Wi-Fi network** | Guest networks almost always isolate devices from each other by design, and frequently block the TCP connection outright | Confirm the Tally PC is joined to your normal staff SSID, not a guest one |
| A stable Windows **computer name** (hostname) | WEBSTUDIO is configured to reach Tally by hostname, not IP, specifically so DHCP re-assigning the IP later doesn't break the connection | `hostname` (see H6) |
| Only one antivirus/firewall product active | A second, third-party firewall (McAfee, Norton, Avast, etc.) enforces its own rules independently of Windows Firewall — opening the port in Windows Firewall alone won't help if another product is also blocking it | Check for any non-Microsoft security suite installed on the Tally PC, and open TCP 9000 there too if one exists |

None of this depends on which exact Tally product or version you run (Tally ERP 9 or Tally Prime) — it's the same LAN requirement either way, because WEBSTUDIO talks to Tally over plain TCP/XML, not through any Tally-specific network layer.

### H3. Configure Tally itself to serve XML on port 9000

1. Install Tally, and open it with your **company loaded** — not just sitting at the gateway/company-selection screen. Settings applied without a company open don't always stick.
2. Open **Gateway of Tally → F12 → Advanced Configuration**, and set:

   | Setting | Value |
   |---|---|
   | Tally acting as | **Both** or **Server** |
   | Enable ODBC / XML Server | **Yes** |
   | Port | **9000** |

   (Menu wording differs slightly between Tally ERP 9 and Tally Prime, but both expose this under **F12 → Advanced Configuration** from the company screen.)

3. **Quit Tally completely** — close it from the Windows system tray as well as the main window, not just the window — then reopen it and re-open the company. XML/ODBC settings from F12 do not reliably take effect without a full restart.

4. **Fallback — edit `tally.ini` directly**, if the F12 screen doesn't stick or isn't available in your Tally edition. It's a plain text file in Tally's install folder (commonly `C:\Program Files\TallyPrime\tally.ini` or `C:\Tally.ERP9\tally.ini`, depending on which product and version you have — locate it if the path differs on your machine). Open it in Notepad and make sure these lines are present:

   ```ini
   EnableODBCServer=Yes
   ODBCServerPort=9000
   ```

   Save, then fully restart Tally (tray icon included).

5. Note the **exact company name** as it appears in Tally's company list (**Gateway of Tally**, or **F3 → Select Company**). Tally Prime often appends date-range suffixes, e.g.:

   ```text
   WEBSTUDIO - (from 1-Apr-2022) - (from 1-Apr-25) - (from 1-Apr-26)
   ```

   You need the **full string, exactly**, including those suffixes — not just `WEBSTUDIO`. Copy it rather than retyping it if you can.

### H4. Confirm the XML server is actually listening — on the Tally PC itself

Before involving the server at all, prove Tally is serving XML locally. PowerShell **on the Tally PC**:

```powershell
netstat -an | findstr 9000
Test-NetConnection localhost -Port 9000
```

Expect:

```text
TCP    0.0.0.0:9000           0.0.0.0:0              LISTENING
...
TcpTestSucceeded : True
```

If `netstat` shows **nothing at all** for port 9000, the XML server isn't running — go back to H3, and don't move on until this local test passes. Testing against the network before this passes locally just makes debugging harder.

### H5. Open the port on the Tally PC's firewall

PowerShell, as Administrator, **on the Tally PC** (not the server):

```powershell
New-NetFirewallRule -DisplayName "Tally XML 9000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9000 -Profile Private
```

Equivalent GUI path, if you'd rather not use PowerShell: **Windows Defender Firewall with Advanced Security → Inbound Rules → New Rule → Port → TCP → Specific local port 9000 → Allow the connection → Private → name it.**

Verify the rule actually registered:

```powershell
Get-NetFirewallRule -DisplayName "Tally XML 9000" | Format-Table DisplayName, Enabled, Direction, Action, Profile
```

Remember H2's warning: if the Tally PC has a third-party antivirus suite with its own firewall, add the same allow-rule there too — Windows Firewall alone won't be enough on that machine.

### H6. Find the Tally PC's hostname

On the Tally PC:

```powershell
hostname
```

Use this **exact value** — not an IP address — in H8. IPs handed out by DHCP change when a laptop reconnects to Wi-Fi or moves rooms; the hostname doesn't, which is the entire reason WEBSTUDIO is configured this way instead of with a fixed IP.

To check or change the name itself: `Settings → System → About → Rename this PC` (requires a reboot to take effect).

### H7. Test reachability from the server's side, before configuring WEBSTUDIO

This confirms the network path end-to-end, independent of anything inside the WEBSTUDIO app. PowerShell **on the WEBSTUDIO server**, substituting the Tally PC's hostname from H6:

```powershell
Test-NetConnection TALLY-LAPTOP -Port 9000
```

`TcpTestSucceeded : True` means the network path (routing, subnet, firewall rule, AP isolation — everything in H1–H5) is genuinely fine, and any remaining problem is inside the WEBSTUDIO settings screen itself, not the network. If this fails, don't bother configuring WEBSTUDIO yet — go back through H2–H6 in order.

### H8. Point WEBSTUDIO at the Tally PC

In the desktop app (as Main Admin): `Settings → Tally`.

| Field | Enter | Notes |
|---|---|---|
| Enable automatic Tally synchronization | Checked | Turn on only once H1–H7 are done |
| Tally workstation address (Host / IP) | The Tally PC's hostname from H6 (e.g. `TALLY-LAPTOP`) | Do **not** leave this as `127.0.0.1` unless Tally genuinely runs on the same PC as the server — leaving the default here is the single most common misconfiguration |
| Port | `9000` | Or whatever you set in H3 |
| Company name in Tally | The exact full string from H3, step 5 | A near-miss here is the classic cause of "sync succeeded, 0 imported" — it isn't a connection failure, it's a name mismatch |
| Polling interval | `300` seconds (default) | How often the server checks Tally for new invoices; valid range is 60–3600 |

Save, then click **Test connection**. It runs three staged checks in order, and the result tells you exactly which one failed rather than a generic error:

1. **Host Resolution** — can the server's DNS/mDNS resolve the hostname you entered at all? (timed out after a few seconds if not)
2. **TCP Connection** — can it open a socket to port 9000? (times out after ~5 seconds)
3. **XML Server** — does Tally answer with a valid XML response once connected? (times out after ~15 seconds)

A full test can therefore take up to about 20 seconds in the worst case before failing — that's normal, not a hang.

| If the test says | It means | Fix |
|---|---|---|
| "Tally workstation is currently offline" | Host resolves but nothing answers | Power on the Tally PC; confirm Tally is actually open with the company loaded |
| "Unable to connect to the configured Tally workstation" | TCP connection refused/blocked | Re-check H5 (firewall, including any second/third-party firewall) and H7 |
| "The configured host could not be resolved" | Hostname lookup failed | Re-verify H6's exact spelling; try appending `.local`; as a last resort use the current IP temporarily |
| "Tally XML Server not enabled" | TCP connects, but Tally isn't serving XML | Redo H3 — XML Server has to be explicitly enabled and Tally fully restarted |
| Sync reports success but 0 checked / 0 imported | Connection is fine, company name isn't matching | Re-copy the exact company name from Tally's company list (H3, step 5) |

**If Tally is offline or unreachable, WEBSTUDIO keeps working normally** — inventory, sales, reports, users, backups, mobile, and desktop are all unaffected. Only the Tally sync itself pauses until the connection comes back; nothing else degrades, and no manual re-import is needed once it does.

For a live machine-readable status at any time (handy for quick checks without opening the desktop app), an authenticated admin can call:

```http
GET /api/v1/integrations/tally/health
```

which returns the same staged status as a JSON object — including `status` (one of `online`, `offline`, `connected`, `xml_error`, `configuration_error`), the resolved IP, and the last successful sync/connection timestamps.

There's also a scripted version of the full check, run on the server:

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\validate-production-tally.ps1 -ApiBaseUrl "http://127.0.0.1:8000" -BearerToken "<admin-jwt>" -TallyHost "TALLY-LAPTOP"
```

### H9. If the Tally PC moves between Wi-Fi networks or floors

Because you configured it by **hostname**, not IP, this should just work — reconnect Tally to whatever Wi-Fi it's using, confirm its network profile is **Private**, and re-run **Test connection** to be sure. If it fails after a move, it's almost always AP client isolation (Part F6 / H2) on the network it just joined, not a Tally setting.

### H10. Quick reference — everything to run on the Tally laptop, start to finish

Everything above explained in full; this is the condensed version for when you already know what you're doing and just need the commands. **Run on the Tally laptop itself, PowerShell as Administrator**, in this order:

```powershell
# 1. Identity — confirm subnet matches the server's, and note the exact hostname
ipconfig
hostname

# 2. Network profile — must be Private, not Public (H2)
Get-NetConnectionProfile
# If it shows "Public" for the adapter you're using, set it:
Set-NetConnectionProfile -InterfaceAlias "<adapter name from above>" -NetworkCategory Private

# 3. Confirm Tally's XML server is actually listening locally (H4) — do this
#    AFTER enabling XML Server in Tally itself: Gateway of Tally -> F12 ->
#    Advanced Configuration -> Enable ODBC/XML Server: Yes, Port: 9000,
#    then fully quit and reopen Tally (tray icon too).
netstat -an | findstr 9000
Test-NetConnection localhost -Port 9000

# 4. Open the firewall for the server to reach in (H5)
New-NetFirewallRule -DisplayName "Tally XML 9000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9000 -Profile Private
Get-NetFirewallRule -DisplayName "Tally XML 9000" | Format-Table DisplayName, Enabled, Direction, Action, Profile

# 5. If this machine has a non-Microsoft antivirus/firewall product (McAfee,
#    Norton, Avast, etc.), open TCP 9000 there too — Windows Firewall alone
#    is not enough on those machines (H2).
```

**What this does *not* cover, because it isn't a Tally-laptop command:** the actual "Tally workstation address / port / company name" fields go into the **WEBSTUDIO desktop app**, on the server side or any admin PC — `Settings → Tally` (H8) — not on the Tally laptop itself. The Tally laptop's only job is to sit there with Tally open, XML Server enabled, and port 9000 reachable; the WEBSTUDIO server does the connecting.

**Sanity check before you leave the Tally laptop:** step 3's two commands should both come back positive (`LISTENING` in the `netstat` output, `TcpTestSucceeded : True`) *before* you go configure anything in WEBSTUDIO. If they don't, nothing on the server side will work either — fix Tally's own XML Server setting first (H3).

---

## Part I — Verification checklist

Don't call this done because login worked. Confirm the data is real.

- [ ] Main Admin login succeeds with the **old**, real credentials (not the temporary Part D account)
- [ ] Inventory count roughly matches what you remember from before the outage
- [ ] A specific sale you remember making is visible in sales history
- [ ] Product images load — not broken icons or placeholders
- [ ] Staff user accounts from before the outage are present in `Settings → Users`, with their original roles
- [ ] Company profile, branding/logo, and any custom settings look correct — not the temporary "Temp Setup" values from Part D
- [ ] `Settings → Tally → Test connection` succeeds once the Tally PC is on the network (Part H)
- [ ] A manual backup runs successfully: `Settings → Backup → Run manual backup` — proves the new server can protect itself going forward, not just that it received old data
- [ ] Reboot the new server once, then confirm both services come back up on their own:
  ```powershell
  Get-Service "WEBSTUDIO Server", postgresql-x64-18
  ```
- [ ] From a laptop and a phone, each on the shop network: apps connect without you typing an IP anywhere (proves auto-discovery is working, not just that a manually-typed address happens to work)

Optional automated summary:

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\validate-production-backup.ps1
```

Once every box above is checked, the old server's copied `D:\` folder can be moved to cold storage (an external drive, kept but not touched) rather than left as an active fallback on the new machine.

**Do not delete the old `D:\` folder before every box above is checked.** It's your only way back if a restore needs to be redone.

---

## Part J — Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Desktop app stuck on "Connecting to server" | Server not actually reachable yet | Confirm Part C5 and Part F4 (`/health/live`) succeed from a browser first, before blaming the desktop app |
| `DATABASE_URL` in `.env` still contains `CHANGE_ME` | Post-install password prompt was missed | Run `finalize-server-setup.ps1` (Part C4) |
| `password authentication failed` during install | Used the `postgres` superuser password instead of `webstudio_app`'s | Re-run with the correct password from Part B3 |
| Restore Center doesn't list the copied backup | File copied to the wrong path, or copy was interrupted | Confirm the file is directly inside `D:\WEBSTUDIO-IMS\backups\` (not a subfolder); re-copy it; or use **Import backup file** to browse to it directly |
| Restore fails checksum validation | Partial/corrupted copy from the old drive | Re-copy the file; if it still fails, fall back to the next-newest backup in the folder |
| Restore reports a schema mismatch | New install's database schema is ahead of the backup's | Confirm the installer's migrations ran fully in Part C3; re-run the migration step, then retry the restore |
| Restore verification fails after completing | Rare, but the system prepared for it | Use the **rollback** option in Restore Center — it automatically targets the emergency backup created in Part E5. After rolling back, retry with an older archive |
| Restore fails with a generic **"Restore failed. Your emergency backup may still be available for rollback."** and no real reason | Known issue on server builds predating the fix in the Appendix — see [E5a](#e5a-known-failure) | Go straight to [E8 — Manual restore fallback](#e8-manual-restore-fallback); retrying the same way through the UI will not get further |
| App shows the **Setup Wizard again** after a restore attempt, instead of a login screen | The restore did not actually finish — `system_settings` (which holds `system_initialized`) never got reloaded | Same as above — this confirms E5a, not a fresh-install glitch. Do not create a new company/admin in the wizard; go to E8 |
| Manual `psql -f truncate-all.sql` fails with `syntax error at or near "ï»¿DO"` | The `.sql` file was saved with a UTF-8 byte-order-mark that `psql` can't parse | Re-save with `Set-Content -Encoding ASCII` instead of `-Encoding utf8` (see E8 step 3) — nothing executed, safe to just re-save and retry |
| Manual restore (E8) stops with `insert or update on table "users" violates foreign key constraint "fk_users_custom_access_role"` | The circular reference between `users` and `custom_access_roles` described in E5a | Follow E8 steps 5–7: drop the named constraint, re-truncate, retry, then re-add the constraint once the restore is fully clean |
| Backup fails with `[WinError 2]` | PostgreSQL's `pg_dump` isn't on the service's PATH | Re-run `finalize-server-setup.ps1` — it fixes this specifically |
| `D:\WEBSTUDIO-IMS\backups\` from the old drive is empty or missing | Old server may not have had automatic backups enabled, or you only copied part of the drive | Check for an **off-site copy** (USB/NAS) — production guidance is to copy backups off the server weekly for exactly this scenario. If none exists, the most recent state you can recover is whatever's in the copied database files directly, which is a materially harder recovery — worth getting a second opinion before proceeding |
| Everything reachable on one floor, nothing on another | AP client isolation between access points | See Part F6 |
| Tally test fails after working fine before | Tally PC's IP was entered instead of its hostname, and DHCP changed it | Switch to hostname (Part H6, H8) so this stops recurring |
| Phone shows `10.0.2.2` and won't connect | That's the Android-emulator-only address, leftover from a dev build | Manually enter the real server address in the Connect screen |

---

## Appendix — your site's documented values

These are the values recorded in this project's own setup documentation as of the last time it was updated. **Confirm each one against your actual router and server before relying on it** — networks drift over time.

| Item | Documented value |
|---|---|
| Server computer name | `WEBSTUDIO-SERVER` |
| Server IP (reserved) | `192.168.29.100` |
| Router admin page | `http://192.168.29.1` |
| Install path | `D:\WEBSTUDIO-IMS` |
| PostgreSQL service | `postgresql-x64-18` (PostgreSQL 18) |
| Application DB / role | `webstudio` / `webstudio_app` |
| API port | `8000` |
| mDNS discovery port | UDP `5353` |
| Tally XML port | `9000` |
| Tally PC hostname | `TALLY-LAPTOP` |
| GitHub releases | `https://github.com/Smarthsingh/WEBSTUDIO-IMS/releases` |

### Known issues in the backup/restore pipeline

Found and fixed in source on **2026-08-16**, during a real recovery. **The fix is not active on any server until a build containing it is installed** — this section exists so you know whether your server still needs the manual workaround in E8, or can rely on the Restore Center directly.

| Issue | Root cause | Fix |
|---|---|---|
| Data-only restore fails partway if the system has any custom access roles | `users.custom_access_role_id` and `custom_access_roles.created_by_user_id` form a circular foreign-key reference; no single `COPY` order satisfies both, so a plain data-only restore always fails at that point | `services/backup_engine.py` now dumps with `pg_dump --disable-triggers`, which suspends FK-check triggers during load so ordering stops mattering. New backups created after upgrading no longer need the E8 workaround. |
| The real restore error gets replaced by a confusing foreign-key crash | The restore's own error-handling tried to record "who ran this restore" using an actor id captured *before* the restore started — but a full restore replaces the `users` table, so that id may no longer exist by the time it's written, and that failure wasn't isolated from the original error | `restore_run_repository.py` now verifies the actor still exists before using it (falls back to a null actor id, keeping the display name); `restore_engine.py`'s error handling now isolates each bookkeeping step so a secondary failure can never again hide the original one |

**To check if your server has the fix:** look at the "server install fixes" note in your release notes, or just attempt a restore — if it fails with a specific, readable error instead of the generic message, and doesn't drop you back to the Setup Wizard, you have it.

**Until you're on a build with the fix:** if your system uses custom access roles (`Settings → Users → Roles` has anything beyond the built-in ones), assume any full restore will need the E8 manual procedure, and budget time for it rather than discovering it live during an actual outage.

### Test your restore before you need it

Everything in this document was written the hard way — during a real outage, discovering the Restore Center's generic error message for the first time. The single best way to not repeat that: run a **restore drill** on a spare machine (or a VM) before it's an emergency. Take your most recent backup, follow Parts A–E on hardware nobody depends on, and see what breaks while it's safe to fail. `docs/milestones/m14/RESTORE_CHECKLIST.md` has a formal version of this (section F, "Annual restore drill") — worth actually doing, not just having documented.

Deeper source material, if you need more than this document covers:

- `docs/milestones/m14/DISASTER_RECOVERY_GUIDE.md` — the outage/recovery scenarios this runbook is built from
- `docs/milestones/m14/RESTORE_CHECKLIST.md` — formal sign-off checklist version of Part I
- `docs/milestones/m14/BACKUP_MANUAL.md` — day-to-day backup operation, retention, off-site copies
- `docs/milestones/m14/FIRST_TIME_SETUP_MASTER_GUIDE.md` — the original full office setup guide this runbook's network sections are drawn from
- `docs/internal/BACKUP_RESTORE.md` — technical format of the backup archive itself
- `docs/network/NETWORK_REQUIREMENTS.md` — the underlying network topology rules
- `docs/integrations/tally-erp9/troubleshooting.md` — Tally connection-test internals
- `docs/milestones/m14/TALLY_PRODUCTION_GUIDE.md` — production Tally configuration reference, sync behavior, recovery scenarios
- `docs/milestones/m14/TALLY_VALIDATION_CHECKLIST.md` — formal Tally sign-off checklist (Part H draws its structure from this)
- `docs/milestones/m12/TALLY_CONNECTIVITY_HARDENING_REPORT.md` — the Wi-Fi roaming / hostname-over-IP design rationale behind Part H
- `apps/backend/src/webstudio_backend/services/restore_engine.py` and `backup_completeness.py` — the actual code this runbook's Section 1 claims are verified against
- `apps/backend/src/webstudio_backend/integrations/tally/connectivity.py` — the actual staged Host Resolution → TCP → XML probe logic and timeout values referenced in Part H8
