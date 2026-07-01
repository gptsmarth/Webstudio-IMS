"""Settings API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

_RESTORE_SCOPE_PATTERN = (
    "^(entire_database|settings_only|company_config|users_only|reports_only)$"
)
_RESTORE_SOURCE_PATTERN = "^(local|scheduled|imported|emergency)$"
_BACKUP_SOURCE_PATTERN = "^(local|scheduled|imported)$"


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
    password_require_lowercase: bool = True
    password_require_number: bool = True
    password_require_symbol: bool = False
    password_history_count: int = 5
    remember_me_ttl_days: int = 30
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


class AIProviderHealthEntry(BaseModel):
    provider: str
    configured: bool
    status: str
    requests: int = 0
    failures: int = 0
    rate_limits: int = 0
    quota_exceeded: int = 0
    last_error: str | None = None
    last_success_at: str | None = None


class IntegrationsSettings(BaseModel):
    gemini_model: str = "gemini-2.5-flash"
    gemini_configured: bool = False
    gemini_api_key_hint: str | None = None
    ai_primary_provider: str = "gemini"
    ai_fallback_chain: list[str] = Field(default_factory=lambda: ["gemini"])
    ai_enrichment_enabled: bool = True
    ai_timeout_seconds: int = 90
    ai_retry_count: int = 2
    groq_model: str = "llama-3.3-70b-versatile"
    groq_configured: bool = False
    groq_api_key_hint: str | None = None
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    openrouter_configured: bool = False
    openrouter_api_key_hint: str | None = None
    ai_provider_health: list[AIProviderHealthEntry] = Field(default_factory=list)


class IntegrationsSettingsUpdate(BaseModel):
    gemini_model: str = Field(default="gemini-2.5-flash", min_length=1, max_length=64)
    gemini_api_key: str | None = Field(default=None, max_length=256)
    clear_gemini_api_key: bool = False
    ai_primary_provider: str = Field(default="gemini", min_length=1, max_length=32)
    ai_fallback_chain: list[str] = Field(default_factory=lambda: ["gemini"])
    ai_enrichment_enabled: bool = True
    ai_timeout_seconds: int = Field(default=90, ge=15, le=300)
    ai_retry_count: int = Field(default=2, ge=0, le=5, description="Total spec lookup attempts (includes the first try).")
    groq_model: str = Field(default="llama-3.3-70b-versatile", min_length=1, max_length=128)
    groq_api_key: str | None = Field(default=None, max_length=256)
    clear_groq_api_key: bool = False
    openrouter_model: str = Field(default="meta-llama/llama-3.3-70b-instruct:free", min_length=1, max_length=128)
    openrouter_api_key: str | None = Field(default=None, max_length=256)
    clear_openrouter_api_key: bool = False


class AIProviderTestRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=32)


class AIProviderTestResponse(BaseModel):
    provider: str
    success: bool
    message: str
    latency_ms: int | None = None


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
    backup_alerts_enabled: bool = True


class BackupHistoryEntry(BaseModel):
    id: int | None = None
    filename: str
    size_bytes: int
    created_at: str
    backup_type: str = "full"
    trigger_type: str = "manual"
    status: str = "completed"
    verification_status: str = "unknown"
    duration_ms: int | None = None
    checksum_sha256: str | None = None
    app_version: str | None = None
    schema_version: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    creator_display_name: str | None = None
    storage_backend: str = "local"
    is_archived: bool = False


class RestoreHistoryEntry(BaseModel):
    id: int
    filename: str
    source: str
    restore_scope: str
    status: str
    verification_status: str
    emergency_backup_filename: str | None = None
    duration_ms: int | None = None
    actor_display_name: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: str


class BackupSettings(BaseModel):
    backup_folder: str = "backups"
    storage_backend: str = "local"
    schedule: str = "manual"
    retention_policy: str = "last_30"
    retention_count: int = 30
    database_size_bytes: int = 0
    last_backup_at: str | None = None
    next_scheduled_backup_at: str | None = None
    health_status: str = "healthy"
    history: list[BackupHistoryEntry] = Field(default_factory=list)
    restore_history: list[RestoreHistoryEntry] = Field(default_factory=list)


class BackupSettingsUpdate(BaseModel):
    backup_folder: str = Field(min_length=1, max_length=512)
    storage_backend: str = Field(default="local", pattern="^(local|cloud|nas|external_drive)$")
    schedule: str = Field(default="manual", pattern="^(manual|daily|weekly|monthly)$")
    retention_policy: str = Field(
        default="last_30",
        pattern="^(last_7|last_30|last_90|unlimited|custom)$",
    )
    retention_count: int = Field(default=30, ge=1, le=365)


class BackupCreateRequest(BaseModel):
    backup_type: str = Field(default="full", pattern="^(full|incremental)$")
    trigger_type: str = Field(default="manual", pattern="^(manual|scheduled|emergency)$")


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
    id: int | None = None
    filename: str
    size_bytes: int
    created_at: str
    backup_type: str = "full"
    trigger_type: str = "manual"
    verification_status: str = "success"
    duration_ms: int = 0
    checksum_sha256: str = ""
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class BackupRestoreRequest(BaseModel):
    filename: str
    restore_scope: str = Field(default="entire_database", pattern=_RESTORE_SCOPE_PATTERN)
    source: str = Field(default="local", pattern=_RESTORE_SOURCE_PATTERN)
    create_emergency_backup: bool = True
    confirmed: bool = False


class BackupValidateRequest(BaseModel):
    filename: str
    source: str = Field(default="local", pattern=_BACKUP_SOURCE_PATTERN)


class CompatibilityReport(BaseModel):
    app_version_match: bool = True
    schema_version_match: bool = True
    backup_version_supported: bool = True
    migration_required: bool = False
    backup_schema_newer: bool = False
    backward_compatible: bool = True
    restore_allowed: bool = True
    summary: str = ""
    backup_app_version: str | None = None
    backup_schema_version: str | None = None
    current_app_version: str | None = None
    current_schema_version: str | None = None
    backup_version: str | None = None


class VerificationCheckEntry(BaseModel):
    key: str
    name: str
    status: str
    message: str


class BackupValidateResponse(BaseModel):
    valid: bool
    filename: str
    source: str
    checksum_valid: bool
    integrity_valid: bool
    corruption_detected: bool
    app_version: str | None = None
    schema_version: str | None = None
    backup_version: str | None = None
    current_app_version: str
    current_schema_version: str
    compatibility: str
    backup_type: str | None = None
    trigger_type: str | None = None
    timestamp: str | None = None
    size_bytes: int
    company_name: str | None = None
    created_by: str | None = None
    database_size_bytes: int | None = None
    inventory_count: int | None = None
    sales_count: int | None = None
    users_count: int | None = None
    audit_log_count: int | None = None
    restore_allowed: bool = True
    migration_required: bool = False
    compatibility_report: CompatibilityReport | None = None
    backup_format_id: str | None = None
    backup_format_label: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class BackupPreviewRequest(BaseModel):
    filename: str
    restore_scope: str = Field(default="entire_database", pattern=_RESTORE_SCOPE_PATTERN)
    source: str = Field(default="local", pattern=_BACKUP_SOURCE_PATTERN)


class BackupPreviewResponse(BaseModel):
    filename: str
    source: str
    restore_scope: str
    scope_implemented: bool
    backup_type: str | None = None
    trigger_type: str | None = None
    timestamp: str | None = None
    contents: list[str] = Field(default_factory=list)
    affected_areas: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    emergency_backup_recommended: bool = True
    company_name: str | None = None
    created_by: str | None = None
    app_version: str | None = None
    backup_version: str | None = None
    schema_version: str | None = None
    inventory_count: int | None = None
    sales_count: int | None = None
    users_count: int | None = None
    database_size_bytes: int | None = None
    compressed_size_bytes: int = 0
    checksum_valid: bool = False
    schema_compatibility: str = "compatible"
    restore_allowed: bool = True
    migration_required: bool = False
    compatibility_summary: str = ""
    backup_format_id: str | None = None
    backup_format_label: str | None = None


class BackupRestoreResponse(BaseModel):
    success: bool
    filename: str
    restore_scope: str
    emergency_backup_filename: str | None = None
    rollback_available: bool = False
    rollback_recommended: bool = False
    verification_status: str
    duration_ms: int
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    restart_required: bool = False
    verification_checks: list[VerificationCheckEntry] = Field(default_factory=list)


class BackupRollbackRequest(BaseModel):
    emergency_backup_filename: str
    confirmed: bool = False


class BackupImportResponse(BaseModel):
    filename: str
    size_bytes: int
    source: str = "imported"
    backup_format_id: str | None = None
    backup_format_label: str | None = None


class BackupAdminDashboard(BaseModel):
    storage_health: str
    storage_total_bytes: int
    storage_used_bytes: int
    storage_free_bytes: int
    backup_folder: str
    backup_folder_used_bytes: int
    retention_policy: str
    retention_count: int
    oldest_backup_at: str | None = None
    newest_backup_at: str | None = None
    failed_backup_count: int = 0
    warning_count: int = 0
    archived_count: int = 0
    total_backup_count: int = 0
    estimated_remaining_backups: int | None = None
    retention_used: int = 0
    warning_threshold_bytes: int = 0
    critical_threshold_bytes: int = 0


class BackupDetailEntry(BackupHistoryEntry):
    manifest: dict = Field(default_factory=dict)
    archive_path: str = ""


class BackupVerifyResponse(BaseModel):
    filename: str
    valid: bool
    checksum_valid: bool
    integrity_valid: bool
    compression_valid: bool = True
    manifest_valid: bool = True
    corruption_detected: bool = False
    verification_status: str
    overall_health: str = "healthy"
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    checks: list[VerificationCheckEntry] = Field(default_factory=list)


class RecoveryHealthIssue(BaseModel):
    code: str
    severity: str
    title: str
    message: str


class RecoveryCenterDashboard(BaseModel):
    system_health: str
    database_status: str
    backup_status: str
    storage_status: str
    recovery_readiness: str
    storage_free_bytes: int
    storage_total_bytes: int
    storage_used_bytes: int
    backup_folder: str
    last_backup_at: str | None = None
    last_restore_at: str | None = None
    failed_backup_count: int = 0
    health_issues: list[RecoveryHealthIssue] = Field(default_factory=list)
    readiness_score: dict[str, int | str] = Field(default_factory=dict)
    storage_monitoring: dict[str, int | str | None] = Field(default_factory=dict)


class MobileBackupStatusResponse(BaseModel):
    health_status: str
    backup_status: str
    last_backup_at: str | None = None
    total_backups: int = 0
    failed_backups: int = 0
    storage_free_bytes: int = 0
    storage_total_bytes: int = 0
    can_trigger_backup: bool = False
    restore_history_available: bool = True


class RecoveryValidationCheck(BaseModel):
    key: str
    name: str
    status: str
    message: str


class RecoveryValidationResponse(BaseModel):
    overall_status: str
    checks: list[RecoveryValidationCheck] = Field(default_factory=list)


class RecoveryFailureAnalysis(BaseModel):
    reason: str
    count: int


class RecoveryReportsResponse(BaseModel):
    recovery_history: list[RestoreHistoryEntry] = Field(default_factory=list)
    backup_success_rate: float = 0.0
    total_backups: int = 0
    successful_backups: int = 0
    failed_backups: int = 0
    failure_analysis: list[RecoveryFailureAnalysis] = Field(default_factory=list)
    export_supported: bool = False
