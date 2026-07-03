---
Title: Deployment Diagrams — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Deployment Diagrams

Physical and logical deployment views for production showrooms.

---

## 1. Physical deployment

```mermaid
flowchart TB
    subgraph Store[Retail Showroom]
        subgraph ServerRoom[Server Area]
            SRV[Windows 11 Pro Server PC]
            UPS[UPS]
        end

        subgraph Floor[Sales Floor]
            D1[Desktop Counter 1]
            D2[Desktop Counter 2]
            M1[Staff Phones]
        end

        subgraph Billing[Billing Desk]
            TALLY[Tally Laptop]
        end

        RTR[Office Router / APs]
    end

    UPS --> SRV
    SRV --- RTR
    D1 --- RTR
    D2 --- RTR
    M1 --- RTR
    TALLY --- RTR
```

---

## 2. Software deployment on server

```mermaid
flowchart TB
    subgraph Win[Windows 11 Pro]
        subgraph Services[Windows Services]
            PGsvc[postgresql-x64-16]
            WSsvc[WEBSTUDIO Server]
        end

        subgraph Dirs[D:\WEBSTUDIO-IMS]
            Venv[Python venv]
            App[apps/backend]
            Logs[logs/]
            Backups[backups/]
            Env[config/env/.env]
        end
    end

    PGsvc --> DB[(PostgreSQL data)]
    WSsvc --> App
    App --> Venv
    App --> DB
    App --> Logs
    App --> Backups
    App --> Env
```

---

## 3. Client deployment

```mermaid
flowchart LR
    subgraph Artifacts[Release Artifacts]
        WinSetup[Desktop Setup.exe]
        Dmg[Desktop.dmg]
        Apk[WEBSTUDIO IMS.apk]
        SrvSetup[Server Setup.exe]
    end

    subgraph Targets[Install Targets]
        PCs[Windows PCs]
        Macs[Macs]
        Phones[Android]
        Server[Server PC]
    end

    WinSetup --> PCs
    Dmg --> Macs
    Apk --> Phones
    SrvSetup --> Server
```

---

## 4. Release deployment pipeline

```mermaid
flowchart LR
    Dev[Development] --> CI[GitHub Actions release.yml]
    CI --> Artifacts[Installers + APK]
    Artifacts --> Bundle[release/vX.Y.Z bundle]
    Bundle --> Staging[Staging LAN test]
    Staging --> Prod[Production showroom]
```

---

## 5. First-time deployment sequence

```mermaid
sequenceDiagram
    participant IT as IT Installer
    participant S as Server
    participant D as Desktop
    participant A as Main Admin

    IT->>S: Run Server Setup.exe
    S->>S: Migrations + service install
    IT->>D: Install Desktop Setup.exe
    D->>S: Discovery / connect
    A->>S: System Setup wizard
    A->>S: Office Deployment wizard
    A->>S: Configure Tally + backup
    A->>D: Train staff
```

---

## 6. Business hours power cycle

```mermaid
stateDiagram-v2
    [*] --> Off: Evening power off
    Off --> Booting: Morning power on
    Booting --> PostgreSQL: Service start
    PostgreSQL --> API: WEBSTUDIO delayed start
    API --> Running: Health ready
    Running --> Clients: Staff login
    Clients --> Running: Business day
    Running --> GracefulStop: Evening script
    GracefulStop --> Off: Power off
```

---

## 7. Environment deployment matrix

| Environment | Server | Clients | Tally | Backups |
|-------------|--------|---------|-------|---------|
| Development | localhost | dev build | optional mock | local folder |
| Testing | CI runner | automated tests | mocked | ephemeral |
| Staging | pilot LAN PC | pilot users | real Tally | daily |
| Production | dedicated PC | all staff | billing PC | scheduled + off-site |

Profiles: `config/env/.env.{development,testing,staging,production}`

---

## 8. Related

- [Deployment Guide](../DEPLOYMENT_GUIDE.md)
- [Installation Guide](../INSTALLATION_GUIDE.md)
- [M12G Release Engineering](../../m12g/RELEASE_ENGINEERING_REPORT.md)
