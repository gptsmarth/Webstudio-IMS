"""System settings read/update service."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.schemas.settings import (
    AIProviderHealthEntry,
    BackupHistoryEntry,
    BackupSettings,
    BackupSettingsUpdate,
    ExcelSettings,
    GeneralSettings,
    IntegrationsSettings,
    IntegrationsSettingsUpdate,
    InventorySettings,
    NotificationSettings,
    RestoreHistoryEntry,
    SalesSettings,
    SecuritySettings,
    SettingsWorkspace,
    SystemInfoSettings,
    TallySettingsGroup,
)
from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import NotificationSeverity, SettingValueType
from webstudio_backend.infrastructure.repositories.restore_run_repository import (
    RestoreRunRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import (
    TallyCompanySyncRepository,
)
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.integrations.tally.connectivity import (
    normalize_tally_host,
    validate_tally_port,
)
from webstudio_backend.integrations.tally.constants import DEFAULT_SYNC_INTERVAL_SECONDS
from webstudio_backend.integrations.tally.incremental_sync import clamp_sync_interval_seconds
from webstudio_backend.services.ai.config import mask_api_key, resolve_ai_config
from webstudio_backend.services.ai.health import AIProviderHealthTracker
from webstudio_backend.services.backup_engine import BackupEngine
from webstudio_backend.services.backup_schedule import (
    backup_health_status,
    compute_next_scheduled_backup,
)
from webstudio_backend.services.scheduler_runtime_service import SchedulerRuntimeService
from webstudio_backend.services.security_alert_service import SecurityAlertService
from webstudio_backend.services.settings_registry import SETTING_DEFAULTS
from webstudio_backend.services.system_info_service import SystemInfoService

_SENSITIVE_SETTING_KEYS = frozenset(
    {"gemini_api_key", "openai_api_key", "groq_api_key", "openrouter_api_key"}
)


def _setting_category(key: str) -> str:
    if key.startswith("tally_"):
        return "tally_configuration"
    if key.startswith(("lockout_", "password_", "session_", "remember_me_")):
        return "security_configuration"
    return "server_configuration"


def _mask_setting_value(key: str, value: str | None) -> str | None:
    if value is None:
        return None
    if key in _SENSITIVE_SETTING_KEYS and value.strip():
        return "••••"
    return value


class SettingsService:
    def __init__(self, session: AsyncSession, app_settings: Settings) -> None:
        self._session = session
        self._settings = SystemSettingRepository(session)
        self._users = UserRepository(session)
        self._app_settings = app_settings
        self._recorder = AuditRecorder(session)

    async def get_workspace(
        self, *, api_health: str = "ok", database_health: str = "ok"
    ) -> SettingsWorkspace:
        await self._ensure_defaults()
        system_info = await SystemInfoService(self._session, self._app_settings).build()
        backup_engine = BackupEngine(
            self._session,
            self._app_settings,
            backup_dir=self._resolve_backup_folder(
                await self._get_str("backup_folder") or "backups"
            ),
        )
        history_rows = await backup_engine.list_dashboard_entries(limit=25)
        restore_rows = await self._restore_history_entries()
        schedule = await self._get_str("backup_schedule") or "manual"
        retention_count = await self._get_int("backup_retention_count", 30)
        retention_policy = await self._get_str("backup_retention_policy") or "last_30"
        storage_backend = await self._get_str("backup_storage_backend") or "local"
        last_backup_raw = await self._get_str("last_backup_at")
        last_backup_dt = datetime.fromisoformat(last_backup_raw) if last_backup_raw else None
        next_scheduled = compute_next_scheduled_backup(schedule, last_backup_at=last_backup_dt)
        last_verification = history_rows[0]["verification_status"] if history_rows else None
        health_status = backup_health_status(
            database_health=database_health,
            last_verification_status=last_verification,
            storage_free_bytes=system_info["storage_free_bytes"],
        )
        resolved_folder = str(
            self._resolve_backup_folder(await self._get_str("backup_folder") or "backups"),
        )
        main_admin = await self._users.get_main_admin()

        return SettingsWorkspace(
            general=GeneralSettings(
                company_name=await self._get_str("company_name"),
                company_logo=await self._get_str("company_logo"),
                company_address=await self._get_str("company_address"),
                gst_number=await self._get_str("gst_number"),
                company_phone=await self._get_str("company_phone"),
                company_email=await self._get_str("company_email"),
                default_store_id=self._parse_optional_int(await self._get_str("default_store_id")),
                default_language=await self._get_str("default_language") or "en",
                timezone=await self._get_str("timezone") or "Asia/Kolkata",
                currency=await self._get_str("currency") or "INR",
            ),
            security=SecuritySettings(
                session_timeout_minutes=await self._get_int("session_timeout_minutes", 15),
                password_min_length=await self._get_int("password_min_length", 10),
                password_require_uppercase=await self._get_bool("password_require_uppercase", True),
                password_require_lowercase=await self._get_bool("password_require_lowercase", True),
                password_require_number=await self._get_bool("password_require_number", True),
                password_require_symbol=await self._get_bool("password_require_symbol", False),
                password_history_count=await self._get_int("password_history_count", 5),
                remember_me_ttl_days=await self._get_int("remember_me_ttl_days", 30),
                lockout_threshold=await self._get_int("lockout_threshold", 5),
                lockout_duration_minutes=await self._get_int("lockout_duration_minutes", 15),
                jwt_access_token_ttl_minutes=self._app_settings.access_token_ttl_minutes,
                jwt_refresh_token_ttl_days=self._app_settings.refresh_token_ttl_days,
                jwt_issuer=self._app_settings.jwt_issuer,
                jwt_audience=self._app_settings.jwt_audience,
                recovery_key_configured=bool(main_admin and main_admin.recovery_key_hash),
                recovery_key_last_used_at=(
                    main_admin.recovery_key_last_used_at.isoformat()
                    if main_admin and main_admin.recovery_key_last_used_at
                    else None
                ),
                https_certificate_status=system_info["https_certificate_status"],
            ),
            inventory=InventorySettings(
                default_inventory_status=await self._get_str("default_inventory_status")
                or "received",
                default_store_id=self._parse_optional_int(await self._get_str("default_store_id")),
                qr_code_enabled=await self._get_bool("qr_code_enabled", True),
                auto_generate_labels=await self._get_bool("auto_generate_labels", False),
                serial_number_prefix=await self._get_str("serial_number_prefix"),
                serial_number_suffix=await self._get_str("serial_number_suffix"),
                inventory_colors=await self._get_json_list("inventory_colors"),
            ),
            sales=SalesSettings(
                default_payment_modes=await self._get_json_list("default_payment_modes")
                or ["Cash", "UPI", "Card", "Finance"],
                invoice_prefix=await self._get_str("invoice_prefix") or "INV-",
                manual_sale_enabled=await self._get_bool("manual_sale_enabled", True),
                default_salesperson_id=None,
            ),
            tally=await self._tally_group(),
            integrations=await self._integrations_group(),
            excel=ExcelSettings(
                export_path=await self._get_str("excel_export_path") or "exports",
                file_naming=await self._get_str("excel_file_naming") or "webstudio-{report}-{date}",
                auto_export_schedule=None,
            ),
            notifications=NotificationSettings(
                notifications_enabled=await self._get_bool("notifications_enabled", True),
                desktop_notifications=await self._get_bool("desktop_notifications", True),
                system_alerts_enabled=await self._get_bool("system_alerts_enabled", True),
                tally_alerts_enabled=await self._get_bool("tally_alerts_enabled", True),
                inventory_alerts_enabled=await self._get_bool("inventory_alerts_enabled", True),
                audit_alerts_enabled=await self._get_bool("audit_alerts_enabled", True),
                backup_alerts_enabled=await self._get_bool("backup_alerts_enabled", True),
            ),
            backup=BackupSettings(
                backup_folder=resolved_folder,
                storage_backend=storage_backend,
                schedule=schedule,
                retention_policy=retention_policy,
                retention_count=retention_count,
                database_size_bytes=system_info["database_size_bytes"],
                last_backup_at=last_backup_raw or system_info["last_backup_at"],
                next_scheduled_backup_at=next_scheduled.isoformat() if next_scheduled else None,
                health_status=health_status,
                history=[BackupHistoryEntry(**row) for row in history_rows],
                restore_history=restore_rows,
            ),
            system=SystemInfoSettings(
                app_version=system_info["app_version"],
                api_version=system_info["api_version"],
                environment=system_info["environment"],
                database_size_bytes=system_info["database_size_bytes"],
                storage_total_bytes=system_info["storage_total_bytes"],
                storage_used_bytes=system_info["storage_used_bytes"],
                storage_free_bytes=system_info["storage_free_bytes"],
                backup_folder=system_info["backup_folder"],
                logs_folder=system_info["logs_folder"],
                last_backup_at=system_info["last_backup_at"],
                api_health=api_health,
                database_health=database_health,
            ),
        )

    async def update_general(self, payload: GeneralSettings, *, actor_id: int) -> GeneralSettings:
        await self._set_str("company_name", payload.company_name, actor_id=actor_id)
        await self._set_str("company_logo", payload.company_logo, actor_id=actor_id)
        await self._set_str("company_address", payload.company_address, actor_id=actor_id)
        await self._set_str("gst_number", payload.gst_number, actor_id=actor_id)
        await self._set_str("company_phone", payload.company_phone, actor_id=actor_id)
        await self._set_str("company_email", payload.company_email, actor_id=actor_id)
        await self._set_str(
            "default_store_id",
            "" if payload.default_store_id is None else str(payload.default_store_id),
            actor_id=actor_id,
        )
        await self._set_str("default_language", payload.default_language, actor_id=actor_id)
        await self._set_str("timezone", payload.timezone, actor_id=actor_id)
        await self._set_str("currency", payload.currency, actor_id=actor_id)
        workspace = await self.get_workspace()
        return workspace.general

    async def update_security(
        self, payload: SecuritySettings, *, actor_id: int
    ) -> SecuritySettings:
        await self._set_int(
            "session_timeout_minutes", payload.session_timeout_minutes, actor_id=actor_id
        )
        await self._set_int("password_min_length", payload.password_min_length, actor_id=actor_id)
        await self._set_bool(
            "password_require_uppercase", payload.password_require_uppercase, actor_id=actor_id
        )
        await self._set_bool(
            "password_require_lowercase", payload.password_require_lowercase, actor_id=actor_id
        )
        await self._set_bool(
            "password_require_number", payload.password_require_number, actor_id=actor_id
        )
        await self._set_bool(
            "password_require_symbol", payload.password_require_symbol, actor_id=actor_id
        )
        await self._set_int(
            "password_history_count", payload.password_history_count, actor_id=actor_id
        )
        await self._set_int("remember_me_ttl_days", payload.remember_me_ttl_days, actor_id=actor_id)
        await self._set_int("lockout_threshold", payload.lockout_threshold, actor_id=actor_id)
        await self._set_int(
            "lockout_duration_minutes", payload.lockout_duration_minutes, actor_id=actor_id
        )
        workspace = await self.get_workspace()
        return workspace.security

    async def update_inventory(
        self, payload: InventorySettings, *, actor_id: int
    ) -> InventorySettings:
        await self._set_str(
            "default_inventory_status", payload.default_inventory_status, actor_id=actor_id
        )
        await self._set_str(
            "default_store_id",
            "" if payload.default_store_id is None else str(payload.default_store_id),
            actor_id=actor_id,
        )
        await self._set_bool("qr_code_enabled", payload.qr_code_enabled, actor_id=actor_id)
        await self._set_bool(
            "auto_generate_labels", payload.auto_generate_labels, actor_id=actor_id
        )
        await self._set_str("serial_number_prefix", payload.serial_number_prefix, actor_id=actor_id)
        await self._set_str("serial_number_suffix", payload.serial_number_suffix, actor_id=actor_id)
        await self._set_json("inventory_colors", payload.inventory_colors, actor_id=actor_id)
        workspace = await self.get_workspace()
        return workspace.inventory

    async def update_sales(self, payload: SalesSettings, *, actor_id: int) -> SalesSettings:
        await self._set_json(
            "default_payment_modes", payload.default_payment_modes, actor_id=actor_id
        )
        await self._set_str("invoice_prefix", payload.invoice_prefix, actor_id=actor_id)
        await self._set_bool("manual_sale_enabled", payload.manual_sale_enabled, actor_id=actor_id)
        workspace = await self.get_workspace()
        return workspace.sales

    async def update_tally(
        self, payload: TallySettingsGroup, *, actor_id: int
    ) -> TallySettingsGroup:
        normalized_host = normalize_tally_host(payload.tally_host)
        normalized_port = validate_tally_port(payload.tally_port)
        normalized_company = payload.tally_company_name.strip()
        await self._set_bool("tally_enabled", payload.enabled, actor_id=actor_id)
        await self._set_str("tally_host", normalized_host, actor_id=actor_id)
        await self._set_str("tally_port", normalized_port, actor_id=actor_id)
        await self._set_str("tally_company_name", normalized_company, actor_id=actor_id)
        await self._set_int(
            "tally_sync_interval_seconds",
            clamp_sync_interval_seconds(payload.sync_interval_seconds),
            actor_id=actor_id,
        )
        interval = clamp_sync_interval_seconds(payload.sync_interval_seconds)
        runtime = SchedulerRuntimeService(self._session)
        await runtime.sync_interval("tally_sync", interval)
        company_repo = TallyCompanySyncRepository(self._session)
        await company_repo.deactivate_except(normalized_company)
        primary = await company_repo.get_or_create(normalized_company)
        primary.is_active = True
        await self._session.flush()
        workspace = await self.get_workspace()
        return workspace.tally

    async def update_integrations(
        self,
        payload: IntegrationsSettingsUpdate,
        *,
        actor_id: int,
    ) -> IntegrationsSettings:
        await self._set_str("gemini_model", payload.gemini_model.strip(), actor_id=actor_id)
        if payload.clear_gemini_api_key:
            await self._set_str("gemini_api_key", "", actor_id=actor_id)
        elif payload.gemini_api_key is not None and payload.gemini_api_key.strip():
            await self._set_str("gemini_api_key", payload.gemini_api_key.strip(), actor_id=actor_id)

        await self._set_str(
            "ai_primary_provider", payload.ai_primary_provider.strip().lower(), actor_id=actor_id
        )
        await self._set_json("ai_fallback_chain", payload.ai_fallback_chain, actor_id=actor_id)
        await self._set_bool(
            "ai_enrichment_enabled", payload.ai_enrichment_enabled, actor_id=actor_id
        )
        await self._set_int("ai_timeout_seconds", payload.ai_timeout_seconds, actor_id=actor_id)
        await self._set_int("ai_retry_count", payload.ai_retry_count, actor_id=actor_id)
        await self._set_int(
            "asus_price_refresh_stale_days",
            payload.asus_price_refresh_stale_days,
            actor_id=actor_id,
        )

        await self._set_str("groq_model", payload.groq_model.strip(), actor_id=actor_id)
        if payload.clear_groq_api_key:
            await self._set_str("groq_api_key", "", actor_id=actor_id)
        elif payload.groq_api_key is not None and payload.groq_api_key.strip():
            await self._set_str("groq_api_key", payload.groq_api_key.strip(), actor_id=actor_id)

        await self._set_str("openrouter_model", payload.openrouter_model.strip(), actor_id=actor_id)
        if payload.clear_openrouter_api_key:
            await self._set_str("openrouter_api_key", "", actor_id=actor_id)
        elif payload.openrouter_api_key is not None and payload.openrouter_api_key.strip():
            await self._set_str(
                "openrouter_api_key", payload.openrouter_api_key.strip(), actor_id=actor_id
            )

        await self._set_str("openai_model", payload.openai_model.strip(), actor_id=actor_id)
        if payload.clear_openai_api_key:
            await self._set_str("openai_api_key", "", actor_id=actor_id)
        elif payload.openai_api_key is not None and payload.openai_api_key.strip():
            await self._set_str("openai_api_key", payload.openai_api_key.strip(), actor_id=actor_id)

        workspace = await self.get_workspace()
        return workspace.integrations

    async def update_excel(self, payload: ExcelSettings, *, actor_id: int) -> ExcelSettings:
        await self._set_str("excel_export_path", payload.export_path, actor_id=actor_id)
        await self._set_str("excel_file_naming", payload.file_naming, actor_id=actor_id)
        workspace = await self.get_workspace()
        return workspace.excel

    async def update_notifications(
        self,
        payload: NotificationSettings,
        *,
        actor_id: int,
    ) -> NotificationSettings:
        await self._set_bool(
            "notifications_enabled", payload.notifications_enabled, actor_id=actor_id
        )
        await self._set_bool(
            "desktop_notifications", payload.desktop_notifications, actor_id=actor_id
        )
        await self._set_bool(
            "system_alerts_enabled", payload.system_alerts_enabled, actor_id=actor_id
        )
        await self._set_bool(
            "tally_alerts_enabled", payload.tally_alerts_enabled, actor_id=actor_id
        )
        await self._set_bool(
            "inventory_alerts_enabled", payload.inventory_alerts_enabled, actor_id=actor_id
        )
        await self._set_bool(
            "audit_alerts_enabled", payload.audit_alerts_enabled, actor_id=actor_id
        )
        await self._set_bool(
            "backup_alerts_enabled", payload.backup_alerts_enabled, actor_id=actor_id
        )
        workspace = await self.get_workspace()
        return workspace.notifications

    async def update_backup(
        self, payload: BackupSettingsUpdate, *, actor_id: int
    ) -> BackupSettings:
        await self._set_str("backup_folder", payload.backup_folder, actor_id=actor_id)
        await self._set_str("backup_schedule", payload.schedule, actor_id=actor_id)
        await self._set_str("backup_retention_policy", payload.retention_policy, actor_id=actor_id)
        await self._set_int("backup_retention_count", payload.retention_count, actor_id=actor_id)
        await self._set_str("backup_storage_backend", payload.storage_backend, actor_id=actor_id)
        workspace = await self.get_workspace()
        return workspace.backup

    async def get_backup_folder_path(self) -> Path:
        return self._resolve_backup_folder(await self._get_str("backup_folder") or "backups")

    async def get_backup_storage_backend(self) -> str:
        return await self._get_str("backup_storage_backend") or "local"

    async def _restore_history_entries(self) -> list[RestoreHistoryEntry]:
        runs = await RestoreRunRepository(self._session).list_recent(limit=15)
        return [
            RestoreHistoryEntry(
                id=run.id,
                filename=run.filename,
                source=run.source,
                restore_scope=run.restore_scope,
                status=run.status,
                verification_status=run.verification_status,
                emergency_backup_filename=run.emergency_backup_filename,
                duration_ms=run.duration_ms,
                actor_display_name=run.actor_display_name,
                warnings=json.loads(run.warnings_json or "[]"),
                errors=json.loads(run.errors_json or "[]"),
                created_at=run.created_at.isoformat(),
            )
            for run in runs
        ]

    async def _tally_group(self) -> TallySettingsGroup:
        enabled = await self._get_bool("tally_enabled", False)
        interval = clamp_sync_interval_seconds(
            await self._get_int("tally_sync_interval_seconds", DEFAULT_SYNC_INTERVAL_SECONDS),
        )
        now = datetime.now(UTC)
        return TallySettingsGroup(
            connection_status="connected" if enabled else "disconnected",
            enabled=enabled,
            tally_host=await self._get_str("tally_host") or "127.0.0.1",
            tally_port=await self._get_str("tally_port") or "9000",
            tally_company_name=await self._get_str("tally_company_name") or "WEBSTUDIO",
            sync_interval_seconds=interval,
            last_sync_at=None,
            next_sync_at=(now + timedelta(seconds=interval)).isoformat() if enabled else None,
            companies=[],
        )

    async def _integrations_group(self) -> IntegrationsSettings:
        config = await resolve_ai_config(self._session, self._app_settings)
        asus_price_refresh_stale_days = await self._get_int("asus_price_refresh_stale_days", 7)
        fallback_raw = await self._get_str("ai_fallback_chain")
        try:
            fallback_chain = json.loads(fallback_raw) if fallback_raw else config.fallback_chain
        except json.JSONDecodeError:
            fallback_chain = config.fallback_chain
        if not isinstance(fallback_chain, list):
            fallback_chain = config.fallback_chain

        configured_map = {
            "gemini": bool(config.gemini.api_key),
            "openai": bool(config.openai.api_key),
            "groq": bool(config.groq.api_key),
            "openrouter": bool(config.openrouter.api_key),
            "mock": True,
        }
        health = [
            AIProviderHealthEntry(
                **AIProviderHealthTracker.snapshot(
                    provider, configured=configured_map[provider]
                ).to_dict()
            )
            for provider in ("gemini", "openai", "groq", "openrouter", "mock")
        ]
        return IntegrationsSettings(
            gemini_model=config.gemini.model,
            gemini_configured=bool(config.gemini.api_key),
            gemini_api_key_hint=mask_api_key(config.gemini.api_key),
            ai_primary_provider=config.primary_provider,
            ai_fallback_chain=[str(item) for item in fallback_chain],
            ai_enrichment_enabled=config.enrichment_enabled,
            ai_timeout_seconds=config.timeout_seconds,
            ai_retry_count=config.retry_count,
            asus_price_refresh_stale_days=asus_price_refresh_stale_days,
            groq_model=config.groq.model,
            groq_configured=bool(config.groq.api_key),
            groq_api_key_hint=mask_api_key(config.groq.api_key),
            openrouter_model=config.openrouter.model,
            openrouter_configured=bool(config.openrouter.api_key),
            openrouter_api_key_hint=mask_api_key(config.openrouter.api_key),
            openai_model=config.openai.model,
            openai_configured=bool(config.openai.api_key),
            openai_api_key_hint=mask_api_key(config.openai.api_key),
            ai_provider_health=health,
        )

    async def _ensure_defaults(self) -> None:
        for key, (value, value_type) in SETTING_DEFAULTS.items():
            if await self._settings.get_by_key(key) is None and key != "company_name":
                await self._settings.set_value(key, value, value_type=value_type)

    async def _get_str(self, key: str) -> str:
        return (
            await self._settings.get_string(key)
            or SETTING_DEFAULTS.get(key, ("", SettingValueType.STRING))[0]
        )

    async def _get_int(self, key: str, default: int) -> int:
        return await self._settings.get_int(key, default=default)

    async def _get_bool(self, key: str, default: bool) -> bool:
        return await self._settings.get_bool(key, default=default)

    async def _get_json_list(self, key: str) -> list[str]:
        raw = await self._get_str(key)
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            return []
        return []

    async def _set_str(self, key: str, value: str, *, actor_id: int) -> None:
        old_raw = await self._get_str(key)
        new_raw = value.strip()
        await self._settings.set_value(
            key,
            new_raw,
            value_type=SETTING_DEFAULTS.get(key, ("", SettingValueType.STRING))[1],
            updated_by_user_id=actor_id,
        )
        if old_raw != new_raw:
            await self._audit_setting_change(key, old_raw, new_raw, actor_id)

    async def _set_int(self, key: str, value: int, *, actor_id: int) -> None:
        old_raw = str(await self._get_int(key, default=value))
        new_raw = str(value)
        await self._settings.set_value(
            key,
            new_raw,
            value_type=SettingValueType.INTEGER,
            updated_by_user_id=actor_id,
        )
        if old_raw != new_raw:
            await self._audit_setting_change(key, old_raw, new_raw, actor_id)

    async def _set_bool(self, key: str, value: bool, *, actor_id: int) -> None:
        old_raw = "true" if await self._get_bool(key, default=value) else "false"
        new_raw = "true" if value else "false"
        await self._settings.set_value(
            key,
            new_raw,
            value_type=SettingValueType.BOOLEAN,
            updated_by_user_id=actor_id,
        )
        if old_raw != new_raw:
            await self._audit_setting_change(key, old_raw, new_raw, actor_id)

    async def _set_json(self, key: str, value: list[Any], *, actor_id: int) -> None:
        old_raw = json.dumps(await self._get_json_list(key))
        new_raw = json.dumps(value)
        await self._settings.set_value(
            key,
            new_raw,
            value_type=SettingValueType.JSON,
            updated_by_user_id=actor_id,
        )
        if old_raw != new_raw:
            await self._audit_setting_change(key, old_raw, new_raw, actor_id)

    async def _audit_setting_change(
        self, key: str, old_value: str, new_value: str, actor_id: int
    ) -> None:
        actor_user = await self._users.get_by_id(actor_id)
        actor = AuditActor(
            user_id=actor_id,
            display_name=(
                (actor_user.display_name or actor_user.username) if actor_user else "System"
            ),
            role=actor_user.role.value if actor_user else "system",
        )
        category = _setting_category(key)
        await self._recorder.record_configuration_change(
            setting_key=key,
            category=category,
            old_value=_mask_setting_value(key, old_value),
            new_value=_mask_setting_value(key, new_value),
            actor=actor,
        )
        if category in {"security_configuration", "tally_configuration"}:
            await SecurityAlertService(self._session).emit(
                title="Security configuration changed",
                message=f"Setting '{key}' was updated by {actor.display_name}.",
                severity=NotificationSeverity.WARNING,
            )

    @staticmethod
    def _parse_optional_int(value: str | None) -> int | None:
        if not value or not value.strip():
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def _resolve_backup_folder(folder_setting: str) -> Path:
        env_dir = os.environ.get("BACKUP_DIR", "").strip()
        if env_dir:
            return Path(env_dir).expanduser().resolve()
        candidate = Path(folder_setting.strip() or "backups")
        if candidate.is_absolute():
            return candidate
        cwd = Path.cwd()
        for root in (cwd, cwd.parent, cwd.parent.parent):
            if (root / "apps" / "backend").is_dir():
                return (root / candidate).resolve()
        return (cwd / candidate).resolve()
