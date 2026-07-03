---
Title: Architecture Diagrams — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
Related: ARCH-001
---

# Architecture Diagrams

High-level system architecture for WEBSTUDIO IMS production. Detail: [ARCH-001](../../SYSTEM_ARCHITECTURE.md).

---

## 1. System context

```mermaid
flowchart TB
    subgraph Users
        Staff[Showroom Staff]
        Admin[Main Admin]
    end

    subgraph Clients
        Desktop[WEBSTUDIO Desktop]
        Mobile[Mobile App]
    end

    subgraph ServerPC[Dedicated Server PC]
        API[WEBSTUDIO API]
        PG[(PostgreSQL)]
        Sched[Schedulers]
    end

    subgraph External
        Tally[Tally ERP 9 PC]
        AI[AI Providers]
    end

    Staff --> Desktop
    Staff --> Mobile
    Admin --> Desktop
    Desktop --> API
    Mobile --> API
    API --> PG
    Sched --> API
    API --> Tally
    API --> AI
```

---

## 2. Layered architecture

```mermaid
flowchart TB
    subgraph Presentation
        UI[Desktop / Flutter UI]
    end

    subgraph API[API Layer - FastAPI]
        Routers[Routers]
        Auth[Auth / RBAC]
        Schemas[Pydantic Schemas]
    end

    subgraph Domain[Domain Services]
        Inv[Inventory Service]
        Sales[Sales Service]
        TallySync[Tally Sync Service]
        Backup[Backup Engine]
    end

    subgraph Data[Data Layer]
        Repo[Repositories]
        Models[SQLAlchemy Models]
        DB[(PostgreSQL webstudio)]
    end

    UI --> Routers
    Routers --> Auth
    Routers --> Domain
    Domain --> Repo
    Repo --> Models
    Models --> DB
```

---

## 3. Authentication flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant D as Database

    C->>A: POST /auth/login
    A->>D: Validate user + password
    D-->>A: User + permissions
    A-->>C: access_token + refresh_token
    C->>A: GET /inventory (Bearer token)
    A->>A: Verify JWT + permissions
    A->>D: Query inventory
    D-->>A: Rows
    A-->>C: Envelope JSON
```

---

## 4. Tally sync data flow

```mermaid
sequenceDiagram
    participant Sch as Tally Scheduler
    participant Sync as TallySyncService
    participant T as Tally XML :9000
    participant DB as PostgreSQL
    participant N as Notifications

    Sch->>Sync: run_sync (interval)
    Sync->>T: Export vouchers (date window)
    T-->>Sync: XML response
    Sync->>Sync: Parse GUID (internal only)
    Sync->>DB: Dedup + match serial
    Sync->>DB: Create sale / update inventory
    Sync->>N: Import alerts (if configured)
    Sync->>DB: Update sync history
```

---

## 5. Backup architecture

```mermaid
flowchart LR
    subgraph Server
        BE[Backup Engine]
        PG[(PostgreSQL)]
        Assets[Asset Files]
    end

    subgraph Archive
        TGZ[backup.tar.gz]
        Manifest[manifest.json]
    end

    subgraph OffSite[Off-site]
        USB[USB / NAS]
    end

    BE --> PG
    BE --> Assets
    BE --> TGZ
    TGZ --> Manifest
    TGZ --> USB
```

---

## 6. Component responsibilities

| Component | Responsibility |
|-----------|----------------|
| FastAPI | HTTP API, validation, auth |
| PostgreSQL | Single source of truth |
| Electron / Flutter | UX, local cache, discovery |
| TallySyncService | Import vouchers, idempotency |
| BackupEngine | Enterprise archives |
| Schedulers | Timers with persistent state |
| mDNS | Optional LAN discovery |

---

## 7. Security boundaries

```mermaid
flowchart TB
    subgraph TrustLAN[Trusted Store LAN]
        Clients
        API
        PG
    end

    subgraph Billing[Tally PC]
        Tally[Tally ERP 9]
    end

    subgraph Internet
        AICloud[AI APIs]
    end

    Clients --> API
    API --> PG
    API --> Tally
    API --> AICloud

    subgraph NeverExposed[Never exposed to staff UI]
        GUID[Tally GUID / MasterID]
    end

    API -.- GUID
```
