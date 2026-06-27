---
Title: WEBSTUDIO IMS — API Specification (Version 1)
Version: 1.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/PROJECT_BIBLE.md, docs/product/PRODUCT_REQUIREMENTS.md, docs/SYSTEM_ARCHITECTURE.md, docs/database/DATABASE_DESIGN.md, docs/IMPLEMENTATION_GUIDE.md
---

# WEBSTUDIO IMS — API Specification

| Attribute | Value |
|-----------|-------|
| **Document ID** | API-001 |
| **Version** | 1.0 |
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
| 1.0 | 2026-06-27 | WEBSTUDIO IMS Team | Initial Version 1 API contract. All modules, bulk operations, standards, and worker endpoints. |

---

## Table of Contents

1. [Global Standards](#1-global-standards)
2. [Authentication](#2-authentication)
3. [Users](#3-users)
4. [Brands](#4-brands)
5. [Product Models](#5-product-models)
6. [Locations](#6-locations)
7. [Inventory](#7-inventory)
8. [Inventory Movement](#8-inventory-movement)
9. [Search](#9-search)
10. [Sales](#10-sales)
11. [Dashboard](#11-dashboard)
12. [Reports](#12-reports)
13. [Excel Sync](#13-excel-sync)
14. [Tally Integration](#14-tally-integration)
15. [Audit](#15-audit)
16. [Settings](#16-settings)
17. [Health](#17-health)
18. [Shared Schemas](#18-shared-schemas)
19. [Error Catalogue](#19-error-catalogue)
20. [Permission Reference](#20-permission-reference)

---

## 1. Global Standards

### 1.1 URI Conventions

| Rule | Standard |
|------|----------|
| **Prefix** | All business endpoints under `/api/v1/` |
| **Health** | `/health`, `/health/ready`, `/health/version` — outside versioned prefix |
| **Resource names** | Plural `snake_case` nouns | `inventory_items`, `product_models`, `sync_jobs` |
| **Path parameters** | `{resource_id}` — integer surrogate keys unless noted |
| **Actions** | Sub-resource verbs as nested paths | `POST /product_models/{id}/archive` |
| **No trailing slashes** | `/api/v1/brands` not `/api/v1/brands/` |

### 1.2 HTTP Methods

| Method | Usage |
|--------|-------|
| `GET` | Read; idempotent; no body |
| `POST` | Create; actions; bulk operations |
| `PATCH` | Partial update of mutable fields |
| `PUT` | Full replacement — **not used V1** except where noted |
| `DELETE` | Permanent removal — **restricted** (product models with no history only) |

Inventory items are **never deleted** (FR-INV-07). Use status transitions instead.

### 1.3 Authentication

| Header | Purpose |
|--------|---------|
| `Authorization: Bearer {access_token}` | Required on all endpoints except login, refresh, and unauthenticated health |
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
| Manual sale reflection | `Idempotency-Key` header | `409` with existing sale in body, or `200` no-op |
| Tally sale reflection | `tally_voucher_number` + `serial_number` | `200` no-op; no duplicate sale |
| Excel sync trigger | `Idempotency-Key` header | Returns existing `sync_job` if pending/running with same key |
| Bulk inventory create | `batch_id` in body (optional UUID) | Rejects duplicate `batch_id` with `409` or returns prior results |
| Bulk movement | `batch_id` in body (optional UUID) | Same as bulk inventory |

### 1.9 Optimistic Concurrency

Inventory updates accept optional `row_version` in request body. Mismatch returns `409` with code `ROW_VERSION_CONFLICT`.

### 1.10 Audit Behaviour Summary

| Mutation Category | Audit Action | Fields Captured |
|-------------------|--------------|-----------------|
| Inventory create/update/transition | `inventory.create`, `inventory.update`, `inventory.transition` | `before_state`, `after_state`, serial as `entity_identifier` |
| Movement | `inventory.move` | from/to location, reason |
| Sale | `sale.reflect` | sale source, voucher reference |
| User management | `user.create`, `user.update`, `user.disable` | role/status changes |
| Product model lifecycle | `product_model.archive`, `product_model.restore`, `product_model.delete` | status |
| Settings | `setting.update` | key, before/after value |
| Auth | `auth.login_success`, `auth.login_failure`, `auth.logout` | username (never password) |
| Sync | `sync.job_created`, `sync.job_completed` | job id, outcome |

Audit records are **append-only** (FR-AUD-06). API exposes read-only audit endpoints.

---

## 2. Authentication

### 2.1 Login

| | |
|---|---|
| **Endpoint** | `POST /api/v1/auth/login` |
| **Method** | `POST` |
| **Purpose** | Authenticate user; issue access and refresh tokens |
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
| `user` | `UserSummary` | See §18 |

**Success Codes:** `200`

**Error Codes:**

| Code | HTTP | Condition |
|------|------|-----------|
| `INVALID_CREDENTIALS` | 401 | Wrong username/password — generic message |
| `ACCOUNT_LOCKED` | 403 | Lockout active — include `locked_until` |
| `ACCOUNT_DISABLED` | 403 | User status disabled |
| `RATE_LIMITED` | 429 | Too many attempts from IP |

**Validation Rules:** Rate limit 10/min/IP on login (TECH_STACK).

**Audit Behaviour:** `auth.login_success` or `auth.login_failure` — never log password.

**Idempotency:** N/A

---

### 2.2 Refresh Token

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

### 2.3 Logout

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

### 2.4 Current User

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

### 2.5 Change Own Password

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

## 3. Users

All user management endpoints require **Main Admin** unless noted.

### 3.1 List Users

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

### 3.2 Create User

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

### 3.3 Get User

| | |
|---|---|
| **Endpoint** | `GET /api/v1/users/{user_id}` |
| **Method** | `GET` |
| **Purpose** | Retrieve user by ID |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Success Codes:** `200`, `404`

---

### 3.4 Update User

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

### 3.5 Update User Role

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

### 3.6 Reset User Password

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

### 3.7 Disable User

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

### 3.8 Enable User

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

## 4. Brands

### 4.1 List Brands

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

### 4.2 Create Brand

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

### 4.3 Get Brand

| | |
|---|---|
| **Endpoint** | `GET /api/v1/brands/{brand_id}` |
| **Method** | `GET` |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Success Codes:** `200`, `404`

---

### 4.4 Update Brand

| | |
|---|---|
| **Endpoint** | `PATCH /api/v1/brands/{brand_id}` |
| **Method** | `PATCH` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body:** `name` (optional)

**Success Codes:** `200`, `409`

---

### 4.5 Deactivate Brand

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

### 4.6 Activate Brand

| | |
|---|---|
| **Endpoint** | `POST /api/v1/brands/{brand_id}/activate` |
| **Method** | `POST` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Success Codes:** `200`

---

## 5. Product Models

### 5.1 List Product Models

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

### 5.2 Create Product Model

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
| `display_name` | string | No | Max 128 |

**Response:** `ProductModel` with `status: active`

**Success Codes:** `201`

**Error Codes:** `409` `MODEL_NUMBER_DUPLICATE`

**Audit Behaviour:** `product_model.create`

---

### 5.3 Get Product Model

| | |
|---|---|
| **Endpoint** | `GET /api/v1/product_models/{product_model_id}` |
| **Method** | `GET` |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Response includes:** `id`, `brand_id`, `brand_name`, `model_number`, `display_name`, `status`, `inventory_count`, `created_at`, `updated_at`

**Success Codes:** `200`, `404`

---

### 5.4 Update Product Model

| | |
|---|---|
| **Endpoint** | `PATCH /api/v1/product_models/{product_model_id}` |
| **Method** | `PATCH` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body:** `model_number`, `display_name` (optional fields)

**Validation Rules:** `brand_id` immutable after inventory linked

**Audit Behaviour:** `product_model.update` (if exposed) or `inventory`-level N/A

---

### 5.5 Archive Product Model

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

### 5.6 Restore Product Model

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

### 5.7 Delete Product Model (Conditional)

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

### 5.8 Bulk Archive Product Models

| | |
|---|---|
| **Endpoint** | `POST /api/v1/product_models/bulk/archive` |
| **Method** | `POST` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `product_model_ids` | integer[] | Yes — max 100 per request |

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

### 5.9 Bulk Restore Product Models

| | |
|---|---|
| **Endpoint** | `POST /api/v1/product_models/bulk/restore` |
| **Method** | `POST` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Request/Response:** Same pattern as §5.8

---

## 6. Locations

Reference data required by inventory. Pre-seeded with three locations (FR-LOC-01).

### 6.1 List Locations

| | |
|---|---|
| **Endpoint** | `GET /api/v1/locations` |
| **Method** | `GET` |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Query Parameters:** `is_active`, `page`, `page_size`

**Success Codes:** `200`

---

### 6.2 Create Location

| | |
|---|---|
| **Endpoint** | `POST /api/v1/locations` |
| **Method** | `POST` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Request Body:** `{ "name": string }` — unique, 1–128 chars

**Success Codes:** `201`

---

### 6.3 Get / Update Location

| | |
|---|---|
| **GET** | `GET /api/v1/locations/{location_id}` |
| **PATCH** | `PATCH /api/v1/locations/{location_id}` — `main_admin` |

---

### 6.4 Deactivate / Activate Location

| | |
|---|---|
| **Deactivate** | `POST /api/v1/locations/{location_id}/deactivate` |
| **Activate** | `POST /api/v1/locations/{location_id}/activate` |
| **Required Role** | `main_admin` |

**Validation:** Deactivate rejected if location holds inventory (FR-LOC-03) — `409` `LOCATION_HAS_INVENTORY`

---

## 7. Inventory

### 7.1 Create Inventory Item

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
| `product_model_id` | integer | Yes | Must reference **active** product model (FR-PM-04) |
| `color` | string | Yes | Non-empty; max 64 (BR-22) |
| `configuration` | string | Yes | Free text — CPU/GPU/RAM/storage (BD-02) |
| `location_id` | integer | Yes | Active location |
| `status` | enum | No | `received` or `available` — default per BD-01 open decision |
| `row_version` | — | — | Not on create |

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

### 7.2 Bulk Create Inventory Items

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

### 7.3 Get Inventory Item

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
| `id` | integer |
| `serial_number` | string |
| `product_model_id` | integer |
| `brand_id`, `brand_name` | |
| `model_number` | string |
| `color` | string |
| `configuration` | string |
| `location_id`, `location_name` | |
| `status` | `received`, `available`, `sold` |
| `row_version` | integer |
| `sale` | `SaleSummary` — nullable; present when sold |
| `created_at`, `updated_at` | datetime |
| `created_by` | `UserSummary` |

**Success Codes:** `200`, `404`

---

### 7.4 Get Inventory Item by Serial

| | |
|---|---|
| **Endpoint** | `GET /api/v1/inventory_items/by-serial/{serial_number}` |
| **Method** | `GET` |
| **Purpose** | Exact serial lookup — highest priority search path |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Success Codes:** `200`, `404`

---

### 7.5 List Inventory Items

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
| `status` | Filter by lifecycle status |
| `location_id` | Filter by location |
| `brand_id` | Filter via product model join |
| `product_model_id` | Filter by model |
| `color` | Partial match |
| `serial_number_prefix` | Prefix search |
| `include_archived_models` | boolean — default false for Salesperson |
| `updated_since` | ISO datetime — recently updated |
| `page`, `page_size`, `sort` | Standard — default sort `updated_at:desc` |

**Success Codes:** `200`

---

### 7.6 List Inventory Groups

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
      "status_summary": { "available": 5, "received": 1, "sold": 12 },
      "serials": [ ]
    }
  ]
}
```

**Success Codes:** `200`

---

### 7.7 Update Inventory Item

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
| `color` | Non-empty if provided |
| `configuration` | Non-empty if provided |
| `location_id` | Use movement endpoint for transfers — **rejected here** with `422` `USE_MOVEMENT_ENDPOINT` |
| `product_model_id` | Rare; audited; must be active |
| `row_version` | Required for optimistic locking |

**Immutable:** `serial_number`

**Success Codes:** `200`

**Error Codes:** `409` `ROW_VERSION_CONFLICT`, `422`

**Audit Behaviour:** `inventory.update`

---

### 7.8 Transition Inventory Status

| | |
|---|---|
| **Endpoint** | `POST /api/v1/inventory_items/{inventory_item_id}/transition` |
| **Method** | `POST` |
| **Purpose** | Lifecycle state change (FR-INV-13) |
| **Authentication Required** | Yes |
| **Required Role** | `received→available`: `main_admin`, `admin`; `available→sold`: see Sales §10 |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `to_status` | enum | Yes — `available` from `received` only in this endpoint |
| `row_version` | integer | Yes |

**Allowed via this endpoint:** `received` → `available` only

**Validation Rules:** Invalid transitions — `422` `INVALID_STATUS_TRANSITION`

**Audit Behaviour:** `inventory.transition`

---

## 8. Inventory Movement

### 8.1 Move Inventory Item

| | |
|---|---|
| **Endpoint** | `POST /api/v1/inventory_items/{inventory_item_id}/move` |
| **Method** | `POST` |
| **Purpose** | Transfer unit to new location (FR-MOV-01–03) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `to_location_id` | integer | Yes | Must differ from current |
| `reason` | string | No | Max 512 |
| `row_version` | integer | Yes | |

**Validation Rules:**

- Status must be `available` (LC-04, FR-MOV-06) — `422` `SOLD_ITEM_CANNOT_MOVE`
- `to_location_id` must be active

**Response Body:** Updated `InventoryItemDetail` + `movement` record

**Success Codes:** `200`

**Audit Behaviour:** `inventory.move` + `inventory_movement` insert

**Idempotency:** Same `Idempotency-Key` within 24h returns original result `200`

---

### 8.2 Bulk Move Inventory Items

| | |
|---|---|
| **Endpoint** | `POST /api/v1/inventory_items/bulk/move` |
| **Method** | `POST` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `batch_id` | UUID | No |
| `to_location_id` | integer | Yes — shared destination |
| `reason` | string | No |
| `items` | array | Yes — max **50** |
| `items[].inventory_item_id` | integer | Yes |
| `items[].row_version` | integer | Yes |
| `continue_on_error` | boolean | No — default false |

**Response:** Per-item success/failure summary

**Audit Behaviour:** `inventory.move` per successful item

---

### 8.3 Movement History (Global)

| | |
|---|---|
| **Endpoint** | `GET /api/v1/movements` |
| **Method** | `GET` |
| **Purpose** | Paginated movement log (FR-MOV-04, FR-RPT-03) |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Query Parameters:** `inventory_item_id`, `from_location_id`, `to_location_id`, `performed_by_user_id`, `moved_at_from`, `moved_at_to`, `page`, `page_size`, `sort` (default `moved_at:desc`)

**Response Body:** `Movement[]`

---

### 8.4 Movement History (Per Item)

| | |
|---|---|
| **Endpoint** | `GET /api/v1/inventory_items/{inventory_item_id}/movements` |
| **Method** | `GET` |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Success Codes:** `200`

---

## 9. Search

### 9.1 Combined Search

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
| `q` | string | — | Free-text — serial exact/prefix OR config trigram if no structured filters |
| `serial_number` | string | exact | Highest priority — returns single detail mode |
| `serial_number_prefix` | string | prefix | |
| `brand_id` | integer | exact | |
| `brand_name` | string | partial | |
| `product_model_id` | integer | exact | |
| `model_number` | string | partial | |
| `color` | string | partial | FR-SRH-13 |
| `location_id` | integer | exact | |
| `status` | enum | exact | Comma-separated multi-value |
| `cpu` | string | config trigram | Maps to configuration search |
| `gpu` | string | config trigram | e.g. `4060` |
| `ram` | string | config trigram | e.g. `16GB` |
| `storage` | string | config trigram | |
| `configuration` | string | trigram | General config term (FR-SRH-05/06) |
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

### 9.2 Quick Search (Dashboard)

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

## 10. Sales

### 10.1 Reflect Sale (Manual)

| | |
|---|---|
| **Endpoint** | `POST /api/v1/sales/reflect` |
| **Method** | `POST` |
| **Purpose** | Mark inventory as sold — manual fallback (FR-SLS-04) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin`, `salesperson` |

**Request Body:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `serial_number` | string | Yes* | *Or `inventory_item_id` |
| `inventory_item_id` | integer | Yes* | |
| `customer_name` | string | No | Reference only — not billing |
| `customer_contact` | string | No | |
| `invoice_reference` | string | No | Tally invoice/voucher reference |
| `notes` | string | No | |
| `row_version` | integer | Yes | |

**Validation Rules:**

- Status must be `available` — `422` `INVALID_STATUS_TRANSITION`
- `received` → `sold` blocked (LC rules)

**Response Body (`201`):** `SaleDetail`

**Success Codes:** `201`

**Error Codes:** `404` serial not found, `409` already sold

**Audit Behaviour:** `sale.reflect` + `inventory.transition`

**Idempotency:** `Idempotency-Key` header — replay returns existing sale `200`

---

### 10.2 Reflect Sale (Tally Worker)

| | |
|---|---|
| **Endpoint** | `POST /api/v1/integrations/tally/sales/reflect` |
| **Method** | `POST` |
| **Purpose** | Tally Sync worker applies sale (FR-TLY-03) — **implementation blocked until POC** |
| **Authentication Required** | Yes — service account `tally_sync` |
| **Required Role** | Service: `tally_sync` |

**Request Body:**

| Field | Type | Required |
|-------|------|----------|
| `tally_voucher_number` | string | Yes |
| `serial_number` | string | Yes |
| `sold_at` | datetime | Yes |
| `invoice_reference` | string | No |
| `customer_name` | string | No |
| `raw_payload_hash` | string | No — SHA-256 for audit |

**Success Codes:** `201` (new sale), `200` (idempotent no-op), `404` (`SERIAL_NOT_FOUND` — worker logs skip)

**Idempotency:** `(tally_voucher_number, serial_number)` — mandatory

**Audit Behaviour:** `sale.reflect`; worker also creates `tally_integration_event`

---

### 10.3 Get Sale

| | |
|---|---|
| **Endpoint** | `GET /api/v1/sales/{sale_id}` |
| **Method** | `GET` |
| **Authentication Required** | Yes |
| **Required Role** | Any authenticated user |

**Success Codes:** `200`, `404`

---

### 10.4 List Sale History

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

## 11. Dashboard

### 11.1 KPI Summary

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

### 11.2 Recent Activity

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

## 12. Reports

Supports FR-RPT-01–05. Export formats: JSON in API; file export via separate download endpoints.

### 12.1 Inventory Summary by Location

| | |
|---|---|
| **Endpoint** | `GET /api/v1/reports/inventory-by-location` |
| **Method** | `GET` |
| **Required Role** | `main_admin`, `admin` |

**Query Parameters:** `status` (default `available`)

---

### 12.2 Sold Inventory Report

| | |
|---|---|
| **Endpoint** | `GET /api/v1/reports/sold-inventory` |
| **Method** | `GET` |
| **Required Role** | `main_admin`, `admin` |

**Query Parameters:** `sold_at_from`, `sold_at_to`, `location_id`, `brand_id`, `page`, `page_size`

---

### 12.3 Stock Count Report

| | |
|---|---|
| **Endpoint** | `GET /api/v1/reports/stock-count` |
| **Method** | `GET` |
| **Purpose** | Available units by brand/model/location (FR-RPT-05) |
| **Required Role** | `main_admin`, `admin` |

---

### 12.4 Export Report to Excel

| | |
|---|---|
| **Endpoint** | `POST /api/v1/reports/{report_type}/export` |
| **Method** | `POST` |
| **Purpose** | Generate downloadable Excel report (FR-RPT-04) |
| **Required Role** | `main_admin`, `admin` |

**Path Parameters:** `report_type` — `inventory-by-location`, `sold-inventory`, `stock-count`, `movements`

**Response:** `202` with `{ "download_url": "...", "expires_at": "..." }` or streaming `200` with `Content-Disposition` — **implementation choice; prefer async job for large reports**

---

## 13. Excel Sync

Excel Sync is **export only** — never imports (BR-08, FR-XLS-06). API enqueues jobs; worker executes (SYSTEM_ARCHITECTURE §14.2).

### 13.1 Trigger Excel Sync

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

### 13.2 Excel Sync Status

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

### 13.3 Excel Sync History

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

### 13.4 Get Sync Job

| | |
|---|---|
| **Endpoint** | `GET /api/v1/sync/jobs/{sync_job_id}` |
| **Method** | `GET` |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin`, `admin` |

---

### 13.5 Worker: List Pending Jobs

| | |
|---|---|
| **Endpoint** | `GET /api/v1/sync/jobs/pending` |
| **Method** | `GET` |
| **Purpose** | Excel worker polls for work |
| **Authentication Required** | Yes — service account `excel_sync` |
| **Required Role** | Service: `excel_sync` |

**Query Parameters:** `job_type=excel_export`, `limit` (default 1)

---

### 13.6 Worker: Claim / Start Job

| | |
|---|---|
| **Endpoint** | `POST /api/v1/sync/jobs/{sync_job_id}/start` |
| **Method** | `POST` |
| **Purpose** | Worker marks job `running` |
| **Required Role** | Service: `excel_sync` |

**Success Codes:** `200`, `409` if already claimed

---

### 13.7 Worker: Complete Job

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

### 13.8 Worker: Export Data Page

| | |
|---|---|
| **Endpoint** | `GET /api/v1/sync/excel/export` |
| **Method** | `GET` |
| **Purpose** | Paginated inventory export for worker assembly (FR-XLS-03) |
| **Authentication Required** | Yes — service account `excel_sync` |
| **Required Role** | Service: `excel_sync` |

**Query Parameters:** `cursor`, `page_size` (default 500, max 500)

**Response columns per row:** `brand_name`, `model_number`, `serial_number`, `color`, `configuration`, `location_name`, `status`

**Success Codes:** `200`

---

## 14. Tally Integration

> **Implementation blocked** until Tally POC checklist passes (SYSTEM_ARCHITECTURE §14.3.1). API contract is defined for implementation readiness.

### 14.1 Integration Status

| | |
|---|---|
| **Endpoint** | `GET /api/v1/integrations/tally/status` |
| **Method** | `GET` |
| **Purpose** | Connection health and last poll (FR-TLY-05, FR-SET-06) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Response Body:**

```json
{
  "data": {
    "enabled": true,
    "last_poll_at": "2026-06-27T10:29:00Z",
    "last_success_at": "2026-06-27T10:29:00Z",
    "last_error": null,
    "consecutive_failures": 0,
    "sales_applied_today": 14,
    "poc_completed": false
  }
}
```

---

### 14.2 Tally Event History

| | |
|---|---|
| **Endpoint** | `GET /api/v1/integrations/tally/events` |
| **Method** | `GET` |
| **Purpose** | Integration event log (FR-TLY-04) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Query Parameters:**

| Parameter | Description |
|-----------|-------------|
| `event_type` | `poll`, `voucher_received`, `sale_applied`, `sale_skipped`, `error` |
| `outcome` | `success`, `skipped`, `failed` |
| `serial_number` | |
| `tally_voucher_number` | |
| `created_at_from`, `created_at_to` | |
| `page`, `page_size` | |

**Response Body:** `TallyIntegrationEvent[]`

---

### 14.3 Get Tally Event

| | |
|---|---|
| **Endpoint** | `GET /api/v1/integrations/tally/events/{event_id}` |
| **Method** | `GET` |
| **Required Role** | `main_admin` |

---

### 14.4 Retry Failed Event

| | |
|---|---|
| **Endpoint** | `POST /api/v1/integrations/tally/events/{event_id}/retry` |
| **Method** | `POST` |
| **Purpose** | Re-attempt sale reflection for failed/skipped voucher (FR-TLY-08) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Validation Rules:** Only events with `outcome=failed` and retryable error codes

**Response Body:** New processing result or `SaleDetail`

**Success Codes:** `200`, `201`, `404`, `409`

**Audit Behaviour:** New `tally_integration_event` + possible `sale.reflect`

**Idempotency:** Underlying sale reflection remains idempotent

---

### 14.5 Worker: Record Tally Event

| | |
|---|---|
| **Endpoint** | `POST /api/v1/integrations/tally/events` |
| **Method** | `POST` |
| **Purpose** | Tally worker logs poll/voucher outcomes |
| **Required Role** | Service: `tally_sync` |

**Request Body:** `TallyIntegrationEventCreate` — event_type, outcome, voucher, serial, error fields

**Success Codes:** `201`

---

## 15. Audit

### 15.1 Search Audit Logs

| | |
|---|---|
| **Endpoint** | `GET /api/v1/audit_logs` |
| **Method** | `GET` |
| **Purpose** | Search and filter audit trail (FR-AUD-05) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Query Parameters:**

| Parameter | Description |
|-----------|-------------|
| `audit_action` | e.g. `inventory.create` |
| `entity_type` | e.g. `inventory_item` |
| `entity_id` | |
| `entity_identifier` | Serial number search |
| `actor_user_id` | |
| `created_at_from`, `created_at_to` | |
| `client_platform` | |
| `page`, `page_size`, `sort` | Default `created_at:desc` |

**Response Body:** `AuditLogEntry[]`

**Success Codes:** `200`

**Audit Behaviour:** Read-only — no audit of audit reads

---

### 15.2 Get Audit Log Entry

| | |
|---|---|
| **Endpoint** | `GET /api/v1/audit_logs/{audit_log_id}` |
| **Method** | `GET` |
| **Purpose** | Full detail including before/after state (FR-AUD-04) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Response Body:** `AuditLogDetail` with `before_state`, `after_state` JSON

**Success Codes:** `200`, `404`

---

### 15.3 Audit History for Entity

| | |
|---|---|
| **Endpoint** | `GET /api/v1/audit_logs/by-entity/{entity_type}/{entity_id}` |
| **Method** | `GET` |
| **Required Role** | `main_admin` |

---

## 16. Settings

### 16.1 List All Settings

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

### 16.2 Get Setting

| | |
|---|---|
| **Endpoint** | `GET /api/v1/settings/{setting_key}` |
| **Method** | `GET` |
| **Required Role** | `main_admin` |

---

### 16.3 Update Setting

| | |
|---|---|
| **Endpoint** | `PATCH /api/v1/settings/{setting_key}` |
| **Method** | `PATCH` |
| **Required Role** | `main_admin` |

**Request Body:** `{ "setting_value": string | integer | boolean | object }`

**Validation Rules:** Type must match `value_type` stored for key

**Audit Behaviour:** `setting.update`

---

### 16.4 System Settings (Grouped)

| | |
|---|---|
| **Endpoint** | `GET /api/v1/settings/groups/system` |
| **PATCH** | `PATCH /api/v1/settings/groups/system` |

**Keys:** `business_display_name`, `barcode_auto_submit`, `session_timeout_minutes`, `lockout_threshold`, `lockout_duration_minutes`

**Required Role:** `main_admin`

---

### 16.5 Excel Configuration (Grouped)

| | |
|---|---|
| **Endpoint** | `GET /api/v1/settings/groups/excel` |
| **PATCH** | `PATCH /api/v1/settings/groups/excel` |

**Keys:** `excel_sync_cron`, `excel_export_path`, `excel_sync_enabled`

**Required Role:** `main_admin`

---

### 16.6 Tally Configuration (Grouped)

| | |
|---|---|
| **Endpoint** | `GET /api/v1/settings/groups/tally` |
| **PATCH** | `PATCH /api/v1/settings/groups/tally` |

**Keys:** `tally_poll_interval_seconds`, `tally_host`, `tally_port`, `tally_enabled`

**Required Role:** `main_admin`

---

### 16.7 User Theme Preference

| | |
|---|---|
| **Endpoint** | `PATCH /api/v1/auth/me/preferences` |
| **Method** | `PATCH` |
| **Purpose** | User theme preference (FR-SET-05) |
| **Required Role** | Any authenticated user |

**Request Body:** `{ "theme_preference": "light" | "dark" | "system" }`

---

## 17. Health

Health endpoints are **unversioned** — used by monitoring and deployment verification.

### 17.1 Health (Liveness)

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

### 17.2 Readiness

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

### 17.3 Version

| | |
|---|---|
| **Endpoint** | `GET /health/version` |
| **Method** | `GET` |
| **Purpose** | Build and API version metadata |
| **Authentication Required** | No |

---

### 17.4 Integration Health

| | |
|---|---|
| **Endpoint** | `GET /health/integrations` |
| **Method** | `GET` |
| **Purpose** | Last sync timestamps and failure counts (FR-SET-06) |
| **Authentication Required** | Yes |
| **Required Role** | `main_admin` |

**Response Body:** Excel and Tally summary — same fields as §13.2 and §14.1

---

## 18. Shared Schemas

Reusable object definitions referenced across endpoints.

### 18.1 UserSummary

| Field | Type |
|-------|------|
| `id` | integer |
| `username` | string |
| `display_name` | string \| null |
| `role` | enum |
| `status` | enum |

### 18.2 Brand

| Field | Type |
|-------|------|
| `id` | integer |
| `name` | string |
| `is_active` | boolean |
| `created_at`, `updated_at` | datetime |

### 18.3 ProductModel

| Field | Type |
|-------|------|
| `id` | integer |
| `brand_id` | integer |
| `brand_name` | string |
| `model_number` | string |
| `display_name` | string \| null |
| `status` | `active` \| `archived` |
| `created_at`, `updated_at` | datetime |

### 18.4 Location

| Field | Type |
|-------|------|
| `id` | integer |
| `name` | string |
| `is_active` | boolean |

### 18.5 InventoryItemDetail

See §7.3. **Excluded fields:** `purchase_date`, `purchase_cost`, `remarks`.

### 18.6 InventoryItemSummary

Subset for lists: `id`, `serial_number`, `brand_name`, `model_number`, `color`, `configuration`, `location_name`, `status`, `updated_at`

### 18.7 Movement

| Field | Type |
|-------|------|
| `id` | integer |
| `inventory_item_id` | integer |
| `serial_number` | string |
| `from_location_id`, `from_location_name` | |
| `to_location_id`, `to_location_name` | |
| `performed_by` | UserSummary |
| `reason` | string \| null |
| `moved_at` | datetime |

### 18.8 SaleDetail

| Field | Type |
|-------|------|
| `id` | integer |
| `inventory_item_id` | integer |
| `serial_number` | string |
| `sale_source` | `manual` \| `tally` |
| `sold_at` | datetime |
| `recorded_by` | UserSummary \| null |
| `customer_name`, `customer_contact` | string \| null |
| `invoice_reference` | string \| null |
| `tally_voucher_number` | string \| null |
| `notes` | string \| null |
| `created_at` | datetime |

### 18.9 SyncJob

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

### 18.10 TallyIntegrationEvent

| Field | Type |
|-------|------|
| `id` | integer |
| `event_type` | enum |
| `outcome` | enum |
| `tally_voucher_number` | string \| null |
| `serial_number` | string \| null |
| `inventory_item_id` | integer \| null |
| `error_code`, `error_message` | string \| null |
| `correlation_id` | string |
| `created_at` | datetime |

### 18.11 AuditLogEntry

| Field | Type |
|-------|------|
| `id` | integer |
| `audit_action` | string |
| `actor` | UserSummary \| null |
| `actor_service` | string \| null |
| `entity_type` | string |
| `entity_id` | integer |
| `entity_identifier` | string \| null |
| `client_platform` | string \| null |
| `request_id` | string |
| `created_at` | datetime |

### 18.12 SystemSetting

| Field | Type |
|-------|------|
| `setting_key` | string |
| `setting_value` | string |
| `value_type` | enum |
| `description` | string \| null |
| `category` | string |
| `updated_at` | datetime |

---

## 19. Error Catalogue

Standard `error.code` values for Version 1.

| Code | HTTP | Description |
|------|------|-------------|
| `VALIDATION_ERROR` | 422 | Generic validation failure |
| `INVALID_CREDENTIALS` | 401 | Login failed |
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
| `MODEL_NUMBER_DUPLICATE` | 409 | Unique per brand |
| `BRAND_NAME_DUPLICATE` | 409 | |
| `USERNAME_DUPLICATE` | 409 | |
| `LAST_MAIN_ADMIN` | 409 | FR-USER-03 |
| `INVALID_STATUS_TRANSITION` | 422 | Lifecycle violation |
| `SOLD_ITEM_CANNOT_MOVE` | 422 | LC-04 |
| `ROW_VERSION_CONFLICT` | 409 | Optimistic lock |
| `USE_MOVEMENT_ENDPOINT` | 422 | Location change via PATCH rejected |
| `ALREADY_SOLD` | 409 | Sale idempotency / duplicate |
| `RATE_LIMITED` | 429 | Login throttled |
| `INVALID_REFRESH_TOKEN` | 401 | |
| `REFRESH_TOKEN_REUSE` | 401 | Token rotation attack |
| `WEAK_PASSWORD` | 422 | Password policy |
| `SERVICE_UNAVAILABLE` | 503 | Readiness failure |
| `INTERNAL_ERROR` | 500 | Unexpected |

---

## 20. Permission Reference

Permissions map to PRD §17.2 matrix. Enforced via `packages/auth/permissions.py`.

| Permission Code | Roles | Endpoints |
|-----------------|-------|-----------|
| `auth:login` | all | §2 |
| `users:manage` | main_admin | §3 |
| `brands:read` | all | GET brands |
| `brands:write` | main_admin, admin | POST/PATCH brands |
| `product_models:read` | all | GET product_models |
| `product_models:write` | main_admin, admin | Create/update |
| `product_models:archive` | main_admin | Archive/restore/delete/bulk |
| `locations:read` | all | GET locations |
| `locations:write` | main_admin | POST/PATCH locations |
| `inventory:read` | all | GET inventory, search |
| `inventory:write` | main_admin, admin | Create/update/bulk |
| `inventory:transition` | main_admin, admin | received→available |
| `movement:execute` | main_admin, admin | §8 |
| `movement:read` | all | GET movements |
| `sales:reflect` | all | Manual sale §10.1 |
| `sales:read` | all | GET sales |
| `dashboard:read` | all | §11 |
| `reports:read` | main_admin, admin | §12 |
| `sync:trigger` | main_admin, admin | §13.1–13.4 |
| `sync:worker` | excel_sync service | §13.5–13.8 |
| `tally:worker` | tally_sync service | §14.2, §14.5, §10.2 |
| `tally:admin` | main_admin | §14.1, §14.3–14.4 |
| `audit:read` | main_admin | §15 |
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
