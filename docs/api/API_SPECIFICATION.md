---
Title: WEBSTUDIO IMS — API Specification (Version 1)
Version: 1.5
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/PROJECT_BIBLE.md, docs/product/PRODUCT_REQUIREMENTS.md, docs/SYSTEM_ARCHITECTURE.md, docs/database/DATABASE_DESIGN.md, docs/IMPLEMENTATION_GUIDE.md
---

# WEBSTUDIO IMS — API Specification

| Attribute | Value |
|-----------|-------|
| **Document ID** | API-001 |
| **Version** | 1.5 |
| **Status** | Active — Version 1 REST contract frozen for implementation |
| **Base URL (production)** | `https://{server-host}:8443/api/v1` |
| **Base URL (development)** | `http://localhost:8000/api/v1` |
| **OpenAPI target** | [docs/api/openapi/webstudio-ims-api-v1.yaml](openapi/webstudio-ims-api-v1.yaml) |

> **Authority:** This document defines the complete Version 1 REST API contract. FastAPI routers, Pydantic schemas, and `packages/api-client` must conform to this specification. Deviations require PRD traceability and an ADR when architectural.
>
> **Scope:** Contract definition only — no implementation code, SQL, or FastAPI source.

---

## Version History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.5 | 2026-06-27 | WEBSTUDIO IMS Team | Audit-only history: removed movement table/APIs; location transfer endpoints; serial lifecycle via audit; expanded audit search. |
| 1.4 | 2026-06-27 | WEBSTUDIO IMS Team | Tally ERP 9 synchronization: read-only invoices; multi-company sync; invoice line processing; dashboard; notifications; manual mark-as-sold (Admin/Main Admin only). |
| 1.3 | 2026-06-27 | WEBSTUDIO IMS Team | Server initialization and client onboarding: setup endpoints; login gated on `system_initialized`. |
| 1.2 | 2026-06-27 | WEBSTUDIO IMS Team | Authentication & audit strategy: Salesperson movement permission; `created_by_user_id` / `updated_by_user_id` on business DTOs; enriched audit log schema; movement audit fields. |
| 1.1 | 2026-06-27 | WEBSTUDIO IMS Team | Synchronized with Sprint 1D: UUID keys on `product_model` and `inventory_item`; structured ProductModel DTO; `current_location_id`; `reserved` status; serial number editable; conditional inventory delete; removed `configuration`, `row_version`, `created_by` from inventory. |
| 1.0 | 2026-06-27 | WEBSTUDIO IMS Team | Initial Version 1 API contract. All modules, bulk operations, standards, and worker endpoints. |

---

## Table of Contents

1. [Global Standards](#1-global-standards)
2. [System Setup](#2-system-setup)
3. [Authentication](#3-authentication)
4. [Users](#4-users)
5. [Brands](#5-brands)
6. [Product Models](#6-product-models)
7. [Locations](#7-locations)
8. [Inventory](#8-inventory)
9. [Inventory Movement](#9-inventory-movement)
10. [Search](#10-search)
11. [Sales](#11-sales)
12. [Dashboard](#12-dashboard)
13. [Reports](#13-reports)
14. [Excel Sync](#14-excel-sync)
15. [Tally Integration](#15-tally-integration)
16. [Audit](#16-audit)
17. [Settings](#17-settings)
18. [Health](#18-health)
19. [Shared Schemas](#19-shared-schemas)
20. [Error Catalogue](#20-error-catalogue)
21. [Permission Reference](#21-permission-reference)

---

## 1. Global Standards

### 1.1 URI Conventions

| Rule | Standard |
|------|----------|
| **Prefix** | All business endpoints under `/api/v1/` |
| **Health** | `/health`, `/health/ready`, `/health/version` — outside versioned prefix |
| **Resource names** | Plural `snake_case` nouns | `inventory_items`, `product_models`, `sync_jobs` |
| **Path parameters** | `{resource_id}` — integer surrogate keys for reference entities (`brand`, `location`, `user`); UUID for `product_model` and `inventory_item` |
| **Actions** | Sub-resource verbs as nested paths | `POST /product_models/{id}/archive` |
| **No trailing slashes** | `/api/v1/brands` not `/api/v1/brands/` |

### 1.2 HTTP Methods

| Method | Usage |
|--------|-------|
| `GET` | Read; idempotent; no body |
| `POST` | Create; actions; bulk operations |
| `PATCH` | Partial update of mutable fields |
| `PUT` | Full replacement — **not used V1** except where noted |
| `DELETE` | Permanent removal — **restricted** (product models and inventory items with no history only) |

Inventory items may be deleted only when not **Sold** and no movement, sale, or audit references exist (FR-INV-07). Otherwise use status transitions.

### 1.3 Authentication

| Header | Purpose |
|--------|---------|
| `Authorization: Bearer {access_token}` | Required on all endpoints except login, refresh, setup (when not initialized), and unauthenticated health |
| `X-Request-ID` | Client may supply UUID; server generates if absent; echoed in response and logs |
| `X-Client-Version` | Client application version — required on authenticated requests |
| `X-Client-Platform` | `windows_desktop`, `macos_desktop`, `android`, `excel_sync`, `tally_sync` |
| `Idempotency-Key` | Optional UUID on mutation requests — see §1.8 |

**Service accounts:** Excel Sync and Tally Sync workers authenticate with JWT issued to dedicated service users (`role` = service account with scoped permissions).

### 1.4 Response Envelope

**Success (single resource):**

```json
{
  "data": { },
  "meta": null,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Success (collection):**

```json
{
  "data": [ ],
  "meta": {
    "page": 1,
    "page_size": 50,
    "total_items": 237,
    "total_pages": 5
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Cursor pagination** (export and large lists):

```json
{
  "data": [ ],
  "meta": {
    "page_size": 500,
    "next_cursor": "eyJpZCI6MTIzfQ==",
    "has_more": true
  },
  "request_id": "..."
}
```

### 1.5 Error Envelope

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": [
      {
        "field": "serial_number",
        "code": "SERIAL_NUMBER_DUPLICATE",
        "message": "Serial number already exists."
      }
    ]
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| HTTP Status | When |
|-------------|------|
| `400` | Malformed request |
| `401` | Missing or invalid token |
| `403` | Authenticated but insufficient permission |
| `404` | Resource not found |
| `409` | Conflict — duplicate, invalid state transition, idempotent replay |
| `422` | Semantic validation failure |
| `429` | Rate limited (login endpoint) |
| `500` | Unexpected server error — generic message only |
| `503` | Service unavailable — readiness failure |

### 1.6 Pagination & Sorting

| Parameter | Type | Default | Max | Notes |
|-----------|------|---------|-----|-------|
| `page` | integer | `1` | — | Offset pagination |
| `page_size` | integer | `50` | `100` | List and search |
| `sort` | string | resource-specific | — | e.g. `updated_at:desc`, `serial_number:asc` |
| `cursor` | string | — | — | Cursor pagination; mutually exclusive with `page` |

### 1.7 Filtering Conventions

- Exact match: `status=available`
- Partial match (where documented): `serial_number_prefix=SN12`, `color=Sil` (ILIKE)
- Multi-value: `status=available,received` (comma-separated OR within field)
- Date range: `sold_at_from`, `sold_at_to` (ISO 8601 UTC)

### 1.8 Idempotency

| Operation | Key | Behaviour on Replay |
|-----------|-----|---------------------|
| Manual sale reflection | `invoice_number` + `serial_number` or `Idempotency-Key` header | `200` no-op if already Sold; Tally sync treats as same transaction |
| Tally sale reflection | `tally_company` + `tally_voucher_number` + `serial_number` | `200` no-op; optional Duplicate Sale notification |
| Excel sync trigger | `Idempotency-Key` header | Returns existing `sync_job` if pending/running with same key |
| Bulk inventory create | `batch_id` in body (optional UUID) | Rejects duplicate `batch_id` with `409` or returns prior results |
| Bulk movement | `batch_id` in body (optional UUID) | Same as bulk inventory |

### 1.9 Audit Behaviour Summary

| Mutation Category | Audit Action | Fields Captured |
|-------------------|--------------|-----------------|
| Inventory create/update/transition | `inventory.create`, `inventory.update`, `inventory.transition` | `before_state`, `after_state`, serial as `entity_identifier` |
| Movement | `inventory.move` | from/to location names, optional reason; updates `current_location_id` only |
| Sale | `sale.reflect` | sale source, voucher reference |
| User management | `user.create`, `user.update`, `user.disable` | role/status changes |
| Product model lifecycle | `product_model.archive`, `product_model.restore`, `product_model.delete` | status |
| Settings | `setting.update` | key, before/after value |
| Auth | `auth.login_success`, `auth.login_failure`, `auth.logout` | username (never password) |
| System setup | `system.initialize` | company name, username (never password) |
| Sync | `sync.job_created`, `sync.job_completed` | job id, outcome |

Audit records are **append-only** (FR-AUD-06). API exposes read-only audit endpoints.

---

## 2. System Setup

Setup endpoints gate first-time server initialization. Initialization state is stored as `system_initialized` in `system_settings` — **not** inferred from Main Admin user existence (FR-INIT-01, BR-28).

Clients call setup status after connecting to the server and before showing Login or the First-Time Setup Wizard (FR-CLIENT-05).

### 2.1 Setup Status

| | |
|---|---|
| **Endpoint** | `GET /api/v1/setup/status` |
| **Method** | `GET` |
| **Purpose** | Return whether the system has completed first-time initialization |
| **Authentication Required** | No |
| **Required Role** | — |

**Path Parameters:** None

**Query Parameters:** None

**Response Body (`200`):**

| Field | Type | Description |
|-------|------|-------------|
| `system_initialized` | boolean | `true` when setup is complete |
| `company_name` | string \| null | Set after initialization; `null` when not initialized |

**Success Codes:** `200`

**Error Codes:** `503` if database unavailable

**Audit Behaviour:** None

**Client behaviour:**

| `system_initialized` | Client action |
|----------------------|---------------|
| `true` | Show Login screen |
| `false` | Launch First-Time Setup Wizard |

---

### 2.2 Initialize System

| | |
|---|---|
| **Endpoint** | `POST /api/v1/setup/initialize` |
| **Method** | `POST` |
| **Purpose** | Complete first-time setup: create Main Admin and mark system initialized |
| **Authentication Required** | No — only accepted when `system_initialized = false` |
| **Required Role** | — |

**Request Body:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `company_name` | string | Yes | 1–200 chars; trimmed |
| `main_admin_name` | string | Yes | Display name; 1–128 chars |
| `username` | string | Yes | 3–64 chars; unique; trimmed |
| `password` | string | Yes | Min 10 chars; stored as **bcrypt** hash only |
| `confirm_password` | string | Yes | Must match `password` |

**Response Body (`201`):**

| Field | Type | Description |
|-------|------|-------------|
| `system_initialized` | boolean | Always `true` on success |
| `company_name` | string | Persisted company name |
| `main_admin` | `UserSummary` | Created Main Admin — see §19 |

**Success Codes:** `201`

**Error Codes:**

| Code | HTTP | Condition |
|------|------|-----------|
| `VALIDATION_ERROR` | 422 | Password mismatch, weak password, invalid fields |
| `USERNAME_DUPLICATE` | 409 | Username already exists |
| `SYSTEM_ALREADY_INITIALIZED` | 409 | `system_initialized` is already `true` |

**Validation Rules:** Reject when `system_initialized = true`. Password never returned or logged.

**Audit Behaviour:** `system.initialize` — username and company name only; never password.

**Idempotency:** Not idempotent — second call after success returns `SYSTEM_ALREADY_INITIALIZED`.

**Post-conditions:**

1. Main Admin user created with `role = main_admin`, `status = active`
2. `system_initialized` set to `true` in `system_settings`
3. `company_name` persisted in `system_settings`
4. Setup wizard must not be offered again unless database is intentionally reinitialized

---

## 3. Authentication

### 3.1 Login

| | |
|---|---|
| **Endpoint** | `POST /api/v1/auth/login` |
| **Method** | `POST` |
| **Purpose** | Authenticate user; issue access and refresh tokens — only when `system_initialized = true` |
| **Authentication Required** | No |
| **Required Role** | — |

**Request Body:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `username` | string | Yes | 3–64 chars; trimmed |
| `password` | string | Yes | Non-empty |

**Response Body (`200`):**

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | JWT — 15 min default |
| `refresh_token` | string | Opaque token — 7 days default |
| `token_type` | string | `"bearer"` |
| `expires_in` | integer | Access token TTL seconds |
| `user` | `UserSummary` | See §19 |

**Success Codes:** `200`

**Error Codes:**

| Code | HTTP | Condition |
|------|------|-----------|
| `SYSTEM_NOT_INITIALIZED` | 403 | `system_initialized = false` — client must run setup first |
| `INVALID_CREDENTIALS` | 401 | Wrong username/password — generic message |
| `ACCOUNT_LOCKED` | 403 | Lockout active — include `locked_until` |
| `ACCOUNT_DISABLED` | 403 | User status disabled |
| `RATE_LIMITED` | 429 | Too many attempts from IP |

**Validation Rules:** Rate limit 10/min/IP on login (TECH_STACK).

**Audit Behaviour:** `auth.login_success` or `auth.login_failure` — never log password.

**Idempotency:** N/A

---

### 3.2 Refresh Token

| | |
|---|---|
| **Endpoint** | `POST /api/v1/auth/refresh` |
| **Method** | `POST` |
| **Purpose** | Issue new access token; rotate refresh token |
| **Authentication Required** | Refresh token in body |
| **Required Role** | — |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `refresh_token` | string | Yes |

**Response Body (`200`):** Same shape as login (new token pair + `user`).

**Success Codes:** `200`

**Error Codes:**

| Code | HTTP | Condition |
|------|------|-----------|
| `INVALID_REFRESH_TOKEN` | 401 | Unknown or revoked token |
| `REFRESH_TOKEN_REUSE` | 401 | Rotation attack detected — family revoked |
| `ACCOUNT_DISABLED` | 403 | User disabled since issue |

**Audit Behaviour:** None (high volume); security events logged at WARNING if reuse detected.

**Idempotency:** N/A

---

### 3.3 Logout

| | |
|---|---|
| **Endpoint** | `POST /api/v1/auth/logout` |
| **Method** | `POST` |
| **Purpose** | Revoke current refresh token |
| **Authentication Required** | Yes (access token) |
| **Required Role** | Any authenticated user |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `refresh_token` | string | Yes |

**Response Body (`200`):** `{ "data": { "success": true } }`

**Success Codes:** `200` (idempotent — unknown token still returns 200)

**Error Codes:** `401` if access token invalid

**Audit Behaviour:** `auth.logout`

**Idempotency:** Safe to retry

---

### 3.4 Current User

| | |
|---|---|
| **Endpoint** | `GET /api/v1/auth/me` |
| **Method** | `GET` |
| **Purpose** | Return authenticated user profile and permissions |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Path Parameters:** None

**Query Parameters:** None

**Response Body (`200`):**

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | User ID |
| `username` | string | |
| `display_name` | string | Nullable |
| `role` | enum | `main_admin`, `admin`, `salesperson` |
| `status` | enum | `active`, `disabled` |
| `permissions` | string[] | Expanded permission codes |
| `must_change_password` | boolean | Force change on first login |
| `theme_preference` | enum | `light`, `dark`, `system` |

**Success Codes:** `200`

**Error Codes:** `401`

**Audit Behaviour:** None

---

### 3.5 Change Own Password

| | |
|---|---|
| **Endpoint** | `POST /api/v1/auth/change-password` |
| **Method** | `POST` |
| **Purpose** | User changes own password |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Request Body:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `current_password` | string | Yes* | *Optional if `must_change_password` |
| `new_password` | string | Yes | Min 10 chars |

**Response Body (`200`):** `{ "data": { "success": true } }` — invalidates other refresh tokens.

**Success Codes:** `200`

**Error Codes:** `401`, `422` (`WEAK_PASSWORD`, `INVALID_CURRENT_PASSWORD`)

**Audit Behaviour:** `user.update` (password change — no password in audit)

---

## 4. Users

All user management endpoints require **Main Admin** (FR-USER-01). Only Main Admin may create users, disable users, reset passwords, and assign roles. Client applications never create users.

### 4.1 List Users

| | |
|---|---|
| **Endpoint** | `GET /api/v1/users` |
| **Method** | `GET` |
| **Purpose** | Paginated list of all users |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Query Parameters:** `page`, `page_size`, `sort`, `status`, `role`, `search` (username/display_name prefix)

**Response Body:** `UserSummary[]` with pagination meta

**Success Codes:** `200`

**Error Codes:** `401`, `403`

---

### 4.2 Create User

| | |
|---|---|
| **Endpoint** | `POST /api/v1/users` |
| **Method** | `POST` |
| **Purpose** | Create new user account |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Request Body:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `username` | string | Yes | Unique; 3–64 chars |
| `display_name` | string | No | Max 128 |
| `role` | enum | Yes | `main_admin`, `admin`, `salesperson` |
| `temporary_password` | string | Yes | Min 10 chars; `must_change_password` set true |

**Response Body (`201`):** `UserDetail`

**Success Codes:** `201`

**Error Codes:** `409` (`USERNAME_DUPLICATE`), `422`

**Audit Behaviour:** `user.create`

---

### 4.3 Get User

| | |
|---|---|
| **Endpoint** | `GET /api/v1/users/{user_id}` |
| **Method** | `GET` |
| **Purpose** | Retrieve user by ID |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Success Codes:** `200`, `404`

---

### 4.4 Update User

| | |
|---|---|
| **Endpoint** | `PATCH /api/v1/users/{user_id}` |
| **Method** | `PATCH` |
| **Purpose** | Update display name or metadata |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Request Body:** `display_name` (optional)

**Success Codes:** `200`

**Audit Behaviour:** `user.update`

---

### 4.5 Update User Role

| | |
|---|---|
| **Endpoint** | `PATCH /api/v1/users/{user_id}/role` |
| **Method** | `PATCH` |
| **Purpose** | Assign role; bumps `token_version` to invalidate sessions |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `role` | enum | Yes |

**Validation Rules:** Cannot demote last `main_admin` (FR-USER-03) — `409` `LAST_MAIN_ADMIN`

**Audit Behaviour:** `user.update` with role in before/after

---

### 4.6 Reset User Password

| | |
|---|---|
| **Endpoint** | `POST /api/v1/users/{user_id}/reset-password` |
| **Method** | `POST` |
| **Purpose** | Main Admin sets temporary password |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Request Body:** `{ "temporary_password": string }`

**Success Codes:** `200` — sets `must_change_password: true`; revokes refresh tokens

**Audit Behaviour:** `user.update`

---

### 4.7 Disable User

| | |
|---|---|
| **Endpoint** | `POST /api/v1/users/{user_id}/disable` |
| **Method** | `POST` |
| **Purpose** | Disable account — user cannot login |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Validation Rules:** Cannot disable last `main_admin` — `409` `LAST_MAIN_ADMIN`

**Success Codes:** `200`

**Audit Behaviour:** `user.disable`

---

### 4.8 Enable User

| | |
|---|---|
| **Endpoint** | `POST /api/v1/users/{user_id}/enable` |
| **Method** | `POST` |
| **Purpose** | Reactivate disabled account |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Success Codes:** `200`

**Audit Behaviour:** `user.update`

---

## 5. Brands

### 5.1 List Brands

| | |
|---|---|
| **Endpoint** | `GET /api/v1/brands` |
| **Method** | `GET` |
| **Purpose** | List all brands |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Query Parameters:** `page`, `page_size`, `is_active` (boolean), `search` (name prefix)

**Response Body:** `Brand[]`

**Success Codes:** `200`

---

### 5.2 Create Brand

| | |
|---|---|
| **Endpoint** | `POST /api/v1/brands` |
| **Method** | `POST` |
| **Purpose** | Add brand |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `name` | string | Yes | Unique; 1–128 chars; trimmed |

**Success Codes:** `201`

**Error Codes:** `409` `BRAND_NAME_DUPLICATE`

**Audit Behaviour:** `brand.create` (via settings/reference audit pattern)

---

### 5.3 Get Brand

| | |
|---|---|
| **Endpoint** | `GET /api/v1/brands/{brand_id}` |
| **Method** | `GET` |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Success Codes:** `200`, `404`

---

### 5.4 Update Brand

| | |
|---|---|
| **Endpoint** | `PATCH /api/v1/brands/{brand_id}` |
| **Method** | `PATCH` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body:** `name` (optional)

**Success Codes:** `200`, `409`

---

### 5.5 Deactivate Brand

| | |
|---|---|
| **Endpoint** | `POST /api/v1/brands/{brand_id}/deactivate` |
| **Method** | `POST` |
| **Purpose** | Set `is_active=false` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Validation Rules:** Rejected if active inventory references brand (FR-BRD-03) — `409` `BRAND_HAS_ACTIVE_INVENTORY`

**Success Codes:** `200`

---

### 5.6 Activate Brand

| | |
|---|---|
| **Endpoint** | `POST /api/v1/brands/{brand_id}/activate` |
| **Method** | `POST` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Success Codes:** `200`

---

## 6. Product Models

### 6.1 List Product Models

| | |
|---|---|
| **Endpoint** | `GET /api/v1/product_models` |
| **Method** | `GET` |
| **Purpose** | List product models with optional filters |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Query Parameters:**

| Parameter | Type | Notes |
|-----------|------|-------|
| `brand_id` | integer | Filter by brand |
| `status` | enum | `active`, `archived` — Salesperson default: `active` only unless `include_archived=true` |
| `include_archived` | boolean | Default `false` for Salesperson; Admin/Main Admin may set `true` |
| `search` | string | Model number prefix |
| `page`, `page_size`, `sort` | | Standard |

**Response Body:** `ProductModel[]` with `available_count` aggregate optional

**Success Codes:** `200`

---

### 6.2 Create Product Model

| | |
|---|---|
| **Endpoint** | `POST /api/v1/product_models` |
| **Method** | `POST` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `brand_id` | integer | Yes | Brand must exist and be active |
| `model_number` | string | Yes | Unique per brand; 1–64 chars |
| `model_name` | string | Yes | Max 128 |
| `cpu` | string | Yes | Max 128 |
| `gpu` | string | No | Max 128 |
| `ram_gb` | integer | Yes | Positive |
| `storage_value` | number | Yes | Positive |
| `storage_unit` | enum | Yes | `GB`, `TB` |
| `storage_type` | enum | Yes | `SSD`, `HDD` |

**Response:** `ProductModel` with `status: active`

**Success Codes:** `201`

**Error Codes:** `409` `MODEL_NUMBER_DUPLICATE`

**Audit Behaviour:** `product_model.create`

---

### 6.3 Get Product Model

| | |
|---|---|
| **Endpoint** | `GET /api/v1/product_models/{product_model_id}` |
| **Method** | `GET` |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Response includes:** `id` (UUID), `brand_id`, `brand_name`, `model_number`, `model_name`, `cpu`, `gpu`, `ram_gb`, `storage_value`, `storage_unit`, `storage_type`, `status`, `inventory_count`, `created_at`, `updated_at`

**Success Codes:** `200`, `404`

---

### 6.4 Update Product Model

| | |
|---|---|
| **Endpoint** | `PATCH /api/v1/product_models/{product_model_id}` |
| **Method** | `PATCH` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body:** `model_number`, `model_name`, `cpu`, `gpu`, `ram_gb`, `storage_value`, `storage_unit`, `storage_type` (optional fields)

**Validation Rules:** `brand_id` immutable after inventory linked

**Audit Behaviour:** `product_model.update` (if exposed) or `inventory`-level N/A

---

### 6.5 Archive Product Model

| | |
|---|---|
| **Endpoint** | `POST /api/v1/product_models/{product_model_id}/archive` |
| **Method** | `POST` |
| **Purpose** | Set status to `archived` (PM-01) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Success Codes:** `200`

**Validation Rules:** Already archived → `200` idempotent

**Audit Behaviour:** `product_model.archive`

---

### 6.6 Restore Product Model

| | |
|---|---|
| **Endpoint** | `POST /api/v1/product_models/{product_model_id}/restore` |
| **Method** | `POST` |
| **Purpose** | Set status to `active` (PM-02) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Success Codes:** `200`

**Audit Behaviour:** `product_model.restore`

---

### 6.7 Delete Product Model (Conditional)

| | |
|---|---|
| **Endpoint** | `DELETE /api/v1/product_models/{product_model_id}` |
| **Method** | `DELETE` |
| **Purpose** | Permanent delete only when no history (PM-06, PM-07) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Validation Rules:** Reject with `409` `PRODUCT_MODEL_HAS_HISTORY` if any inventory, sale, or audit reference ever existed

**Success Codes:** `204`

**Audit Behaviour:** `product_model.delete`

---

### 6.8 Bulk Archive Product Models

| | |
|---|---|
| **Endpoint** | `POST /api/v1/product_models/bulk/archive` |
| **Method** | `POST` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `product_model_ids` | UUID[] | Yes — max 100 per request |

**Response Body:**

```json
{
  "data": {
    "succeeded": [1, 2],
    "failed": [{ "id": 3, "code": "ALREADY_ARCHIVED" }]
  }
}
```

**Audit Behaviour:** One audit entry per archived model

---

### 6.9 Bulk Restore Product Models

| | |
|---|---|
| **Endpoint** | `POST /api/v1/product_models/bulk/restore` |
| **Method** | `POST` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Request/Response:** Same pattern as §5.8

---

## 7. Locations

Reference data required by inventory. Pre-seeded with three locations (FR-LOC-01).

### 7.1 List Locations

| | |
|---|---|
| **Endpoint** | `GET /api/v1/locations` |
| **Method** | `GET` |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Query Parameters:** `is_active`, `page`, `page_size`

**Success Codes:** `200`

---

### 7.2 Create Location

| | |
|---|---|
| **Endpoint** | `POST /api/v1/locations` |
| **Method** | `POST` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Request Body:** `{ "name": string }` — unique, 1–128 chars

**Success Codes:** `201`

---

### 7.3 Get / Update Location

| | |
|---|---|
| **GET** | `GET /api/v1/locations/{location_id}` |
| **PATCH** | `PATCH /api/v1/locations/{location_id}` — `main_admin` |

---

### 7.4 Deactivate / Activate Location

| | |
|---|---|
| **Deactivate** | `POST /api/v1/locations/{location_id}/deactivate` |
| **Activate** | `POST /api/v1/locations/{location_id}/activate` |
| **Required Role** | `main_admin` |

**Validation:** Deactivate rejected if location holds inventory (FR-LOC-03) — `409` `LOCATION_HAS_INVENTORY`

---

## 8. Inventory

### 8.1 Create Inventory Item

| | |
|---|---|
| **Endpoint** | `POST /api/v1/inventory_items` |
| **Method** | `POST` |
| **Purpose** | Register single laptop (FR-INV-01) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `serial_number` | string | Yes | Globally unique; trimmed; non-empty (BR-01) |
| `product_model_id` | UUID | Yes | Must reference **active** product model (FR-PM-04) |
| `color` | string | Yes | Non-empty; max 64 (BR-22) |
| `current_location_id` | integer | Yes | Active location |
| `status` | enum | No | `received` or `available` — default per BD-01 open decision |

**Excluded V1 fields:** `purchase_date`, `purchase_cost`, `remarks` — not accepted.

**Response Body (`201`):** `InventoryItemDetail`

**Success Codes:** `201`

**Error Codes:**

| Code | HTTP | Condition |
|------|------|-----------|
| `SERIAL_NUMBER_DUPLICATE` | 409 | BR-01 |
| `PRODUCT_MODEL_ARCHIVED` | 422 | FR-PM-04 |
| `INVALID_STATUS` | 422 | Invalid initial status |

**Audit Behaviour:** `inventory.create`

**Idempotency:** Optional `Idempotency-Key` — duplicate serial always `409` regardless

---

### 8.2 Bulk Create Inventory Items

| | |
|---|---|
| **Endpoint** | `POST /api/v1/inventory_items/bulk` |
| **Method** | `POST` |
| **Purpose** | Register multiple laptops in one transaction |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `batch_id` | string (UUID) | No | Idempotency for entire batch |
| `items` | `CreateInventoryItemRequest[]` | Yes | Max **50** items per request |
| `continue_on_error` | boolean | No | Default `false` — all-or-nothing |

**Response Body (`201` or `207`):**

```json
{
  "data": {
    "batch_id": "uuid",
    "created_count": 48,
    "items": [ "InventoryItemDetail" ],
    "errors": [ { "index": 2, "code": "SERIAL_NUMBER_DUPLICATE", "serial_number": "..." } ]
  }
}
```

**Success Codes:** `201` (all succeeded), `207` (partial — only if `continue_on_error=true`)

**Audit Behaviour:** `inventory.create` per successful item

**Idempotency:** Same `batch_id` returns prior result with `200`

---

### 8.3 Get Inventory Item

| | |
|---|---|
| **Endpoint** | `GET /api/v1/inventory_items/{inventory_item_id}` |
| **Method** | `GET` |
| **Purpose** | Full detail for one unit — FR-SRH-11 |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Response Body (`InventoryItemDetail`):**

| Field | Type |
|-------|------|
| `id` | UUID |
| `serial_number` | string |
| `product_model_id` | UUID |
| `brand_id`, `brand_name` | |
| `model_number` | string |
| `model_name`, `cpu`, `gpu`, `ram_gb`, `storage_value`, `storage_unit`, `storage_type` | Product Model specification fields |
| `color` | string |
| `current_location_id`, `current_location_name` | |
| `status` | `received`, `available`, `reserved`, `sold` |
| `sale` | `SaleSummary` — nullable; present when sold |
| `created_by` | `UserSummary` |
| `updated_by` | `UserSummary` |
| `created_at`, `updated_at` | datetime |

**Success Codes:** `200`, `404`

---

### 8.4 Get Inventory Item by Serial

| | |
|---|---|
| **Endpoint** | `GET /api/v1/inventory_items/by-serial/{serial_number}` |
| **Method** | `GET` |
| **Purpose** | Exact serial lookup — highest priority search path |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Success Codes:** `200`, `404`

---

### 8.5 List Inventory Items

| | |
|---|---|
| **Endpoint** | `GET /api/v1/inventory_items` |
| **Method** | `GET` |
| **Purpose** | Flat paginated inventory list |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Query Parameters:**

| Parameter | Description |
|-----------|-------------|
| `status` | Filter by lifecycle status (`received`, `available`, `reserved`, `sold`) |
| `current_location_id` | Filter by current location |
| `brand_id` | Filter via product model join |
| `product_model_id` | Filter by model |
| `color` | Partial match |
| `serial_number_prefix` | Prefix search |
| `include_archived_models` | boolean — default false for Salesperson |
| `updated_since` | ISO datetime — recently updated |
| `page`, `page_size`, `sort` | Standard — default sort `updated_at:desc` |

**Success Codes:** `200`

---

### 8.6 List Inventory Groups

| | |
|---|---|
| **Endpoint** | `GET /api/v1/inventory_items/groups` |
| **Method** | `GET` |
| **Purpose** | Brand → model grouped view with available counts (FR-INV-10, PR-01–PR-08) |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Query Parameters:** Same filters as §7.5 plus `expand_serials` (boolean — include serial list per group, max 20 per group)

**Response Body:**

```json
{
  "data": [
    {
      "brand_id": 1,
      "brand_name": "ASUS",
      "product_model_id": 10,
      "model_number": "VivoBook 15",
      "status_summary": { "available": 5, "received": 1, "reserved": 0, "sold": 12 },
      "serials": [ ]
    }
  ]
}
```

**Success Codes:** `200`

---

### 8.7 Update Inventory Item

| | |
|---|---|
| **Endpoint** | `PATCH /api/v1/inventory_items/{inventory_item_id}` |
| **Method** | `PATCH` |
| **Purpose** | Update mutable attributes (FR-INV-06) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body (all optional):**

| Field | Validation |
|-------|------------|
| `serial_number` | Globally unique if changed; trimmed; non-empty |
| `color` | Non-empty if provided |
| `current_location_id` | Use location transfer endpoint (§9.1) — **rejected here** with `422` `USE_LOCATION_TRANSFER_ENDPOINT` |
| `product_model_id` | Rare; audited; must be active |

**Immutable:** none — all listed fields are mutable by authorized roles subject to validation

**Success Codes:** `200`

**Error Codes:** `409` `SERIAL_NUMBER_DUPLICATE`, `422`

**Audit Behaviour:** `inventory.update`

---

### 8.8 Transition Inventory Status

| | |
|---|---|
| **Endpoint** | `POST /api/v1/inventory_items/{inventory_item_id}/transition` |
| **Method** | `POST` |
| **Purpose** | Lifecycle state change (FR-INV-13) |
| **Authentication Required** | Yes |
| **Required Role** | `received→available`, `available↔reserved`: `main_admin`, `admin`; `available→sold`, `reserved→sold`: see Sales §10 |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `to_status` | enum | Yes — `available`, `reserved` from `received`/`available`; see transition matrix |

**Allowed via this endpoint:** `received` → `available`; `available` ↔ `reserved`

**Validation Rules:** Invalid transitions — `422` `INVALID_STATUS_TRANSITION`

**Audit Behaviour:** `inventory.transition`

---

### 8.9 Delete Inventory Item (Conditional)

| | |
|---|---|
| **Endpoint** | `DELETE /api/v1/inventory_items/{inventory_item_id}` |
| **Method** | `DELETE` |
| **Purpose** | Permanent delete only when no history (FR-INV-07) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Validation Rules:** Reject with `409` `INVENTORY_ITEM_HAS_HISTORY` if status is `sold` or any sale or audit reference exists

**Success Codes:** `204`

**Audit Behaviour:** `inventory.delete`

---

## 9. Inventory Location Transfer

Location changes update `inventory_item.current_location_id` only. **No separate movement table or movement history API.** Every transfer creates an `audit_log` entry (`inventory.move`) that is the authoritative history (FR-MOV-02, FR-AUD-01).

### 9.1 Transfer Inventory Item Location

| | |
|---|---|
| **Endpoint** | `POST /api/v1/inventory_items/{inventory_item_id}/transfer-location` |
| **Method** | `POST` |
| **Purpose** | Transfer unit to a new location (FR-MOV-01–03) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin`, `salesperson` |

**Request Body:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `to_location_id` | integer | Yes | Must differ from current; must be active |
| `reason` | string | No | Max 512 — optional note stored on audit entry |

**Validation Rules:**

- Status must be `available` or `reserved` (LC-04, FR-MOV-06) — `422` `SOLD_ITEM_CANNOT_MOVE`
- `to_location_id` must be active

**Response Body:** Updated `InventoryItemDetail` (no movement record)

**Success Codes:** `200`

**Audit Behaviour:** `inventory.move` — captures actor, timestamp, from/to locations with human-readable names, `before_state`/`after_state`

**Idempotency:** Same `Idempotency-Key` within 24h returns original result `200`

---

### 9.2 Bulk Location Transfer

| | |
|---|---|
| **Endpoint** | `POST /api/v1/inventory_items/bulk/transfer-location` |
| **Method** | `POST` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin`, `salesperson` |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `batch_id` | UUID | No |
| `to_location_id` | integer | Yes — shared destination |
| `reason` | string | No — applied to all successful transfers |
| `items` | array | Yes — max **50** |
| `items[].inventory_item_id` | UUID | Yes |
| `continue_on_error` | boolean | No — default false |

**Response:** Per-item success/failure summary

**Audit Behaviour:** `inventory.move` per successful item

**History:** Use `GET /api/v1/audit_logs` or `GET /api/v1/audit_logs/lifecycle/by-serial/{serial_number}` (§16)

---

## 10. Search

### 10.1 Combined Search

| | |
|---|---|
| **Endpoint** | `GET /api/v1/search/inventory` |
| **Method** | `GET` |
| **Purpose** | Multi-filter search (FR-SRH-07) — Brand, Model, Serial, CPU/GPU/RAM/Storage, Color, Location, Status |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Query Parameters:**

| Parameter | Type | Match | Notes |
|-----------|------|-------|-------|
| `q` | string | — | Free-text — serial exact/prefix OR product-model spec match if no structured filters |
| `serial_number` | string | exact | Highest priority — returns single detail mode |
| `serial_number_prefix` | string | prefix | |
| `brand_id` | integer | exact | |
| `brand_name` | string | partial | |
| `product_model_id` | UUID | exact | |
| `model_number` | string | partial | |
| `color` | string | partial | FR-SRH-13 |
| `current_location_id` | integer | exact | |
| `status` | enum | exact | `received`, `available`, `reserved`, `sold` — comma-separated multi-value |
| `cpu` | string | partial | Product Model `cpu` field |
| `gpu` | string | partial | Product Model `gpu` field — e.g. `4060` |
| `ram_gb` | integer | exact | Product Model `ram_gb` — e.g. `16` |
| `storage` | string | partial | Product Model storage fields |
| `include_archived_models` | boolean | — | Default false for Salesperson |
| `group_by_model` | boolean | — | Default `true` for model/config queries; `false` for serial |
| `page`, `page_size`, `sort` | | | |

**Response Modes:**

1. **Serial exact match** (`serial_number` provided and found): `data` is single `InventoryItemDetail`; `meta.match_type: "serial_exact"`
2. **Grouped results** (`group_by_model=true`): `data` is `InventoryGroup[]` with expandable serials
3. **Flat results** (`group_by_model=false`): `data` is `InventoryItemSummary[]`

**Success Codes:** `200`

**Error Codes:** `422` if mutually incompatible parameters

**Audit Behaviour:** None (read-only)

---

### 10.2 Quick Search (Dashboard)

| | |
|---|---|
| **Endpoint** | `GET /api/v1/search/quick` |
| **Method** | `GET` |
| **Purpose** | Optimized single-field search from dashboard (FR-DSH-06) |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Query Parameters:** `q` (required) — auto-detects serial vs model vs config term

**Success Codes:** `200` — same response shapes as §9.1

---

## 11. Sales

### 11.1 Reflect Sale (Manual)

| | |
|---|---|
| **Endpoint** | `POST /api/v1/sales/reflect` |
| **Method** | `POST` |
| **Purpose** | Manually mark inventory as Sold (FR-SLS-04, §8.6.2) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` only — **Salesperson excluded** |

**Request Body:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `serial_number` | string | Yes* | *Or `inventory_item_id` |
| `inventory_item_id` | UUID | Yes* | |
| `invoice_number` | string | Yes | Tally invoice/voucher reference |
| `customer_name` | string | No | Reference only — not billing |
| `payment_mode` | string | No | e.g., Cash, UPI, Card |
| `sold_at` | datetime | No | Defaults to now |
| `notes` | string | No | |

**Validation Rules:**

- Status must be `available` or `reserved` — `422` `INVALID_STATUS_TRANSITION`
- `received` → `sold` blocked (LC rules)
- Duplicate `(invoice_number, inventory_item_id)` → `200` idempotent no-op (FR-SLS-06)

**Response Body (`201`):** `SaleDetail`

**Success Codes:** `201`, `200` (idempotent duplicate)

**Error Codes:** `404` serial not found, `409` already sold (different invoice)

**Audit Behaviour:** `sale.reflect` + `inventory.transition`

**Idempotency:** `Idempotency-Key` header or `(invoice_number, serial_number)` pair

---

### 11.2 Process Invoice Line (Tally Worker)

| | |
|---|---|
| **Endpoint** | `POST /api/v1/integrations/tally/sales/process-line` |
| **Method** | `POST` |
| **Purpose** | Tally Sync worker processes one invoice line per FR-TLY-05–07 |
| **Authentication Required** | Yes — service account `tally_sync` |
| **Required Role** | Service: `tally_sync` |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `tally_company_name` | string | Yes |
| `tally_voucher_number` | string | Yes |
| `serial_number` | string | Yes |
| `product_model_number` | string | Yes |
| `brand_name` | string | No — used with model for match |
| `sold_at` | datetime | Yes |
| `invoice_number` | string | Yes — same as voucher identifier |
| `raw_payload_hash` | string | No — SHA-256 for audit |

**Response Body (`200`):**

| Field | Type | Description |
|-------|------|-------------|
| `outcome` | enum | `sale_applied`, `serial_not_found`, `model_mismatch`, `ignored`, `duplicate_sale` |
| `sale` | `SaleDetail` | Present when `sale_applied` or `duplicate_sale` |
| `notification_id` | integer | Present when notification created |

**Success Codes:** `200` for all outcomes (including ignored lines)

**Processing rules (exact match only):**

| Match | Action |
|-------|--------|
| Serial + product model match | Mark Sold; create sale; audit |
| Model exists; serial not found | Create `serial_not_found` notification |
| Serial exists; model mismatch | Create `model_mismatch` notification |
| Neither in IMS | Ignore — no notification |
| Already sold (manual or prior sync) | Idempotent; optional `duplicate_sale` notification |

**Idempotency:** `(tally_company_name, tally_voucher_number, serial_number)` — mandatory

**Audit Behaviour:** `sale.reflect` when sold; `tally_integration_event` always

---

### 11.3 Reflect Sale (Tally Worker — Legacy Alias)

Deprecated alias for single-line processing — prefer §11.2. Endpoint `POST /api/v1/integrations/tally/sales/reflect` delegates to same logic.

---

### 11.4 Get Sale

| | |
|---|---|
| **Endpoint** | `GET /api/v1/sales/{sale_id}` |
| **Method** | `GET` |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Success Codes:** `200`, `404`

---

### 11.5 List Sale History

| | |
|---|---|
| **Endpoint** | `GET /api/v1/sales` |
| **Method** | `GET` |
| **Purpose** | Sales history with filters (FR-SLS-03) |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Query Parameters:**

| Parameter | Description |
|-----------|-------------|
| `sold_at_from`, `sold_at_to` | Date range |
| `location_id` | Location at time of sale |
| `brand_id` | Via inventory join |
| `sale_source` | `manual`, `tally` |
| `serial_number_prefix` | |
| `page`, `page_size`, `sort` | Default `sold_at:desc` |

**Response Body:** `SaleDetail[]`

**Success Codes:** `200`

---

## 12. Dashboard

### 12.1 KPI Summary

| | |
|---|---|
| **Endpoint** | `GET /api/v1/dashboard/kpis` |
| **Method** | `GET` |
| **Purpose** | Operational KPI cards (FR-DSH-02–05) |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Response Body:**

```json
{
  "data": {
    "total_available": 142,
    "total_received": 8,
    "total_sold": 891,
    "brand_summary": [
      { "brand_id": 1, "brand_name": "ASUS", "available_count": 45 }
    ],
    "location_summary": [
      { "location_id": 1, "location_name": "ASUS Exclusive Store", "available_count": 22 }
    ],
    "as_of": "2026-06-27T10:30:00Z"
  }
}
```

**Success Codes:** `200`

**Audit Behaviour:** None

---

### 12.2 Recent Activity

| | |
|---|---|
| **Endpoint** | `GET /api/v1/dashboard/recent-activity` |
| **Method** | `GET` |
| **Purpose** | Recently updated inventory (FR-DSH-07) |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Query Parameters:** `limit` (default 20, max 50)

**Response Body:** `InventoryItemSummary[]` sorted by `updated_at:desc`

**Success Codes:** `200`

---

## 13. Reports

Supports FR-RPT-01–05. Export formats: JSON in API; file export via separate download endpoints.

### 13.1 Inventory Summary by Location

| | |
|---|---|
| **Endpoint** | `GET /api/v1/reports/inventory-by-location` |
| **Method** | `GET` |
| **Required Role** | `main_admin`, `admin` |

**Query Parameters:** `status` (default `available`)

---

### 13.2 Sold Inventory Report

| | |
|---|---|
| **Endpoint** | `GET /api/v1/reports/sold-inventory` |
| **Method** | `GET` |
| **Required Role** | `main_admin`, `admin` |

**Query Parameters:** `sold_at_from`, `sold_at_to`, `location_id`, `brand_id`, `page`, `page_size`

---

### 13.3 Stock Count Report

| | |
|---|---|
| **Endpoint** | `GET /api/v1/reports/stock-count` |
| **Method** | `GET` |
| **Purpose** | Available units by brand/model/location (FR-RPT-05) |
| **Required Role** | `main_admin`, `admin` |

---

### 13.4 Export Report to Excel

| | |
|---|---|
| **Endpoint** | `POST /api/v1/reports/{report_type}/export` |
| **Method** | `POST` |
| **Purpose** | Generate downloadable Excel report (FR-RPT-04) |
| **Required Role** | `main_admin`, `admin` |

**Path Parameters:** `report_type` — `inventory-by-location`, `sold-inventory`, `stock-count`, `movements`

**Response:** `202` with `{ "download_url": "...", "expires_at": "..." }` or streaming `200` with `Content-Disposition` — **implementation choice; prefer async job for large reports**

---

## 14. Excel Sync

Excel Sync is **export only** — never imports (BR-08, FR-XLS-06). API enqueues jobs; worker executes (SYSTEM_ARCHITECTURE §14.2).

### 14.1 Trigger Excel Sync

| | |
|---|---|
| **Endpoint** | `POST /api/v1/sync/excel/trigger` |
| **Method** | `POST` |
| **Purpose** | Manual sync trigger (FR-XLS-02) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `scheduled_at` | datetime | No — immediate if omitted |

**Response Body (`202`):** `SyncJob`

**Success Codes:** `202`

**Idempotency:** `Idempotency-Key` — returns existing pending job

**Audit Behaviour:** `sync.job_created`

---

### 14.2 Excel Sync Status

| | |
|---|---|
| **Endpoint** | `GET /api/v1/sync/excel/status` |
| **Method** | `GET` |
| **Purpose** | Current sync state and last completed job (FR-XLS-05) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Response Body:**

```json
{
  "data": {
    "last_completed_at": "2026-06-27T06:00:00Z",
    "last_job_status": "completed",
    "last_record_count": 1247,
    "last_output_path": "D:\\WEBSTUDIO-IMS\\exports\\inventory.xlsx",
    "pending_job": null,
    "last_error": null
  }
}
```

---

### 14.3 Excel Sync History

| | |
|---|---|
| **Endpoint** | `GET /api/v1/sync/excel/history` |
| **Method** | `GET` |
| **Purpose** | Paginated sync job history (FR-XLS-04) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Query Parameters:** `status`, `created_at_from`, `created_at_to`, `page`, `page_size`

**Response Body:** `SyncJob[]`

---

### 14.4 Get Sync Job

| | |
|---|---|
| **Endpoint** | `GET /api/v1/sync/jobs/{sync_job_id}` |
| **Method** | `GET` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

---

### 14.5 Worker: List Pending Jobs

| | |
|---|---|
| **Endpoint** | `GET /api/v1/sync/jobs/pending` |
| **Method** | `GET` |
| **Purpose** | Excel worker polls for work |
| **Authentication Required** | Yes — service account `excel_sync` |
| **Required Role** | Service: `excel_sync` |

**Query Parameters:** `job_type=excel_export`, `limit` (default 1)

---

### 14.6 Worker: Claim / Start Job

| | |
|---|---|
| **Endpoint** | `POST /api/v1/sync/jobs/{sync_job_id}/start` |
| **Method** | `POST` |
| **Purpose** | Worker marks job `running` |
| **Required Role** | Service: `excel_sync` |

**Success Codes:** `200`, `409` if already claimed

---

### 14.7 Worker: Complete Job

| | |
|---|---|
| **Endpoint** | `POST /api/v1/sync/jobs/{sync_job_id}/complete` |
| **Method** | `POST` |
| **Required Role** | Service: `excel_sync` |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `success` | boolean | Yes |
| `record_count` | integer | No |
| `output_file_path` | string | No |
| `error_message` | string | No — if failed |

**Audit Behaviour:** `sync.job_completed`

---

### 14.8 Worker: Export Data Page

| | |
|---|---|
| **Endpoint** | `GET /api/v1/sync/excel/export` |
| **Method** | `GET` |
| **Purpose** | Paginated inventory export for worker assembly (FR-XLS-03) |
| **Authentication Required** | Yes — service account `excel_sync` |
| **Required Role** | Service: `excel_sync` |

**Query Parameters:** `cursor`, `page_size` (default 500, max 500)

**Response columns per row:** `brand_name`, `model_number`, `serial_number`, `color`, `cpu`, `gpu`, `ram_gb`, `storage_value`, `storage_unit`, `storage_type`, `current_location_name`, `status`

**Success Codes:** `200`

---

## 15. Tally Integration

> **Billing boundary:** IMS **reads** invoices from Tally only. IMS **never** creates invoices in Tally (FR-TLY-12, BR-32).
>
> **Implementation blocked** until Tally POC checklist passes (SYSTEM_ARCHITECTURE §14.3.1). API contract defined for implementation readiness.

### 15.1 Tally Synchronization Dashboard

| | |
|---|---|
| **Endpoint** | `GET /api/v1/integrations/tally/dashboard` |
| **Method** | `GET` |
| **Purpose** | Tally Sync Dashboard (FR-TLY-11) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Response Body (`200`):**

| Field | Type | Description |
|-------|------|-------------|
| `connection_status` | enum | `connected`, `disconnected`, `error` |
| `enabled` | boolean | Master Tally sync enabled |
| `sync_interval_seconds` | integer | Configured interval — default **1800** |
| `next_scheduled_sync_at` | datetime | |
| `companies` | array | Per-company sync state |
| `companies[].company_name` | string | e.g., WEBSTUDIO, ASUS Exclusive Store |
| `companies[].last_successful_sync_time` | datetime \| null | |
| `companies[].last_processed_voucher_identifier` | string \| null | |
| `companies[].last_error` | string \| null | |
| `pending_notifications_count` | integer | Unresolved Tally notifications |
| `last_error` | string \| null | Most recent global error |

---

### 15.2 Trigger Tally Sync (Sync Now)

| | |
|---|---|
| **Endpoint** | `POST /api/v1/integrations/tally/sync/trigger` |
| **Method** | `POST` |
| **Purpose** | Manual sync — **Sync Now** (FR-TLY-10) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body (optional):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company_name` | string | No | Sync one company only; omit for all enabled companies |

**Response Body (`202`):** `{ "status": "accepted", "correlation_id": "..." }`

**Audit Behaviour:** `sync.tally_triggered`

---

### 15.3 Integration Status

| | |
|---|---|
| **Endpoint** | `GET /api/v1/integrations/tally/status` |
| **Method** | `GET` |
| **Purpose** | Lightweight connection health (FR-SET-06) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Response Body:** Summary subset of §15.1 — connection, last poll, consecutive failures

---

### 15.4 Tally Event History

| | |
|---|---|
| **Endpoint** | `GET /api/v1/integrations/tally/events` |
| **Method** | `GET` |
| **Purpose** | Integration event log (FR-TLY-04) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Query Parameters:**

| Parameter | Description |
|-----------|-------------|
| `event_type` | `poll`, `company_sync_started`, `company_sync_completed`, `invoice_line_processed`, `sale_applied`, `error` |
| `outcome` | `success`, `skipped`, `ignored`, `failed` |
| `tally_company_name` | Filter by company |
| `serial_number` | |
| `tally_voucher_number` | |
| `created_at_from`, `created_at_to` | |
| `page`, `page_size` | |

**Response Body:** `TallyIntegrationEvent[]`

---

### 15.5 Get Tally Event

| | |
|---|---|
| **Endpoint** | `GET /api/v1/integrations/tally/events/{event_id}` |
| **Method** | `GET` |
| **Required Role** | `main_admin`, `admin` |

---

### 15.6 Retry Failed Event

| | |
|---|---|
| **Endpoint** | `POST /api/v1/integrations/tally/events/{event_id}/retry` |
| **Method** | `POST` |
| **Purpose** | Re-attempt invoice line processing (FR-TLY-08 reconciliation) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Validation Rules:** Only events with `outcome=failed` and retryable error codes

**Response Body:** New processing result or `SaleDetail`

**Success Codes:** `200`, `201`, `404`, `409`

**Audit Behaviour:** New `tally_integration_event` + possible `sale.reflect`

**Idempotency:** Underlying sale reflection remains idempotent

---

### 15.7 Worker: Record Tally Event

| | |
|---|---|
| **Endpoint** | `POST /api/v1/integrations/tally/events` |
| **Method** | `POST` |
| **Purpose** | Tally worker logs poll/voucher outcomes |
| **Required Role** | Service: `tally_sync` |

**Request Body:** `TallyIntegrationEventCreate` — event_type, outcome, tally_company_name, voucher, serial, product_model_number, error fields

**Success Codes:** `201`

---

### 15.8 List Tally Notifications

| | |
|---|---|
| **Endpoint** | `GET /api/v1/integrations/tally/notifications` |
| **Method** | `GET` |
| **Purpose** | Tally notifications for Notification Center (FR-NOT-01) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Query Parameters:** `notification_type`, `is_resolved`, `tally_company_name`, `page`, `page_size`

**Response Body:** `Notification[]`

---

### 15.9 Resolve Tally Notification

| | |
|---|---|
| **Endpoint** | `POST /api/v1/integrations/tally/notifications/{notification_id}/resolve` |
| **Method** | `POST` |
| **Required Role** | `main_admin`, `admin` |

**Success Codes:** `200`

---

## 16. Audit

### 16.1 Search Audit Logs

| | |
|---|---|
| **Endpoint** | `GET /api/v1/audit_logs` |
| **Method** | `GET` |
| **Purpose** | Search and filter audit trail — **single source of truth** for inventory history (FR-AUD-05, FR-MOV-04) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Query Parameters:**

| Parameter | Description |
|-----------|-------------|
| `action` | e.g. `CREATE`, `LOCATION_CHANGE`, `STATUS_CHANGE`, `SYSTEM_ACTION` |
| `entity_type` | e.g. `inventory_item`, `product_model`, `brand`, `location`, `user` |
| `entity_id` | Inventory item UUID or other entity PK |
| `inventory_item_id` | Filter by inventory item UUID |
| `serial_number` | Serial number — returns full laptop lifecycle when used |
| `product_model_id` | Filter inventory-related entries for a model |
| `brand_id` | Filter inventory-related entries for a brand |
| `actor_user_id` | Who performed the action |
| `created_at_from`, `created_at_to` | Date range |
| `page`, `page_size` | Default sort `created_at:desc` |

**Response Body:** `AuditLogEntry[]` with human-readable `old_value`, `new_value`, and `description`

**Success Codes:** `200`

**Audit Behaviour:** Read-only — no audit of audit reads

---

### 16.2 Get Audit Log Entry

| | |
|---|---|
| **Endpoint** | `GET /api/v1/audit_logs/{audit_log_id}` |
| **Method** | `GET` |
| **Purpose** | Full detail including before/after state (FR-AUD-04) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Response Body:** `AuditLogEntry` with `old_value`, `new_value`, and `description`

**Success Codes:** `200`, `404`

---

### 16.4 Serial Number Lifecycle

| | |
|---|---|
| **Endpoint** | `GET /api/v1/audit_logs/lifecycle/by-serial/{serial_number}` |
| **Method** | `GET` |
| **Purpose** | Complete chronological history for one laptop (FR-MOV-04, FR-AUD-04) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin`, `salesperson` |

**Response includes:** creation, every location change (who/when/from/to), status changes, Tally sale reflection, archive/restore impacts, and other audited modifications — ordered `created_at:asc`.

**Success Codes:** `200`, `404` (serial not found)

---

### 16.5 Audit History for Entity

| | |
|---|---|
| **Endpoint** | `GET /api/v1/audit_logs/by-entity/{entity_type}/{entity_id}` |
| **Method** | `GET` |
| **Required Role** | `main_admin` |

---

## 17. Settings

### 17.1 List All Settings

| | |
|---|---|
| **Endpoint** | `GET /api/v1/settings` |
| **Method** | `GET` |
| **Purpose** | All system settings (FR-SET-01–07) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Query Parameters:** `category` — `system`, `excel`, `tally`, `security`, `display`

**Response Body:** `SystemSetting[]` — keys, values, types, descriptions (secrets masked)

---

### 17.2 Get Setting

| | |
|---|---|
| **Endpoint** | `GET /api/v1/settings/{setting_key}` |
| **Method** | `GET` |
| **Required Role** | `main_admin` |

---

### 17.3 Update Setting

| | |
|---|---|
| **Endpoint** | `PATCH /api/v1/settings/{setting_key}` |
| **Method** | `PATCH` |
| **Required Role** | `main_admin` |

**Request Body:** `{ "setting_value": string | integer | boolean | object }`

**Validation Rules:** Type must match `value_type` stored for key

**Audit Behaviour:** `setting.update`

---

### 17.4 System Settings (Grouped)

| | |
|---|---|
| **Endpoint** | `GET /api/v1/settings/groups/system` |
| **PATCH** | `PATCH /api/v1/settings/groups/system` |

**Keys:** `business_display_name`, `barcode_auto_submit`, `session_timeout_minutes`, `lockout_threshold`, `lockout_duration_minutes`

**Required Role:** `main_admin`

---

### 17.5 Excel Configuration (Grouped)

| | |
|---|---|
| **Endpoint** | `GET /api/v1/settings/groups/excel` |
| **PATCH** | `PATCH /api/v1/settings/groups/excel` |

**Keys:** `excel_sync_cron`, `excel_export_path`, `excel_sync_enabled`

**Required Role:** `main_admin`

---

### 17.6 Tally Configuration (Grouped)

| | |
|---|---|
| **Endpoint** | `GET /api/v1/settings/groups/tally` |
| **PATCH** | `PATCH /api/v1/settings/groups/tally` |

**Keys:** `tally_sync_interval_seconds` (default **1800**), `tally_host`, `tally_port`, `tally_enabled`

**Required Role:** `main_admin`

---

### 17.7 User Theme Preference

| | |
|---|---|
| **Endpoint** | `PATCH /api/v1/auth/me/preferences` |
| **Method** | `PATCH` |
| **Purpose** | User theme preference (FR-SET-05) |
| **Required Role** | Any authenticated user |

**Request Body:** `{ "theme_preference": "light" | "dark" | "system" }`

---

## 18. Health

Health endpoints are **unversioned** — used by monitoring and deployment verification.

### 18.1 Health (Liveness)

| | |
|---|---|
| **Endpoint** | `GET /health` |
| **Method** | `GET` |
| **Purpose** | Process is running |
| **Authentication Required** | No |

**Response Body (`200`):**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "api_version": "v1",
  "min_client_version": "0.1.0"
}
```

---

### 18.2 Readiness

| | |
|---|---|
| **Endpoint** | `GET /health/ready` |
| **Method** | `GET` |
| **Purpose** | Ready to serve traffic — DB connected, migrations current, disk space OK |
| **Authentication Required** | No |

**Response Body (`200` or `503`):**

```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "migrations": "ok",
    "disk_space": "ok"
  }
}
```

---

### 18.3 Version

| | |
|---|---|
| **Endpoint** | `GET /health/version` |
| **Method** | `GET` |
| **Purpose** | Build and API version metadata |
| **Authentication Required** | No |

---

### 18.4 Integration Health

| | |
|---|---|
| **Endpoint** | `GET /health/integrations` |
| **Method** | `GET` |
| **Purpose** | Last sync timestamps and failure counts (FR-SET-06) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Response Body:** Excel and Tally summary — same fields as §13.2 and §14.1

---

## 19. Shared Schemas

Reusable object definitions referenced across endpoints.

### 19.1 UserSummary

| Field | Type |
|-------|------|
| `id` | integer |
| `username` | string |
| `display_name` | string \| null |
| `role` | enum |
| `status` | enum |

### 19.2 Brand

| Field | Type |
|-------|------|
| `id` | integer |
| `name` | string |
| `is_active` | boolean |
| `created_at`, `updated_at` | datetime |

### 19.3 ProductModel

| Field | Type |
|-------|------|
| `id` | UUID |
| `brand_id` | integer |
| `brand_name` | string |
| `model_number` | string |
| `model_name` | string |
| `cpu` | string |
| `gpu` | string \| null |
| `ram_gb` | integer |
| `storage_value` | number |
| `storage_unit` | `GB` \| `TB` |
| `storage_type` | `SSD` \| `HDD` |
| `status` | `active` \| `archived` |
| `created_by` | `UserSummary` |
| `updated_by` | `UserSummary` |
| `created_at`, `updated_at` | datetime |

### 19.4 Location

| Field | Type |
|-------|------|
| `id` | integer |
| `name` | string |
| `is_active` | boolean |

### 19.5 InventoryItemDetail

See §7.3. **Excluded fields:** `purchase_date`, `purchase_cost`, `remarks`.

### 19.6 InventoryItemSummary

Subset for lists: `id`, `serial_number`, `brand_name`, `model_number`, `color`, `cpu`, `gpu`, `ram_gb`, `storage_value`, `storage_unit`, `storage_type`, `current_location_name`, `status`, `updated_at`

### 19.7 SaleDetail

| Field | Type |
|-------|------|
| `id` | integer |
| `inventory_item_id` | UUID |
| `serial_number` | string |
| `sale_source` | `manual` \| `tally` |
| `sold_at` | datetime |
| `recorded_by` | UserSummary \| null |
| `invoice_number` | string |
| `customer_name` | string \| null |
| `payment_mode` | string \| null |
| `tally_company_name` | string \| null |
| `tally_voucher_number` | string \| null |
| `notes` | string \| null |
| `created_at` | datetime |

### 19.9 SyncJob

| Field | Type |
|-------|------|
| `id` | integer |
| `job_type` | `excel_export` |
| `status` | `pending`, `running`, `completed`, `failed`, `cancelled` |
| `triggered_by` | UserSummary \| null |
| `scheduled_at`, `started_at`, `completed_at` | datetime \| null |
| `record_count` | integer \| null |
| `output_file_path` | string \| null |
| `error_message` | string \| null |
| `retry_count` | integer |
| `created_at` | datetime |

### 19.10 TallyIntegrationEvent

| Field | Type |
|-------|------|
| `id` | integer |
| `event_type` | enum |
| `outcome` | enum |
| `tally_company_name` | string |
| `tally_voucher_number` | string \| null |
| `serial_number` | string \| null |
| `product_model_number` | string \| null |
| `inventory_item_id` | UUID \| null |
| `skip_reason` | string \| null |
| `error_code`, `error_message` | string \| null |
| `correlation_id` | string |
| `created_at` | datetime |

### 19.11 Notification

| Field | Type |
|-------|------|
| `id` | integer |
| `notification_type` | `serial_not_found`, `model_mismatch`, `duplicate_sale`, `sync_failure` |
| `severity` | `info`, `warning`, `error` |
| `title` | string |
| `message` | string |
| `tally_company_name` | string \| null |
| `tally_voucher_number` | string \| null |
| `serial_number` | string \| null |
| `product_model_number` | string \| null |
| `is_read` | boolean |
| `is_resolved` | boolean |
| `created_at` | datetime |
| `resolved_at` | datetime \| null |

### 19.12 AuditLogEntry

| Field | Type |
|-------|------|
| `id` | uuid |
| `entity_type` | string |
| `entity_id` | string |
| `inventory_item_id` | uuid \| null |
| `actor_user_id` | integer \| null |
| `actor_display_name` | string \| null |
| `actor_role` | string \| null |
| `action` | enum (`CREATE`, `UPDATE`, `ARCHIVE`, `RESTORE`, `STATUS_CHANGE`, `LOCATION_CHANGE`, `SYSTEM_ACTION`) |
| `field_name` | string \| null |
| `old_value` | object \| null — human-readable snapshots (e.g. location names) |
| `new_value` | object \| null — may include Tally metadata (`invoice_number`, `voucher_type`) |
| `description` | string \| null — human-readable summary |
| `created_at` | datetime |

### 19.13 SystemSetting

| Field | Type |
|-------|------|
| `setting_key` | string |
| `setting_value` | string |
| `value_type` | enum |
| `description` | string \| null |
| `category` | string |
| `updated_at` | datetime |

---

## 20. Error Catalogue

Standard `error.code` values for Version 1.

| Code | HTTP | Description |
|------|------|-------------|
| `VALIDATION_ERROR` | 422 | Generic validation failure |
| `INVALID_CREDENTIALS` | 401 | Login failed |
| `SYSTEM_NOT_INITIALIZED` | 403 | Login blocked until first-time setup completes |
| `SYSTEM_ALREADY_INITIALIZED` | 409 | Setup initialize rejected — system already initialized |
| `ACCOUNT_LOCKED` | 403 | Lockout active |
| `ACCOUNT_DISABLED` | 403 | User disabled |
| `PERMISSION_DENIED` | 403 | RBAC failure |
| `NOT_FOUND` | 404 | Resource not found |
| `SERIAL_NUMBER_DUPLICATE` | 409 | BR-01 |
| `SERIAL_NOT_FOUND` | 404 | Sale/search — no matching serial |
| `PRODUCT_MODEL_ARCHIVED` | 422 | FR-PM-04 |
| `PRODUCT_MODEL_HAS_HISTORY` | 409 | PM-06 — delete rejected |
| `BRAND_HAS_ACTIVE_INVENTORY` | 409 | FR-BRD-03 |
| `LOCATION_HAS_INVENTORY` | 409 | FR-LOC-03 |
| `MODEL_MISMATCH` | 422 | Tally line — serial exists; model does not match |
| `TALLY_LINE_IGNORED` | 200 | Accessory/non-IMS line — not an error |
| `BRAND_NAME_DUPLICATE` | 409 | |
| `USERNAME_DUPLICATE` | 409 | |
| `LAST_MAIN_ADMIN` | 409 | FR-USER-03 |
| `INVALID_STATUS_TRANSITION` | 422 | Lifecycle violation |
| `INVENTORY_ITEM_HAS_HISTORY` | 409 | FR-INV-07 — delete rejected |
| `SOLD_ITEM_CANNOT_MOVE` | 422 | LC-04 |
| `USE_MOVEMENT_ENDPOINT` | 422 | Location change via PATCH rejected |
| `ALREADY_SOLD` | 409 | Sale idempotency / duplicate |
| `RATE_LIMITED` | 429 | Login throttled |
| `INVALID_REFRESH_TOKEN` | 401 | |
| `REFRESH_TOKEN_REUSE` | 401 | Token rotation attack |
| `WEAK_PASSWORD` | 422 | Password policy |
| `SERVICE_UNAVAILABLE` | 503 | Readiness failure |
| `INTERNAL_ERROR` | 500 | Unexpected |

---

## 21. Permission Reference

Permissions map to PRD §17.2 matrix. Enforced via `packages/auth/permissions.py`.

| Permission Code | Roles | Endpoints |
|-----------------|-------|-----------|
| `auth:login` | all | §3 |
| `users:manage` | main_admin | §3 |
| `brands:read` | all | GET brands |
| `brands:write` | main_admin, admin | POST/PATCH brands |
| `product_models:read` | all | GET product_models |
| `product_models:write` | main_admin, admin | Create/update |
| `product_models:archive` | main_admin | Archive/restore/delete/bulk |
| `locations:read` | all | GET locations |
| `locations:write` | main_admin | POST/PATCH locations |
| `inventory:read` | all | GET inventory, search |
| `inventory:write` | main_admin, admin | Create/update/bulk/delete (conditional) |
| `inventory:transition` | main_admin, admin | received→available; available↔reserved |
| `location:transfer` | main_admin, admin, salesperson | §9 location transfer |
| `audit:lifecycle` | all authenticated | §16.4 serial lifecycle |
| `sales:reflect` | main_admin, admin | Manual mark-as-sold §11.1 — Salesperson excluded |
| `sales:read` | all | GET sales |
| `dashboard:read` | all | §12 |
| `reports:read` | main_admin, admin | §13 |
| `sync:trigger` | main_admin, admin | §14.1–14.4 |
| `sync:worker` | excel_sync service | §14.5–14.8 |
| `tally:sync` | main_admin, admin | §15.2 Sync Now |
| `tally:dashboard` | main_admin, admin | §15.1 dashboard |
| `tally:notifications` | main_admin, admin | §15.8–15.9 |
| `tally:worker` | tally_sync service | §11.2, §15.7 |
| `tally:admin` | main_admin, admin | §15.3–15.6 events; settings `main_admin` only |
| `audit:read` | main_admin | §16 |
| `settings:read` | main_admin | GET settings |
| `settings:write` | main_admin | PATCH settings |
| `health:integrations` | main_admin | §17.4 |

---

## Implementation Notes

1. **OpenAPI generation:** This specification is the source for `docs/api/openapi/webstudio-ims-api-v1.yaml`. Keep both in sync.
2. **Tally endpoints:** Contract defined; implementation gated on POC (SYSTEM_ARCHITECTURE §14.3.1).
3. **Bulk limits:** 50 items per bulk request V1 — adjust via ADR if migration requires more.
4. **Default inventory status on create:** Follow BD-01 resolution in DATABASE_DESIGN §15 — document in OpenAPI enum default when decided.
5. **Sale field list:** Customer/invoice fields per BD-03 — optional fields above may become required after business sign-off.

---

## References

| Document | Path |
|----------|------|
| Project Bible | [docs/PROJECT_BIBLE.md](../PROJECT_BIBLE.md) |
| Product Requirements | [docs/product/PRODUCT_REQUIREMENTS.md](../product/PRODUCT_REQUIREMENTS.md) |
| System Architecture | [docs/SYSTEM_ARCHITECTURE.md](../SYSTEM_ARCHITECTURE.md) |
| Database Design | [docs/database/DATABASE_DESIGN.md](../database/DATABASE_DESIGN.md) |
| Implementation Guide | [docs/IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) |
| OpenAPI (implementation artefact) | [docs/api/openapi/webstudio-ims-api-v1.yaml](openapi/webstudio-ims-api-v1.yaml) |

---

> **Document Authority:** This API contract is binding for WEBSTUDIO IMS Version 1. Endpoint changes require updating this document, the OpenAPI spec, and `packages/api-client`.

*WEBSTUDIO IMS Team — 2026*
