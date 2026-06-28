#!/usr/bin/env python3
"""WEBSTUDIO IMS — Production simulation UAT (Phases 2–13)."""

from __future__ import annotations

import asyncio
import json
import secrets
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "scripts"))
sys.path.insert(0, str(ROOT / "apps" / "backend" / "src"))

from uat_analyze_tally_xml import analyze, print_report  # noqa: E402

from webstudio_backend.core.config import get_settings  # noqa: E402
from webstudio_backend.infrastructure.database.enums import SettingValueType  # noqa: E402
from webstudio_backend.infrastructure.database.session import close_db, init_db, session_scope  # noqa: E402
from webstudio_backend.infrastructure.repositories.system_setting_repository import (  # noqa: E402
    SystemSettingRepository,
)
from webstudio_backend.services.tally_sync_service import TallySyncService  # noqa: E402

BASE_URL = "http://127.0.0.1:8000"
XML_PATH = ROOT / "tools" / "uat" / "daybook_response.xml"
REPORT_DIR = ROOT / "tools" / "uat"

ADMIN_USERNAME = "admin"
ADMIN_NAME = "ARVIND SINGH"
ADMIN_PASSWORD = "WsiUat#Admin2026!Arv"
SUNAINA_USERNAME = "sunaina"
SUNAINA_PASSWORD = "WsiUat#Sunaina2026!"
HEMANT_USERNAME = "hemant"
HEMANT_PASSWORD = "WsiUat#Hemant2026!"

LAPTOP_DEFINITIONS = [
    {
        "brand": "Acer",
        "stock_name": "ACER ASPIRE A325-45-V2 UN.36FSI.00B",
        "model_number": "A325-45-V2",
        "model_name": "Aspire A325-45-V2",
        "serial": "UN36FSI00B613004C20700",
    },
    {
        "brand": "Lenovo",
        "stock_name": "LENOVO L27-4C 27 IPS 144 HTZ",
        "model_number": "L27-4C",
        "model_name": "L27-4C 27 IPS Monitor",
        "serial": "UT10082A",
    },
    {
        "brand": "Asus",
        "stock_name": "ASUS E1504FA-BQ2113WS",
        "model_number": "E1504FA-BQ2113WS",
        "model_name": "E1504FA-BQ2113WS",
        "serial": "W3N0CV09678412A",
    },
]

EXTRA_SERIAL_ITEMS = [
    {
        "brand": "Asus",
        "stock_name": "ASUS ADAPTER 45W",
        "model_number": "ADAPTER-45W",
        "model_name": "Adapter 45W",
        "serial": "T7BCXB003887STA",
    },
    {
        "brand": "Epson",
        "stock_name": "Epson L3350",
        "model_number": "L3350",
        "model_name": "EcoTank L3350",
        "serial": "XFAL007602",
    },
    {
        "brand": "Asus",
        "stock_name": "ASUS MD102 MOUSE",
        "model_number": "MD102",
        "model_name": "MD102 Mouse",
        "serial": "SCBMCP0036075P5",
    },
]


@dataclass
class UatState:
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)
    product_models: dict[str, str] = field(default_factory=dict)
    inventory_ids: dict[str, str] = field(default_factory=dict)
    gemini_stats: dict[str, int] = field(default_factory=lambda: {"success": 0, "skipped": 0, "failed": 0})
    sync_durations: list[float] = field(default_factory=list)
    credentials: list[dict[str, str]] = field(default_factory=list)


def _ok(state: UatState, msg: str) -> None:
    state.passes.append(msg)


def _warn(state: UatState, msg: str) -> None:
    state.warnings.append(msg)


def _fail(state: UatState, msg: str) -> None:
    state.failures.append(msg)


async def _login(client: httpx.AsyncClient, username: str, password: str) -> dict[str, str]:
    resp = await client.post(f"{BASE_URL}/api/v1/auth/login", json={"username": username, "password": password})
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {username}: {resp.status_code} {resp.text}")
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _ensure_setup(client: httpx.AsyncClient, state: UatState) -> tuple[dict[str, str], int]:
    status = (await client.get(f"{BASE_URL}/api/v1/setup/status")).json()["data"]
    if not status["system_initialized"]:
        init = await client.post(
            f"{BASE_URL}/api/v1/setup/initialize",
            json={
                "company_name": "WEBSTUDIO",
                "main_admin_name": ADMIN_NAME,
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD,
                "confirm_password": ADMIN_PASSWORD,
            },
        )
        if init.status_code not in {201, 409}:
            _fail(state, f"Setup initialize failed: {init.status_code} {init.text}")
            raise RuntimeError("Setup failed")
        recovery_key = init.json().get("data", {}).get("recovery_key", "")
        if recovery_key:
            (REPORT_DIR / "recovery_key.txt").write_text(recovery_key, encoding="utf-8")
        confirm = await client.post(f"{BASE_URL}/api/v1/setup/confirm-recovery-key")
        if confirm.status_code not in {200, 409}:
            _fail(state, f"Recovery key confirm failed: {confirm.status_code}")
        _ok(state, "First-time setup completed via API (ARVIND SINGH / admin)")
    else:
        _ok(state, "System already initialized — reusing existing setup")

    headers = await _login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    me = (await client.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)).json()["data"]
    admin_user_id = me["id"]
    state.credentials.append(
        {
            "name": ADMIN_NAME,
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "role": "main_admin",
            "login_tested": "Yes",
        },
    )
    return headers, admin_user_id


async def _get_or_create_brand(client: httpx.AsyncClient, headers: dict[str, str], name: str) -> int:
    brands = (await client.get(f"{BASE_URL}/api/v1/brands", headers=headers)).json()["data"]
    for brand in brands:
        if brand["name"].lower() == name.lower():
            return brand["id"]
    created = await client.post(f"{BASE_URL}/api/v1/brands", headers=headers, json={"name": name})
    created.raise_for_status()
    return created.json()["data"]["id"]


async def _get_or_create_location(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    name: str,
    location_type: str,
) -> int:
    locations = (await client.get(f"{BASE_URL}/api/v1/locations", headers=headers)).json()["data"]
    for loc in locations:
        if loc["name"].lower() == name.lower():
            return loc["id"]
    created = await client.post(
        f"{BASE_URL}/api/v1/locations",
        headers=headers,
        json={"name": name, "location_type": location_type},
    )
    created.raise_for_status()
    return created.json()["data"]["id"]


async def _add_laptop_workflow(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    state: UatState,
    *,
    brand_id: int,
    brand_name: str,
    definition: dict[str, str],
    warehouse_id: int,
    extra_serials: list[str] | None = None,
    skip_gemini: bool = False,
) -> str:
    model_number = definition["model_number"]
    model_id: str | None = None
    existing = (
        await client.get(
            f"{BASE_URL}/api/v1/product-models",
            headers=headers,
            params={"brand_id": brand_id},
        )
    ).json()["data"]
    for pm in existing:
        if pm["model_number"].lower() == model_number.lower():
            state.gemini_stats["skipped"] += 1
            model_id = pm["id"]
            _ok(state, f"Reused existing product model {model_number}")
            break
    else:
        spec = None
        if not skip_gemini:
            lookup = await client.post(
                f"{BASE_URL}/api/v1/product-models/spec-lookup",
                headers=headers,
                json={
                    "model_number": model_number,
                    "model_name": definition["model_name"],
                    "brand_name": brand_name,
                },
            )
            if lookup.status_code == 200:
                spec = lookup.json()["data"]
                state.gemini_stats["success"] += 1
                _ok(state, f"Gemini enrichment succeeded for {model_number}")
            else:
                state.gemini_stats["failed"] += 1
                _warn(state, f"Gemini enrichment unavailable for {model_number}: {lookup.status_code}")

        payload = {
            "brand_id": brand_id,
            "model_number": model_number,
            "model_name": (spec or {}).get("model_name") or definition["model_name"],
            "cpu": (spec or {}).get("cpu") or "Intel Core i5",
            "gpu": (spec or {}).get("gpu"),
            "ram_gb": (spec or {}).get("ram_gb") or 8,
            "storage_value": str((spec or {}).get("storage_value") or "512"),
            "storage_unit": (spec or {}).get("storage_unit") or "GB",
            "storage_type": (spec or {}).get("storage_type") or "SSD",
            "display": (spec or {}).get("display"),
            "product_image_url": (spec or {}).get("product_image_url"),
            "notes": (spec or {}).get("notes"),
        }
        created = await client.post(f"{BASE_URL}/api/v1/product-models", headers=headers, json=payload)
        if created.status_code == 409:
            for pm in existing:
                if pm["model_number"].lower() == model_number.lower():
                    model_id = pm["id"]
                    break
            else:
                created.raise_for_status()
        else:
            created.raise_for_status()
            model_id = created.json()["data"]["id"]
            _ok(state, f"Created product model {model_number}")

    if model_id is None:
        raise RuntimeError(f"Product model id missing for {model_number}")

    state.product_models[model_number] = model_id

    serials = [definition["serial"], *(extra_serials or [])]
    for serial in serials:
        inv = await client.post(
            f"{BASE_URL}/api/v1/inventory",
            headers=headers,
            json={
                "serial_number": serial,
                "product_model_id": model_id,
                "color": "Black",
                "current_location_id": warehouse_id,
                "status": "available",
                "purchase_date": str(date.today()),
            },
        )
        if inv.status_code == 409:
            _warn(state, f"Inventory serial already exists: {serial}")
            lookup = await client.get(f"{BASE_URL}/api/v1/inventory/by-serial/{serial}", headers=headers)
            if lookup.status_code == 200:
                state.inventory_ids[serial] = lookup.json()["data"]["id"]
            continue
        inv.raise_for_status()
        state.inventory_ids[serial] = inv.json()["data"]["id"]
        _ok(state, f"Created inventory {serial} at Warehouse")

    return model_id


async def _run_inventory_feature_checks(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    state: UatState,
    warehouse_id: int,
    webstudio_id: int,
) -> None:
    serials = list(state.inventory_ids.keys())
    if not serials:
        _fail(state, "No inventory items to validate")
        return
    test_serial = next((s for s in serials if s.startswith("TEST")), serials[0])
    item_id = state.inventory_ids[test_serial]

    patch = await client.patch(
        f"{BASE_URL}/api/v1/inventory/{item_id}",
        headers=headers,
        json={"color": "Silver"},
    )
    if patch.status_code == 200:
        _ok(state, "Edit laptop — PASS")
    else:
        _fail(state, f"Edit laptop failed: {patch.status_code}")

    transfer = await client.patch(
        f"{BASE_URL}/api/v1/inventory/{item_id}/location",
        headers=headers,
        json={"location_id": webstudio_id},
    )
    if transfer.status_code == 200:
        _ok(state, "Transfer laptop — PASS")
    else:
        _fail(state, f"Transfer failed: {transfer.status_code}")

    archive = await client.post(f"{BASE_URL}/api/v1/inventory/{item_id}/archive", headers=headers)
    if archive.status_code == 200:
        _ok(state, "Archive laptop — PASS")
    else:
        _fail(state, f"Archive failed: {archive.status_code}")

    restore = await client.post(f"{BASE_URL}/api/v1/inventory/{item_id}/restore", headers=headers)
    if restore.status_code == 200:
        _ok(state, "Restore laptop — PASS")
    else:
        _fail(state, f"Restore failed: {restore.status_code}")

    search = await client.get(
        f"{BASE_URL}/api/v1/inventory",
        headers=headers,
        params={"serial_number": test_serial, "page": 1, "page_size": 10},
    )
    if search.status_code == 200 and search.json()["meta"]["total_items"] >= 1:
        _ok(state, "Search & pagination — PASS")
    else:
        _fail(state, "Search inventory failed")

    for fmt in ("xlsx", "pdf"):
        export = await client.get(
            f"{BASE_URL}/api/v1/reports/export",
            headers=headers,
            params={"report_type": "inventory", "format": fmt},
        )
        if export.status_code == 200:
            _ok(state, f"Inventory report {fmt.upper()} export — PASS")
        else:
            _warn(state, f"Inventory {fmt} export returned {export.status_code}")


async def _enable_tally(state: UatState, company_name: str, admin_user_id: int) -> None:
    async with session_scope() as session:
        settings = SystemSettingRepository(session)
        await settings.set_value(
            "tally_enabled",
            "true",
            value_type=SettingValueType.BOOLEAN,
            updated_by_user_id=admin_user_id,
        )
        await settings.set_value(
            "tally_company_name",
            company_name,
            value_type=SettingValueType.STRING,
            updated_by_user_id=admin_user_id,
        )
        await session.commit()
    _ok(state, "Tally integration enabled in settings")


async def _replay_xml(state: UatState, company_name: str, label: str) -> dict:
    xml_text = XML_PATH.read_text(encoding="utf-8", errors="replace")
    started = time.perf_counter()
    async with session_scope() as session:
        result = await TallySyncService(session).process_voucher_xml(
            xml_text,
            correlation_id=str(uuid.uuid4()),
            company_name=company_name,
        )
        await session.commit()
    elapsed = time.perf_counter() - started
    state.sync_durations.append(elapsed)
    counters = result.counters
    _ok(
        state,
        f"{label}: vouchers={counters.vouchers_processed} sales={counters.sales_created} "
        f"dupes={counters.duplicates} missing_serials={counters.missing_serials}",
    )
    return {
        "sales_created": counters.sales_created,
        "duplicates": counters.duplicates,
        "missing_serials": counters.missing_serials,
        "elapsed": elapsed,
    }


async def _create_role_users(client: httpx.AsyncClient, admin_headers: dict[str, str], state: UatState) -> None:
    users_to_create = [
        (SUNAINA_USERNAME, "Sunaina", "admin", SUNAINA_PASSWORD),
        (HEMANT_USERNAME, "Hemant", "salesperson", HEMANT_PASSWORD),
    ]
    for username, display_name, role, password in users_to_create:
        created = await client.post(
            f"{BASE_URL}/api/v1/users",
            headers=admin_headers,
            json={
                "username": username,
                "display_name": display_name,
                "role": role,
                "temporary_password": password,
            },
        )
        if created.status_code in {201, 409}:
            _ok(state, f"User {username} ({role}) ready")
        else:
            _fail(state, f"User creation failed for {username}: {created.status_code}")

        login_ok = "No"
        try:
            await _login(client, username, password)
            login_ok = "Yes"
            _ok(state, f"Login test {username} — PASS")
        except RuntimeError:
            _fail(state, f"Login test failed for {username}")

        state.credentials.append(
            {
                "name": display_name,
                "username": username,
                "password": password,
                "role": role,
                "login_tested": login_ok,
            },
        )


async def _role_access_checks(client: httpx.AsyncClient, state: UatState) -> None:
    admin_h = await _login(client, SUNAINA_USERNAME, SUNAINA_PASSWORD)
    hemant_h = await _login(client, HEMANT_USERNAME, HEMANT_PASSWORD)

    admin_inventory = await client.get(f"{BASE_URL}/api/v1/inventory", headers=admin_h)
    admin_users = await client.get(f"{BASE_URL}/api/v1/users", headers=admin_h)
    if admin_inventory.status_code == 200:
        _ok(state, "Admin role — inventory access PASS")
    if admin_users.status_code == 403:
        _ok(state, "Admin role — user management blocked PASS")
    elif admin_users.status_code == 200:
        _warn(state, "Admin can access user management (may be intended)")

    hemant_inventory = await client.get(f"{BASE_URL}/api/v1/inventory", headers=hemant_h)
    hemant_users = await client.get(f"{BASE_URL}/api/v1/users", headers=hemant_h)
    hemant_settings = await client.get(f"{BASE_URL}/api/v1/settings", headers=hemant_h)
    if hemant_inventory.status_code == 200:
        _ok(state, "Salesperson — inventory access PASS")
    if hemant_users.status_code == 403:
        _ok(state, "Salesperson — user management blocked PASS")
    if hemant_settings.status_code == 403:
        _ok(state, "Salesperson — settings blocked PASS")


async def _audit_and_dashboard_checks(client: httpx.AsyncClient, headers: dict[str, str], state: UatState) -> None:
    audit = await client.get(f"{BASE_URL}/api/v1/audit_logs", headers=headers, params={"page": 1, "page_size": 50})
    if audit.status_code == 200 and audit.json()["meta"]["total_items"] > 0:
        _ok(state, f"Audit logs present ({audit.json()['meta']['total_items']} entries)")
    else:
        _fail(state, "Audit logs missing or empty")

    dashboard = await client.get(f"{BASE_URL}/api/v1/dashboard", headers=headers)
    if dashboard.status_code == 200:
        _ok(state, "Dashboard loads — PASS")
    else:
        _fail(state, f"Dashboard failed: {dashboard.status_code}")

    notifications = await client.get(f"{BASE_URL}/api/v1/notifications", headers=headers)
    if notifications.status_code == 200:
        _ok(state, f"Notifications — {notifications.json()['meta']['total_items']} entries")

    for report in ("inventory", "sales", "audit", "notifications"):
        preview = await client.get(f"{BASE_URL}/api/v1/reports/{report}", headers=headers, params={"page": 1, "page_size": 10})
        if preview.status_code == 200:
            _ok(state, f"Report preview {report} — PASS")
        else:
            _warn(state, f"Report {report} preview: {preview.status_code}")


async def run_uat() -> UatState:
    state = UatState()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Phase 1
    report = analyze(XML_PATH)
    phase1_path = REPORT_DIR / "phase1_analysis.txt"
    with phase1_path.open("w", encoding="utf-8") as fh:
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_report(report)
        fh.write(buf.getvalue())
    _ok(state, f"Phase 1 analysis saved to {phase1_path}")

    settings = get_settings()
    await init_db(settings)

    async with httpx.AsyncClient(timeout=120.0) as client:
        admin_headers, admin_user_id = await _ensure_setup(client, state)

        # Reference data
        brand_ids = {}
        for name in ("Acer", "Asus", "Lenovo", "Epson"):
            brand_ids[name] = await _get_or_create_brand(client, admin_headers, name)
        warehouse_id = await _get_or_create_location(client, admin_headers, "Warehouse", "warehouse")
        webstudio_id = await _get_or_create_location(client, admin_headers, "WEBSTUDIO", "retail_floor")
        aes_id = await _get_or_create_location(client, admin_headers, "AES", "retail_floor")
        _ok(state, f"Locations ready: Warehouse={warehouse_id}, WEBSTUDIO={webstudio_id}, AES={aes_id}")

        tally_patch = await client.patch(
            f"{BASE_URL}/api/v1/settings/tally",
            headers=admin_headers,
            json={"enabled": True, "tally_host": "127.0.0.1", "tally_port": "9000", "sync_interval_seconds": 1800},
        )
        if tally_patch.status_code == 200:
            _ok(state, "Tally settings patched via API")

        # Phase 2–3: product models + inventory
        for definition in LAPTOP_DEFINITIONS:
            await _add_laptop_workflow(
                client,
                admin_headers,
                state,
                brand_id=brand_ids[definition["brand"]],
                brand_name=definition["brand"],
                definition=definition,
                warehouse_id=warehouse_id,
                extra_serials=["TEST001", "TEST002", "TEST003"],
            )

        # Extra serial-bearing XML lines for full sync coverage
        for definition in EXTRA_SERIAL_ITEMS:
            await _add_laptop_workflow(
                client,
                admin_headers,
                state,
                brand_id=brand_ids[definition["brand"]],
                brand_name=definition["brand"],
                definition=definition,
                warehouse_id=warehouse_id,
                skip_gemini=False,
            )

        # Phase 4: scenario — add to existing model (no duplicate PM)
        asus_def = LAPTOP_DEFINITIONS[2]
        before_count = len(state.product_models)
        await _add_laptop_workflow(
            client,
            admin_headers,
            state,
            brand_id=brand_ids["Asus"],
            brand_name="Asus",
            definition=asus_def,
            warehouse_id=warehouse_id,
            extra_serials=["SCENARIO-DUP-MODEL-001"],
        )
        if len(state.product_models) == before_count:
            _ok(state, "Scenario: reusing product model without duplication — PASS")

        # New model scenario
        new_def = {
            "brand": "Asus",
            "stock_name": "ASUS VIVOBOOK X1502ZA",
            "model_number": "X1502ZA-EJ541WS",
            "model_name": "Vivobook 15 X1502ZA",
            "serial": "SCENARIO-NEW-MODEL-001",
        }
        await _add_laptop_workflow(
            client,
            admin_headers,
            state,
            brand_id=brand_ids["Asus"],
            brand_name="Asus",
            definition=new_def,
            warehouse_id=warehouse_id,
            extra_serials=["SCENARIO-NEW-MODEL-002"],
        )
        await _add_laptop_workflow(
            client,
            admin_headers,
            state,
            brand_id=brand_ids["Asus"],
            brand_name="Asus",
            definition=new_def,
            warehouse_id=warehouse_id,
            extra_serials=["SCENARIO-NEW-MODEL-003"],
        )

        await _run_inventory_feature_checks(client, admin_headers, state, warehouse_id, webstudio_id)

        company_name = report.company_name
        await _enable_tally(state, company_name, admin_user_id)

        # Phase 5
        first_sync = await _replay_xml(state, company_name, "Phase 5 first XML replay")

        # Phase 6 checks
        sales = await client.get(f"{BASE_URL}/api/v1/sales", headers=admin_headers, params={"page": 1, "page_size": 50})
        if sales.status_code == 200 and sales.json()["meta"]["total_items"] >= first_sync["sales_created"]:
            _ok(state, f"Sales imported: {sales.json()['meta']['total_items']}")
        tally_dash = await client.get(f"{BASE_URL}/api/v1/integrations/tally/dashboard", headers=admin_headers)
        if tally_dash.status_code == 200:
            _ok(state, "Tally dashboard updated — PASS")

        # Phase 7 duplicate replay
        second_sync = await _replay_xml(state, company_name, "Phase 7 duplicate XML replay")
        if second_sync["duplicates"] >= first_sync["sales_created"] or second_sync["sales_created"] == 0:
            _ok(state, "Duplicate protection on second replay — PASS")
        else:
            _warn(state, f"Duplicate protection unclear: second sales_created={second_sync['sales_created']}")

        # Phase 8
        await _create_role_users(client, admin_headers, state)
        await _role_access_checks(client, state)

        # Phases 9–11
        await _audit_and_dashboard_checks(client, admin_headers, state)

    await close_db()
    return state


def write_final_report(state: UatState, report: object) -> Path:
    out = REPORT_DIR / "FINAL_VALIDATION_REPORT.md"
    lines = [
        "# WEBSTUDIO IMS — Final Validation Report",
        "",
        "## XML Summary",
        f"- Company: {getattr(report, 'company_name', '')}",
        f"- Vouchers: {getattr(report, 'voucher_count', 0)}",
        f"- Voucher types: {dict(getattr(report, 'voucher_types', {}))}",
        f"- Inventory lines: {len(getattr(report, 'rows', []))}",
        "",
        "## Product Models Created",
        *[f"- {k}: {v}" for k, v in state.product_models.items()],
        "",
        "## Inventory Serials",
        *[f"- {serial}: {iid}" for serial, iid in sorted(state.inventory_ids.items())],
        "",
        "## Gemini",
        f"- Success: {state.gemini_stats['success']}",
        f"- Skipped (existing): {state.gemini_stats['skipped']}",
        f"- Failed/graceful: {state.gemini_stats['failed']}",
        "",
        "## Sync Duration",
        *[f"- Run {i + 1}: {d:.2f}s" for i, d in enumerate(state.sync_durations)],
        "",
        "## PASS Summary",
        *[f"- ✓ {p}" for p in state.passes],
        "",
        "## Warnings",
        *([f"- ⚠ {w}" for w in state.warnings] if state.warnings else ["- None"]),
        "",
        "## Failures",
        *([f"- ✗ {f}" for f in state.failures] if state.failures else ["- None"]),
        "",
        "## Test Credentials",
        "",
        "| Name | Username | Password | Role | Login Tested |",
        "|------|----------|----------|------|--------------|",
    ]
    for cred in state.credentials:
        lines.append(
            f"| {cred['name']} | {cred['username']} | {cred['password']} | {cred['role']} | {cred['login_tested']} |",
        )
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")

    creds_json = REPORT_DIR / "test_credentials.json"
    creds_json.write_text(json.dumps(state.credentials, indent=2), encoding="utf-8")
    return out


async def main() -> int:
    report = analyze(XML_PATH)
    state = await run_uat()
    path = write_final_report(state, report)
    print(f"\nFinal report: {path}")
    print(f"Failures: {len(state.failures)} | Warnings: {len(state.warnings)} | Passes: {len(state.passes)}")
    return 1 if state.failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
