---
Title: Networking Diagrams — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Networking Diagrams

LAN topology, discovery, and Tally connectivity for production showrooms.

---

## 1. Single-floor topology

```mermaid
flowchart TB
    Internet((Internet)) --- Router[Office Router]

    Router --> AP[Wi‑Fi Access Point]
    Router --> ETH[Ethernet Switch]

    ETH --> Server[WEBSTUDIO Server<br/>192.168.1.100]
    ETH --> Desktop1[Desktop PC]
    ETH --> Tally[Tally Laptop]

    AP --> Phone1[Android Phone]
    AP --> Phone2[iPhone]
    AP --> Desktop2[Wi‑Fi Desktop]
```

---

## 2. Multi-floor / multi-SSID

```mermaid
flowchart TB
    Router[Main Router]

    Router --> AP1[SSID: Store-Ground]
    Router --> AP2[SSID: Store-First]
    Router --> AP3[SSID: Office]

    AP1 --> VLAN[Same LAN / VLAN]
    AP2 --> VLAN
    AP3 --> VLAN

    VLAN --> Server[WEBSTUDIO Server]
    VLAN --> Tally[Tally Laptop mobile]
    VLAN --> Clients[All Clients]

    note[Requirement: AP isolation OFF between store SSIDs]
```

---

## 3. mDNS discovery flow

```mermaid
sequenceDiagram
    participant D as Desktop App
    participant MDNS as mDNS multicast
    participant S as Server mDNS advertiser
    participant API as WEBSTUDIO API

    D->>MDNS: Browse _webstudio-ims._tcp.local.
    S->>MDNS: Advertise host:port
    MDNS-->>D: Service record
    D->>API: GET /health/live
    API-->>D: 200 OK
    D->>API: GET /discovery/health
    API-->>D: company_name, versions
```

---

## 4. Manual URL fallback

```mermaid
flowchart LR
    Client[Client App]
    Client -->|1 mDNS fails| Manual[Manual URL entry]
    Manual -->|http://192.168.1.100:8000| API[API]
    Client -->|2 Saved URL| Cache[Local storage]
    Cache --> API
    Client -->|3 Candidates| Env[office_discovery_urls]
    Env --> API
```

---

## 5. Tally network path

```mermaid
flowchart LR
    subgraph ServerPC[Server PC]
        API[WEBSTUDIO API]
        Probe[Connectivity Probe 120s]
    end

    subgraph TallyPC[Tally Billing PC]
        Tally[Tally ERP 9 :9000]
    end

    API -->|HTTP XML POST| Tally
    Probe -->|TCP test| Tally
```

**Firewall:** Server outbound to Tally:9000; Tally inbound from server IP.

---

## 6. Port and firewall map

```mermaid
flowchart TB
    subgraph InboundToServer[Inbound to Server]
        P8000[TCP 8000 - API]
        P5353[UDP 5353 - mDNS]
    end

    subgraph LocalOnly[Localhost only]
        P5432[TCP 5432 - PostgreSQL]
    end

    subgraph OutboundFromServer[Outbound from Server]
        T9000[TCP 9000 - Tally]
        AI443[TCP 443 - AI APIs optional]
    end

    Clients[LAN Clients] --> P8000
    Clients --> P5353
    API[API Process] --> P5432
    API --> T9000
    API --> AI443
```

---

## 7. IP addressing strategy

```mermaid
flowchart TD
    Start[New deployment] --> Wizard[Office Deployment Wizard]
    Wizard --> MDNS{mDNS active?}
    MDNS -->|Yes| DHCP[Recommend DHCP Reservation]
    MDNS -->|No| Static[Recommend Static IP on server]
    DHCP --> Router[Configure router MAC reservation]
    Static --> NIC[Set static IPv4 on server adapter]
    Router --> Done[Document IP in deployment summary]
    NIC --> Done
```

---

## 8. Client reconnect after outage

```mermaid
sequenceDiagram
    participant C as Client
    participant API as Server API

    Note over API: Server restart
    C->>API: health check fails
    C->>C: Show Offline
    loop Every 15s
        C->>API: health check
    end
    API-->>C: 200 OK
    C->>C: Show Online
    C->>API: Resume session / refresh data
```

---

## 9. Related

- [Networking Guide](../NETWORKING_GUIDE.md)
- [M12D Network Report](../../m12d/NETWORK_REPORT.md)
- [docs/network/NETWORK_DISCOVERY_ARCHITECTURE.md](../../network/NETWORK_DISCOVERY_ARCHITECTURE.md)
