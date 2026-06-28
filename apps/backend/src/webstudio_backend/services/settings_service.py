"""System settings read/update service."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.schemas.settings import (
    BackupSettings,
    ExcelSettings,
    GeneralSettings,
    IntegrationsSettings,
    IntegrationsSettingsUpdate,
    InventorySettings,
    NotificationSettings,
    SalesSettings,
    SecuritySettings,
    SettingsWorkspace,
    SystemInfoSettings,
    TallySettingsGroup,
)
from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import SettingValueType
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.services.backup_service import BackupService
from webstudio_backend.services.gemini_config import mask_api_key, resolve_gemini_credentials
from webstudio_backend.services.settings_registry import SETTING_DEFAULTS
from webstudio_backend.services.system_info_service import SystemInfoService


class SettingsService:
    def __init__(self, session: AsyncSession, app_settings: Settings) -> None:
        self._session = session
        self._settings = SystemSettingRepository(session)
        self._users = UserRepository(session)
        self._app_settings = app_settings

    async def get_workspace(self, *, api_health: str = "ok", database_health: str = "ok") -> SettingsWorkspace:
        await self._ensure_defaults()
        system_info = await SystemInfoService(self._session, self._app_settings).build()
        backups = BackupService().list_backups()
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
                password_require_number=await self._get_bool("password_require_number", True),
                password_require_symbol=await self._get_bool("password_require_symbol", False),
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
                default_inventory_status=await self._get_str("default_inventory_status") or "received",
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
            ),
            backup=BackupSettings(
                backup_folder=system_info["backup_folder"],
                database_size_bytes=system_info["database_size_bytes"],
                last_backup_at=system_info["last_backup_at"],
                history=[
                    {
                        "filename": item.filename,
                        "size_bytes": item.size_bytes,
                        "created_at": item.created_at,
                    }
                    for item in backups
                ],
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

    async def update_security(self, payload: SecuritySettings, *, actor_id: int) -> SecuritySettings:
        await self._set_int("session_timeout_minutes", payload.session_timeout_minutes, actor_id=actor_id)
        await self._set_int("password_min_length", payload.password_min_length, actor_id=actor_id)
        await self._set_bool("password_require_uppercase", payload.password_require_uppercase, actor_id=actor_id)
        await self._set_bool("password_require_number", payload.password_require_number, actor_id=actor_id)
        await self._set_bool("password_require_symbol", payload.password_require_symbol, actor_id=actor_id)
        await self._set_int("lockout_threshold", payload.lockout_threshold, actor_id=actor_id)
        await self._set_int("lockout_duration_minutes", payload.lockout_duration_minutes, actor_id=actor_id)
        workspace = await self.get_workspace()
        return workspace.security

    async def update_inventory(self, payload: InventorySettings, *, actor_id: int) -> InventorySettings:
        await self._set_str("default_inventory_status", payload.default_inventory_status, actor_id=actor_id)
        await self._set_str(
            "default_store_id",
            "" if payload.default_store_id is None else str(payload.default_store_id),
            actor_id=actor_id,
        )
        await self._set_bool("qr_code_enabled", payload.qr_code_enabled, actor_id=actor_id)
        await self._set_bool("auto_generate_labels", payload.auto_generate_labels, actor_id=actor_id)
        await self._set_str("serial_number_prefix", payload.serial_number_prefix, actor_id=actor_id)
        await self._set_str("serial_number_suffix", payload.serial_number_suffix, actor_id=actor_id)
        await self._set_json("inventory_colors", payload.inventory_colors, actor_id=actor_id)
        workspace = await self.get_workspace()
        return workspace.inventory

    async def update_sales(self, payload: SalesSettings, *, actor_id: int) -> SalesSettings:
        await self._set_json("default_payment_modes", payload.default_payment_modes, actor_id=actor_id)
        await self._set_str("invoice_prefix", payload.invoice_prefix, actor_id=actor_id)
        await self._set_bool("manual_sale_enabled", payload.manual_sale_enabled, actor_id=actor_id)
        workspace = await self.get_workspace()
        return workspace.sales

    async def update_tally(self, payload: TallySettingsGroup, *, actor_id: int) -> TallySettingsGroup:
        await self._set_bool("tally_enabled", payload.enabled, actor_id=actor_id)
        await self._set_str("tally_host", payload.tally_host, actor_id=actor_id)
        await self._set_str("tally_port", payload.tally_port, actor_id=actor_id)
        await self._set_str("tally_company_name", payload.tally_company_name, actor_id=actor_id)
        await self._set_int("tally_sync_interval_seconds", payload.sync_interval_seconds, actor_id=actor_id)
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
        await self._set_bool("notifications_enabled", payload.notifications_enabled, actor_id=actor_id)
        await self._set_bool("desktop_notifications", payload.desktop_notifications, actor_id=actor_id)
        await self._set_bool("system_alerts_enabled", payload.system_alerts_enabled, actor_id=actor_id)
        await self._set_bool("tally_alerts_enabled", payload.tally_alerts_enabled, actor_id=actor_id)
        await self._set_bool("inventory_alerts_enabled", payload.inventory_alerts_enabled, actor_id=actor_id)
        await self._set_bool("audit_alerts_enabled", payload.audit_alerts_enabled, actor_id=actor_id)
        workspace = await self.get_workspace()
        return workspace.notifications

    async def _tally_group(self) -> TallySettingsGroup:
        enabled = await self._get_bool("tally_enabled", False)
        interval = await self._get_int("tally_sync_interval_seconds", 1800)
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
        api_key, model = await resolve_gemini_credentials(self._session, self._app_settings)
        return IntegrationsSettings(
            gemini_model=model,
            gemini_configured=bool(api_key),
            gemini_api_key_hint=mask_api_key(api_key),
        )

    async def _ensure_defaults(self) -> None:
        for key, (value, value_type) in SETTING_DEFAULTS.items():
            if await self._settings.get_by_key(key) is None and key != "company_name":
                await self._settings.set_value(key, value, value_type=value_type)

    async def _get_str(self, key: str) -> str:
        return await self._settings.get_string(key) or SETTING_DEFAULTS.get(key, ("", SettingValueType.STRING))[0]

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
        await self._settings.set_value(
            key,
            value.strip(),
            value_type=SETTING_DEFAULTS.get(key, ("", SettingValueType.STRING))[1],
            updated_by_user_id=actor_id,
        )

    async def _set_int(self, key: str, value: int, *, actor_id: int) -> None:
        await self._settings.set_value(
            key,
            str(value),
            value_type=SettingValueType.INTEGER,
            updated_by_user_id=actor_id,
        )

    async def _set_bool(self, key: str, value: bool, *, actor_id: int) -> None:
        await self._settings.set_value(
            key,
            "true" if value else "false",
            value_type=SettingValueType.BOOLEAN,
            updated_by_user_id=actor_id,
        )

    async def _set_json(self, key: str, value: list[Any], *, actor_id: int) -> None:
        await self._settings.set_value(
            key,
            json.dumps(value),
            value_type=SettingValueType.JSON,
            updated_by_user_id=actor_id,
        )

    @staticmethod
    def _parse_optional_int(value: str | None) -> int | None:
        if not value or not value.strip():
            return None
        try:
            return int(value)
        except ValueError:
            return None
