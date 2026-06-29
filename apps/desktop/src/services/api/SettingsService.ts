import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export interface GeneralSettings {
  company_name: string;
  company_logo: string;
  company_address: string;
  gst_number: string;
  company_phone: string;
  company_email: string;
  default_store_id: number | null;
  default_language: string;
  timezone: string;
  currency: string;
}

export interface SecuritySettings {
  session_timeout_minutes: number;
  password_min_length: number;
  password_require_uppercase: boolean;
  password_require_lowercase: boolean;
  password_require_number: boolean;
  password_require_symbol: boolean;
  password_history_count: number;
  remember_me_ttl_days: number;
  lockout_threshold: number;
  lockout_duration_minutes: number;
  jwt_access_token_ttl_minutes: number;
  jwt_refresh_token_ttl_days: number;
  jwt_issuer: string;
  jwt_audience: string;
  recovery_key_configured: boolean;
  recovery_key_last_used_at: string | null;
  https_certificate_status: string;
}

export interface InventorySettings {
  default_inventory_status: string;
  default_store_id: number | null;
  qr_code_enabled: boolean;
  auto_generate_labels: boolean;
  serial_number_prefix: string;
  serial_number_suffix: string;
  inventory_colors: string[];
}

export interface SalesSettings {
  default_payment_modes: string[];
  invoice_prefix: string;
  manual_sale_enabled: boolean;
  default_salesperson_id: number | null;
}

export interface TallySettingsGroup {
  connection_status: string;
  enabled: boolean;
  tally_host: string;
  tally_port: string;
  tally_company_name: string;
  sync_interval_seconds: number;
  last_sync_at: string | null;
  next_sync_at: string | null;
  companies: string[];
}

export interface IntegrationsSettings {
  gemini_model: string;
  gemini_configured: boolean;
  gemini_api_key_hint: string | null;
}

export interface IntegrationsSettingsUpdate {
  gemini_model: string;
  gemini_api_key?: string | null;
  clear_gemini_api_key?: boolean;
}

export interface ExcelSettings {
  export_path: string;
  file_naming: string;
  auto_export_schedule: string | null;
}

export interface NotificationSettings {
  notifications_enabled: boolean;
  desktop_notifications: boolean;
  system_alerts_enabled: boolean;
  tally_alerts_enabled: boolean;
  inventory_alerts_enabled: boolean;
  audit_alerts_enabled: boolean;
  backup_alerts_enabled: boolean;
}

export interface BackupHistoryEntry {
  id?: number | null;
  filename: string;
  size_bytes: number;
  created_at: string;
  backup_type?: string;
  trigger_type?: string;
  status?: string;
  verification_status?: string;
  duration_ms?: number | null;
  checksum_sha256?: string | null;
  app_version?: string | null;
  schema_version?: string | null;
  warnings?: string[];
  errors?: string[];
  creator_display_name?: string | null;
  storage_backend?: string;
  is_archived?: boolean;
}

export interface BackupAdminDashboard {
  storage_health: string;
  storage_total_bytes: number;
  storage_used_bytes: number;
  storage_free_bytes: number;
  backup_folder: string;
  backup_folder_used_bytes: number;
  retention_policy: string;
  retention_count: number;
  oldest_backup_at: string | null;
  newest_backup_at: string | null;
  failed_backup_count: number;
  warning_count: number;
  archived_count: number;
  total_backup_count: number;
}

export interface BackupDetailEntry extends BackupHistoryEntry {
  manifest?: Record<string, unknown>;
  archive_path?: string;
}

export interface BackupVerifyResult {
  filename: string;
  valid: boolean;
  checksum_valid: boolean;
  integrity_valid: boolean;
  compression_valid?: boolean;
  manifest_valid?: boolean;
  corruption_detected?: boolean;
  verification_status: string;
  overall_health?: string;
  warnings: string[];
  errors: string[];
  checks?: VerificationCheckEntry[];
}

export interface VerificationCheckEntry {
  key: string;
  name: string;
  status: string;
  message: string;
}

export interface BackupHistoryFilters {
  page?: number;
  page_size?: number;
  date_from?: string;
  date_to?: string;
  backup_type?: string;
  trigger_type?: string;
  creator?: string;
  status?: string;
  include_archived?: boolean;
}

export interface RecoveryHealthIssue {
  code: string;
  severity: string;
  title: string;
  message: string;
}

export interface RecoveryCenterDashboard {
  system_health: string;
  database_status: string;
  backup_status: string;
  storage_status: string;
  recovery_readiness: string;
  storage_free_bytes: number;
  storage_total_bytes: number;
  storage_used_bytes: number;
  backup_folder: string;
  last_backup_at: string | null;
  last_restore_at: string | null;
  failed_backup_count: number;
  health_issues: RecoveryHealthIssue[];
  readiness_score?: Record<string, number | string>;
  storage_monitoring?: Record<string, number | string | null>;
}

export interface RecoveryValidationCheck {
  key: string;
  name: string;
  status: string;
  message: string;
}

export interface RecoveryValidationResult {
  overall_status: string;
  checks: RecoveryValidationCheck[];
}

export interface RecoveryFailureAnalysis {
  reason: string;
  count: number;
}

export interface RecoveryReports {
  recovery_history: RestoreHistoryEntry[];
  backup_success_rate: number;
  total_backups: number;
  successful_backups: number;
  failed_backups: number;
  failure_analysis: RecoveryFailureAnalysis[];
  export_supported: boolean;
}

export interface BackupSettings {
  backup_folder: string;
  storage_backend: string;
  schedule: string;
  retention_policy: string;
  retention_count: number;
  database_size_bytes: number;
  last_backup_at: string | null;
  next_scheduled_backup_at: string | null;
  health_status: string;
  history: BackupHistoryEntry[];
  restore_history: RestoreHistoryEntry[];
}

export interface BackupSettingsUpdate {
  backup_folder: string;
  storage_backend: 'local' | 'cloud' | 'nas' | 'external_drive';
  schedule: 'manual' | 'daily' | 'weekly' | 'monthly';
  retention_policy: 'last_7' | 'last_30' | 'last_90' | 'unlimited' | 'custom';
  retention_count: number;
}

export interface BackupCreateResult extends BackupHistoryEntry {
  warnings: string[];
  errors: string[];
}

export type RestoreScope =
  | 'entire_database'
  | 'settings_only'
  | 'company_config'
  | 'users_only'
  | 'reports_only';

export type BackupSource = 'local' | 'scheduled' | 'imported';

export interface CompatibilityReport {
  app_version_match: boolean;
  schema_version_match: boolean;
  backup_version_supported: boolean;
  migration_required: boolean;
  restore_allowed: boolean;
  summary: string;
}

export interface BackupValidateResult {
  valid: boolean;
  filename: string;
  source: string;
  checksum_valid: boolean;
  integrity_valid: boolean;
  corruption_detected: boolean;
  app_version: string | null;
  schema_version: string | null;
  backup_version?: string | null;
  current_app_version: string;
  current_schema_version: string;
  compatibility: string;
  backup_type: string | null;
  trigger_type: string | null;
  timestamp: string | null;
  size_bytes: number;
  company_name?: string | null;
  created_by?: string | null;
  database_size_bytes?: number | null;
  inventory_count?: number | null;
  sales_count?: number | null;
  users_count?: number | null;
  audit_log_count?: number | null;
  restore_allowed?: boolean;
  migration_required?: boolean;
  compatibility_report?: CompatibilityReport;
  warnings: string[];
  errors: string[];
}

export interface BackupPreviewResult {
  filename: string;
  source: string;
  restore_scope: RestoreScope;
  scope_implemented: boolean;
  backup_type: string | null;
  trigger_type: string | null;
  timestamp: string | null;
  contents: string[];
  affected_areas: string[];
  warnings: string[];
  emergency_backup_recommended: boolean;
  company_name?: string | null;
  created_by?: string | null;
  app_version?: string | null;
  backup_version?: string | null;
  schema_version?: string | null;
  inventory_count?: number | null;
  sales_count?: number | null;
  users_count?: number | null;
  database_size_bytes?: number | null;
  compressed_size_bytes?: number;
  checksum_valid?: boolean;
  schema_compatibility?: string;
  restore_allowed?: boolean;
  migration_required?: boolean;
  compatibility_summary?: string;
}

export interface BackupRestoreResult {
  success: boolean;
  filename: string;
  restore_scope: RestoreScope;
  emergency_backup_filename: string | null;
  rollback_available: boolean;
  rollback_recommended?: boolean;
  verification_status: string;
  duration_ms: number;
  warnings: string[];
  errors: string[];
  restart_required: boolean;
  verification_checks?: VerificationCheckEntry[];
}

export interface BackupImportResult {
  filename: string;
  size_bytes: number;
  source: string;
}

export interface RestoreHistoryEntry {
  id: number;
  filename: string;
  source: string;
  restore_scope: string;
  status: string;
  verification_status: string;
  emergency_backup_filename: string | null;
  duration_ms: number | null;
  actor_display_name: string | null;
  warnings: string[];
  errors: string[];
  created_at: string;
}

export interface SystemInfoSettings {
  app_version: string;
  api_version: string;
  environment: string;
  database_size_bytes: number;
  storage_total_bytes: number;
  storage_used_bytes: number;
  storage_free_bytes: number;
  backup_folder: string;
  logs_folder: string;
  last_backup_at: string | null;
  api_health: string;
  database_health: string;
}

export interface SettingsWorkspace {
  general: GeneralSettings;
  security: SecuritySettings;
  inventory: InventorySettings;
  sales: SalesSettings;
  tally: TallySettingsGroup;
  integrations: IntegrationsSettings;
  excel: ExcelSettings;
  notifications: NotificationSettings;
  backup: BackupSettings;
  system: SystemInfoSettings;
}

export class SettingsService {
  static async getWorkspace(): Promise<SettingsWorkspace> {
    LoggingService.debug('API', 'Fetching settings workspace');
    const client = await ApiClientProvider.getClient();
    return client.get<SettingsWorkspace>('/api/v1/settings');
  }

  static async updateGeneral(payload: GeneralSettings): Promise<GeneralSettings> {
    const client = await ApiClientProvider.getClient();
    return client.patch<GeneralSettings>('/api/v1/settings/general', payload);
  }

  static async updateSecurity(payload: SecuritySettings): Promise<SecuritySettings> {
    const client = await ApiClientProvider.getClient();
    return client.patch<SecuritySettings>('/api/v1/settings/security', payload);
  }

  static async updateInventory(payload: InventorySettings): Promise<InventorySettings> {
    const client = await ApiClientProvider.getClient();
    return client.patch<InventorySettings>('/api/v1/settings/inventory', payload);
  }

  static async updateSales(payload: SalesSettings): Promise<SalesSettings> {
    const client = await ApiClientProvider.getClient();
    return client.patch<SalesSettings>('/api/v1/settings/sales', payload);
  }

  static async updateTally(payload: TallySettingsGroup): Promise<TallySettingsGroup> {
    const client = await ApiClientProvider.getClient();
    return client.patch<TallySettingsGroup>('/api/v1/settings/tally', payload);
  }

  static async updateIntegrations(payload: IntegrationsSettingsUpdate): Promise<IntegrationsSettings> {
    const client = await ApiClientProvider.getClient();
    return client.patch<IntegrationsSettings>('/api/v1/settings/integrations', payload);
  }

  static async updateExcel(payload: ExcelSettings): Promise<ExcelSettings> {
    const client = await ApiClientProvider.getClient();
    return client.patch<ExcelSettings>('/api/v1/settings/excel', payload);
  }

  static async updateNotifications(payload: NotificationSettings): Promise<NotificationSettings> {
    const client = await ApiClientProvider.getClient();
    return client.patch<NotificationSettings>('/api/v1/settings/notifications', payload);
  }

  static async updateBackup(payload: BackupSettingsUpdate): Promise<BackupSettings> {
    const client = await ApiClientProvider.getClient();
    return client.patch<BackupSettings>('/api/v1/settings/backup', payload);
  }

  static async createBackup(
    payload: { backup_type?: 'full' | 'incremental'; trigger_type?: 'manual' | 'scheduled' } = {},
  ): Promise<BackupCreateResult> {
    LoggingService.info('API', 'Creating enterprise backup');
    const client = await ApiClientProvider.getClient();
    return client.post<BackupCreateResult>('/api/v1/settings/backups', payload);
  }

  static async restoreBackup(payload: {
    filename: string;
    restore_scope?: RestoreScope;
    source?: BackupSource | 'emergency';
    create_emergency_backup?: boolean;
    confirmed?: boolean;
  }): Promise<BackupRestoreResult> {
    LoggingService.warn('API', 'Restoring database backup', payload);
    const client = await ApiClientProvider.getClient();
    return client.post<BackupRestoreResult>('/api/v1/settings/backups/restore', {
      restore_scope: 'entire_database',
      source: 'local',
      create_emergency_backup: true,
      confirmed: false,
      ...payload,
    });
  }

  static async validateBackup(
    filename: string,
    source: BackupSource = 'local',
  ): Promise<BackupValidateResult> {
    const client = await ApiClientProvider.getClient();
    return client.post<BackupValidateResult>('/api/v1/settings/backups/validate', { filename, source });
  }

  static async previewRestore(
    filename: string,
    restoreScope: RestoreScope,
    source: BackupSource = 'local',
  ): Promise<BackupPreviewResult> {
    const client = await ApiClientProvider.getClient();
    return client.post<BackupPreviewResult>('/api/v1/settings/backups/preview', {
      filename,
      restore_scope: restoreScope,
      source,
    });
  }

  static async importBackup(file: File): Promise<BackupImportResult> {
    const client = await ApiClientProvider.getClient();
    const formData = new FormData();
    formData.append('file', file);
    return client.postForm<BackupImportResult>('/api/v1/settings/backups/import', formData);
  }

  static async rollbackBackup(emergencyBackupFilename: string): Promise<BackupRestoreResult> {
    LoggingService.warn('API', 'Rolling back restore', { emergencyBackupFilename });
    const client = await ApiClientProvider.getClient();
    return client.post<BackupRestoreResult>('/api/v1/settings/backups/rollback', {
      emergency_backup_filename: emergencyBackupFilename,
      confirmed: true,
    });
  }

  static async getBackupAdminDashboard(): Promise<BackupAdminDashboard> {
    const client = await ApiClientProvider.getClient();
    return client.get<BackupAdminDashboard>('/api/v1/settings/backups/admin/dashboard');
  }

  static async listBackupHistory(filters: BackupHistoryFilters = {}): Promise<BackupHistoryEntry[]> {
    const client = await ApiClientProvider.getClient();
    return client.get<BackupHistoryEntry[]>(
      '/api/v1/settings/backups/admin/history',
      filters as Record<string, unknown>,
    );
  }

  static async getBackupDetails(filename: string): Promise<BackupDetailEntry> {
    const client = await ApiClientProvider.getClient();
    return client.get<BackupDetailEntry>(`/api/v1/settings/backups/${encodeURIComponent(filename)}/details`);
  }

  static async downloadBackup(filename: string): Promise<Blob> {
    const client = await ApiClientProvider.getClient();
    return client.getBlob(`/api/v1/settings/backups/${encodeURIComponent(filename)}/download`);
  }

  static async verifyBackup(filename: string): Promise<BackupVerifyResult> {
    const client = await ApiClientProvider.getClient();
    return client.post<BackupVerifyResult>(`/api/v1/settings/backups/${encodeURIComponent(filename)}/verify`);
  }

  static async archiveBackup(filename: string): Promise<BackupHistoryEntry> {
    const client = await ApiClientProvider.getClient();
    return client.post<BackupHistoryEntry>(`/api/v1/settings/backups/${encodeURIComponent(filename)}/archive`);
  }

  static async deleteBackup(filename: string): Promise<{ filename: string; deleted: string }> {
    const client = await ApiClientProvider.getClient();
    return client.delete(`/api/v1/settings/backups/${encodeURIComponent(filename)}`);
  }

  static async exportBackupHistory(format: 'xlsx' | 'pdf', filters: BackupHistoryFilters = {}): Promise<Blob> {
    const client = await ApiClientProvider.getClient();
    return client.getBlob('/api/v1/settings/backups/admin/history/export', { format, ...filters });
  }

  static async getRecoveryCenter(): Promise<RecoveryCenterDashboard> {
    const client = await ApiClientProvider.getClient();
    return client.get<RecoveryCenterDashboard>('/api/v1/settings/recovery/center');
  }

  static async runRecoveryValidation(): Promise<RecoveryValidationResult> {
    const client = await ApiClientProvider.getClient();
    return client.post<RecoveryValidationResult>('/api/v1/settings/recovery/validate');
  }

  static async getRecoveryHealthChecks(): Promise<RecoveryHealthIssue[]> {
    const client = await ApiClientProvider.getClient();
    return client.get<RecoveryHealthIssue[]>('/api/v1/settings/recovery/health-checks');
  }

  static async getRecoveryReports(): Promise<RecoveryReports> {
    const client = await ApiClientProvider.getClient();
    return client.get<RecoveryReports>('/api/v1/settings/recovery/reports');
  }
}
