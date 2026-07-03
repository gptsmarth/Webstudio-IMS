---
Title: Administrator Manual — WEBSTUDIO IMS
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14H
Audience: Main Admin, IT administrators, WEBSTUDIO engineers
Related Documents:
  - docs/milestones/m14/OPERATIONS_MANUAL.md
  - docs/milestones/m14/MAINTENANCE_GUIDE.md
  - docs/milestones/m14/INSTALLATION_MANUAL.md
  - docs/milestones/m14/PRODUCTION_COMMISSIONING_GUIDE.md
---

# Administrator Manual (M14H)

Authoritative administrator reference for **WEBSTUDIO IMS Version 1.0.0** on a dedicated **Windows 11 Pro** server with LAN-connected desktop and mobile clients.

| Companion manual | Scope |
|------------------|-------|
| [Operations Manual](OPERATIONS_MANUAL.md) | Updates, deployment, rollback, backups, Tally operations, incident response |
| [Maintenance Guide](MAINTENANCE_GUIDE.md) | Schedules, preventive care, deep troubleshooting |

---

## 1. Administrator roles

| Role | Responsibilities |
|------|------------------|
| **Main Admin** | System setup wizard, recovery key, user management, backup approval, deployment sign-off |
| **Administrator (`admin`)** | Day-to-day settings, Tally, backups, reports — no Main Admin exclusives |
| **IT operator** | Server install, Windows Service, firewall, PostgreSQL, release upgrades |
| **WEBSTUDIO engineer** | Commissioning validation, rollback assistance, disaster recovery drills |

---

## 2. Installation

Production installation uses packaged artifacts from the **stable** release bundle. No source builds on the customer server.

### 2.1 Prerequisites

| Item | Requirement |
|------|-------------|
| Server OS | Windows 11 Pro (patched, NTP enabled) |
| Install root | `D:\WEBSTUDIO-IMS` (default) |
| Database | PostgreSQL 16.x (`postgresql-x64-16` service) |
| Network | Static IP or DHCP reservation on store LAN |
| Artifacts | `WEBSTUDIO Server Setup.exe` + checksum verification |

### 2.2 Installation sequence (summary)

| Step | Action | Validation |
|------|--------|------------|
| 1 | Prepare Windows server PC | Hostname, time zone, disk ≥20% free |
| 2 | Install PostgreSQL 16 | `Get-Service postgresql-x64-16` → Running |
| 3 | Run **WEBSTUDIO Server Setup.exe** (Administrator) | `apps\backend`, `venv`, `config\env\.env` exist |
| 4 | Register **WEBSTUDIO Server** Windows Service | `Get-Service "WEBSTUDIO Server"` → Running |
| 5 | Apply database migrations | `alembic upgrade head` (installer runs automatically) |
| 6 | Configure firewall | TCP **8000** inbound from LAN subnet only |
| 7 | Start service | `GET /health/ready` → database ok |
| 8 | Complete Setup Wizard (desktop) | Main Admin account + recovery key |
| 9 | Run Office Deployment Wizard | Discovery URLs documented |
| 10 | Deploy desktop/mobile clients | See [DESKTOP_DEPLOYMENT_GUIDE.md](DESKTOP_DEPLOYMENT_GUIDE.md) |

**Full procedure:** [INSTALLATION_MANUAL.md](INSTALLATION_MANUAL.md)  
**Post-install commissioning:** [PRODUCTION_COMMISSIONING_GUIDE.md](PRODUCTION_COMMISSIONING_GUIDE.md)  
**First-start checklist:** [FIRST_STARTUP_CHECKLIST.md](FIRST_STARTUP_CHECKLIST.md)

### 2.3 Install paths

| Path | Purpose |
|------|---------|
| `D:\WEBSTUDIO-IMS\apps\backend` | API application |
| `D:\WEBSTUDIO-IMS\config\env\.env` | Production environment |
| `D:\WEBSTUDIO-IMS\backups` | Default backup folder |
| `D:\WEBSTUDIO-IMS\logs` | API and service logs |
| `D:\WEBSTUDIO-IMS\infra\windows` | PowerShell operator scripts |

---

## 3. Configuration

### 3.1 Environment file

Primary file: `config\env\.env` (generated from template on first install).

| Variable | Production value | Notes |
|----------|------------------|-------|
| `APP_ENV` | `production` | Enables startup validation |
| `JWT_SECRET` | ≥ 32 random bytes | **Required** — server refuses weak default |
| `API_HOST` | `0.0.0.0` | Accept LAN clients |
| `API_PORT` | `8000` | Match firewall rule |
| `DATABASE_URL` | `postgresql+asyncpg://…@localhost:5432/…` | Localhost only |
| `MDNS_ENABLED` | `true` | Client auto-discovery |
| `WEBSTUDIO_DISCOVERY_CANDIDATES` | Server IP or hostname | Fallback when mDNS blocked |
| `TLS_CERT_PATH` / `TLS_KEY_PATH` | Optional | HTTPS on LAN |
| `WEBSTUDIO_BACKUP_SCHEDULER` | `1` | Enable automatic backups |
| `WEBSTUDIO_DATA_ROOT` | Install root | Data, backups, exports |

**Reference:** [m12a/PRODUCTION_ENVIRONMENT_CONFIGURATION.md](../m12a/PRODUCTION_ENVIRONMENT_CONFIGURATION.md)

### 3.2 Settings workspace (desktop UI)

Open **Settings** after login (requires `settings:view` or higher).

| Section | Keys / purpose |
|---------|----------------|
| **General** | Company name, address, GST, timezone, currency |
| **Security** | Session timeout, password policy, lockout, recovery key |
| **Inventory** | Default store, serial prefix, colour options |
| **Sales** | Payment modes, invoice prefix |
| **Tally** | Host, port, company name, sync interval, enable sync |
| **Integrations** | AI provider keys, primary provider, fallback chain |
| **Notifications** | Alert categories (Tally, inventory, backup, security) |
| **Backup** | Folder, schedule, retention, Recovery Center |
| **Excel** | Export path and file naming |

Settings persist in `webstudio.system_settings` and override `.env` defaults where applicable.

### 3.3 Security configuration

| Control | Default | Configure via |
|---------|---------|---------------|
| Password min length | 10 | Settings → Security |
| Password history | 5 | Settings → Security |
| Account lockout | 5 attempts / 15 min | Settings → Security |
| Access token TTL | 15 minutes | `.env` `ACCESS_TOKEN_TTL_MINUTES` |
| Refresh token TTL | 7 days | `.env` `REFRESH_TOKEN_TTL_DAYS` |
| RBAC | System + custom roles | Settings → Users / Access Roles |

**Certification reference:** [SECURITY_CERTIFICATION.md](SECURITY_CERTIFICATION.md)

### 3.4 Post-configuration validation

Run after configuration changes:

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\validate-production-certification.ps1 -BearerToken "<main-admin-token>"
.\validate-production-network.ps1 -BearerToken "<token>"
```

---

## 4. Networking

WEBSTUDIO IMS operates on a **private store LAN**. No public internet exposure is required for daily operations.

### 4.1 Topology

```
Staff devices (Wi‑Fi / wired)
        ↓
Store LAN (single subnet / VLAN recommended)
        ↓
WEBSTUDIO Server (Windows 11 Pro) — API :8000
        ↓ localhost only
PostgreSQL :5432

Billing PC (Tally ERP 9) — XML :9000  ← server outbound only
```

### 4.2 Discovery

| Method | When to use |
|--------|-------------|
| **mDNS** (`webstudio-server.local`) | Default — same LAN, UDP 5353 allowed |
| **Static IP** | mDNS blocked by router or multi-SSID isolation |
| **Manual URL** | `http://<server-ip>:8000` saved in client |

Document the server IP in **Office Deployment Wizard** or `WEBSTUDIO_DISCOVERY_CANDIDATES`.

### 4.3 Client connectivity requirements

| Platform | Requirement |
|----------|-------------|
| Desktop (Windows/macOS) | Outbound TCP 8000 to server |
| Android / iOS | Same Wi‑Fi/VLAN as server |
| Tally billing PC | Server can reach Tally host:9000 |

**Deep dive:** [INFRASTRUCTURE_CHECKLIST.md](INFRASTRUCTURE_CHECKLIST.md) · [m12h/NETWORKING_GUIDE.md](../m12h/NETWORKING_GUIDE.md)  
**Validation:** [NETWORK_VALIDATION_REPORT.md](NETWORK_VALIDATION_REPORT.md)

---

## 5. Firewall

Windows Defender Firewall on the **server** must allow LAN clients to reach the API while keeping PostgreSQL local.

### 5.1 Port matrix

| Port | Protocol | Direction | Bind | Purpose |
|------|----------|-----------|------|---------|
| **8000** | TCP | Inbound (LAN subnet) | Server | REST API |
| **5353** | UDP | Inbound (LAN subnet) | Server | mDNS discovery |
| **5432** | TCP | Localhost only | `127.0.0.1` | PostgreSQL — **never LAN** |
| **9000** | TCP | Outbound server → Tally PC | — | Tally XML |

### 5.2 Automated configuration

```powershell
cd D:\WEBSTUDIO-IMS\infra\windows
.\configure-firewall.ps1 -ApiPort 8000 -Subnet 192.168.1.0/24
```

Replace `192.168.1.0/24` with your store CIDR. Do **not** use `Any` in production.

### 5.3 Verify

```powershell
Get-NetFirewallRule -DisplayName "WEBSTUDIO IMS*" | Format-Table DisplayName, Enabled, Direction, Action
.\validate-production-network.ps1 -ApiPort 8000 -BearerToken "<token>"
```

**Full guide:** [FIREWALL_CONFIGURATION_GUIDE.md](FIREWALL_CONFIGURATION_GUIDE.md)

---

## 6. AI providers

AI enrichment assists **product specification lookup** when adding inventory (Add Laptop workflow). AI does not modify sales, inventory status, or Tally data.

### 6.1 Supported providers

| Provider | Settings key | Default model |
|----------|--------------|---------------|
| Google Gemini | `gemini_api_key` | `gemini-2.5-flash` |
| Groq | `groq_api_key` | `llama-3.3-70b-versatile` |
| OpenRouter | `openrouter_api_key` | Configurable |

Configure **primary provider** and **fallback chain** in Settings → Integrations.

### 6.2 Administrator setup

1. Open **Settings → Integrations**.
2. Enter API key for the chosen provider.
3. Set **AI enrichment enabled** (toggle).
4. Click **Test AI** — confirm provider responds.
5. Save.

Keys are stored in `system_settings` and **masked** in the API (`gemini_api_key_hint` shows last four characters only). Prefer database storage over `.env` files in production.

### 6.3 Operational notes

| Topic | Guidance |
|-------|----------|
| Internet | Server needs outbound HTTPS to provider APIs |
| Offline | Staff enter specs manually — no blocking |
| Cost | Monitor provider usage dashboards |
| Privacy | Only brand/model search terms sent to provider |

**Reference:** [m12h/AI_GUIDE.md](../m12h/AI_GUIDE.md)

---

## 7. API keys

WEBSTUDIO IMS uses two distinct key types. Do not confuse them.

### 7.1 AI provider keys

| Attribute | Value |
|-----------|-------|
| Purpose | Gemini, Groq, OpenRouter for product enrichment |
| Storage | `system_settings` (masked in API) |
| UI | Settings → Integrations |
| API | `PATCH /api/v1/settings/integrations` |
| Rotation | Update in Settings; clear with `clear_gemini_api_key` flag |

### 7.2 Integration API keys

| Attribute | Value |
|-----------|-------|
| Purpose | Email, SMS, WhatsApp, custom third-party services |
| Storage | `integration_api_keys` table — **Fernet-encrypted** at rest |
| UI | Settings → Integration Keys (desktop admin) |
| API | `GET/POST/PATCH /api/v1/admin/integration-keys` |
| Permission | `integration_keys:manage` |
| Rotation | Archive old key → create new → update external service |

Integration keys never appear in plaintext API responses — only `key_hint` (last four characters).

### 7.3 Key hygiene

| Rule | Reason |
|------|--------|
| Never commit keys to git or share in chat | Credential leak |
| Rotate after staff departure if shared | Access control |
| Use separate keys per environment | Blast radius |
| Exclude AI keys from casual backup exports | `restore_engine` excludes `gemini_api_key` by default |

**Certification:** [SECURITY_CERTIFICATION.md](SECURITY_CERTIFICATION.md) § AI & integration keys

---

## 8. Users and access control

| Task | Path |
|------|------|
| Create user | Settings → Users |
| Assign role | System role or custom access role |
| Custom permissions | Settings → Access Roles |
| Disable account | Archive user |
| Reset password | Admin reset; user changes on next login |

**Role matrix:** [ROLE_MATRIX_VALIDATION.md](ROLE_MATRIX_VALIDATION.md)

---

## 9. Quick reference — validation endpoints

| Validation | Endpoint |
|------------|----------|
| Production certification | `GET /api/v1/deployment/production-certification` |
| Production acceptance | `GET /api/v1/deployment/production-acceptance` |
| Network (production) | `GET /api/v1/network/admin/report?scope=production` |
| Backup (production) | `GET /api/v1/settings/backups/production-validation` |
| Tally (production) | `GET /api/v1/integrations/tally/production-validation` |
| Client deployment | `GET /api/v1/deployment/client-validation` |
| Health | `GET /health/ready` |

All commissioning endpoints require **network admin** or equivalent bearer token.

---

## 10. Related documents

| Topic | Document |
|-------|----------|
| Installation (step-by-step) | [INSTALLATION_MANUAL.md](INSTALLATION_MANUAL.md) |
| Operations | [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md) |
| Maintenance | [MAINTENANCE_GUIDE.md](MAINTENANCE_GUIDE.md) |
| Windows Service | [m12b/WINDOWS_SERVICE_GUIDE.md](../m12b/WINDOWS_SERVICE_GUIDE.md) |
| Installers | [m12c/INSTALLER_GUIDE.md](../m12c/INSTALLER_GUIDE.md) |
| Business hours | [m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md](../m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md) |
