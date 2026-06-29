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
}

export interface BackupHistoryEntry {
  filename: string;
  size_bytes: number;
  created_at: string;
}

export interface BackupSettings {
  backup_folder: string;
  database_size_bytes: number;
  last_backup_at: string | null;
  history: BackupHistoryEntry[];
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

  static async createBackup(): Promise<BackupHistoryEntry> {
    LoggingService.info('API', 'Creating database backup');
    const client = await ApiClientProvider.getClient();
    const result = await client.post<{ filename: string; size_bytes: number; created_at: string }>(
      '/api/v1/settings/backups',
    );
    return result;
  }

  static async restoreBackup(filename: string): Promise<void> {
    LoggingService.warn('API', 'Restoring database backup', { filename });
    const client = await ApiClientProvider.getClient();
    await client.post('/api/v1/settings/backups/restore', { filename });
  }
}
