"""Settings API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GeneralSettings(BaseModel):
    company_name: str = ""
    company_logo: str = ""
    company_address: str = ""
    gst_number: str = ""
    company_phone: str = ""
    company_email: str = ""
    default_store_id: int | None = None
    default_language: str = "en"
    timezone: str = "Asia/Kolkata"
    currency: str = "INR"


class SecuritySettings(BaseModel):
    session_timeout_minutes: int = 15
    password_min_length: int = 10
    password_require_uppercase: bool = True
    password_require_number: bool = True
    password_require_symbol: bool = False
    lockout_threshold: int = 5
    lockout_duration_minutes: int = 15
    jwt_access_token_ttl_minutes: int = 15
    jwt_refresh_token_ttl_days: int = 7
    jwt_issuer: str = ""
    jwt_audience: str = ""
    recovery_key_configured: bool = False
    recovery_key_last_used_at: str | None = None
    https_certificate_status: str = "not_configured"


class InventorySettings(BaseModel):
    default_inventory_status: str = "received"
    default_store_id: int | None = None
    qr_code_enabled: bool = True
    auto_generate_labels: bool = False
    serial_number_prefix: str = ""
    serial_number_suffix: str = ""
    inventory_colors: list[str] = Field(default_factory=list)


class SalesSettings(BaseModel):
    default_payment_modes: list[str] = Field(default_factory=lambda: ["Cash", "UPI", "Card", "Finance"])
    invoice_prefix: str = "INV-"
    manual_sale_enabled: bool = True
    default_salesperson_id: int | None = None


class TallySettingsGroup(BaseModel):
    connection_status: str = "disconnected"
    enabled: bool = False
    tally_host: str = "127.0.0.1"
    tally_port: str = "9000"
    tally_company_name: str = "WEBSTUDIO"
    sync_interval_seconds: int = 1800
    last_sync_at: str | None = None
    next_sync_at: str | None = None
    companies: list[str] = Field(default_factory=list)


class IntegrationsSettings(BaseModel):
    gemini_model: str = "gemini-2.5-flash"
    gemini_configured: bool = False
    gemini_api_key_hint: str | None = None


class IntegrationsSettingsUpdate(BaseModel):
    gemini_model: str = Field(default="gemini-2.5-flash", min_length=1, max_length=64)
    gemini_api_key: str | None = Field(default=None, max_length=256)
    clear_gemini_api_key: bool = False


class ExcelSettings(BaseModel):
    export_path: str = "exports"
    file_naming: str = "webstudio-{report}-{date}"
    auto_export_schedule: str | None = None


class NotificationSettings(BaseModel):
    notifications_enabled: bool = True
    desktop_notifications: bool = True
    system_alerts_enabled: bool = True
    tally_alerts_enabled: bool = True
    inventory_alerts_enabled: bool = True
    audit_alerts_enabled: bool = True


class BackupSettings(BaseModel):
    backup_folder: str = "backups"
    database_size_bytes: int = 0
    last_backup_at: str | None = None
    history: list[dict] = Field(default_factory=list)


class SystemInfoSettings(BaseModel):
    app_version: str = ""
    api_version: str = ""
    environment: str = ""
    database_size_bytes: int = 0
    storage_total_bytes: int = 0
    storage_used_bytes: int = 0
    storage_free_bytes: int = 0
    backup_folder: str = ""
    logs_folder: str = ""
    last_backup_at: str | None = None
    api_health: str = "unknown"
    database_health: str = "unknown"


class SettingsWorkspace(BaseModel):
    general: GeneralSettings
    security: SecuritySettings
    inventory: InventorySettings
    sales: SalesSettings
    tally: TallySettingsGroup
    integrations: IntegrationsSettings
    excel: ExcelSettings
    notifications: NotificationSettings
    backup: BackupSettings
    system: SystemInfoSettings


class BackupCreateResponse(BaseModel):
    filename: str
    size_bytes: int
    created_at: str


class BackupRestoreRequest(BaseModel):
    filename: str
