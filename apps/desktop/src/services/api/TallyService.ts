import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export interface TallyCompanyStatus {
  company_name: string;
  last_successful_sync_time: string | null;
  last_processed_voucher_identifier: string | null;
  last_processed_guid: string | null;
  last_error: string | null;
  connection_status: string;
}

export interface TallyDashboardStats {
  invoices_processed: number;
  inventory_entries: number;
  duplicates: number;
  missing_serials: number;
  model_mismatches: number;
  failures: number;
}

export interface TallySyncLogEntry {
  sync_run_id: string;
  voucher_type: string | null;
  printed_invoice_number: string | null;
  voucher_number: string | null;
  status: string;
  started_at: string;
  completed_at: string | null;
  successfully_updated: number;
  already_sold: number;
  missing_serial: number;
  model_mismatches: number;
}

export interface TallyDashboardData {
  connection_status: 'connected' | 'disconnected' | 'error';
  enabled: boolean;
  tally_host: string;
  tally_port: string;
  sync_interval_seconds: number;
  next_scheduled_sync_at: string | null;
  last_successful_sync_at: string | null;
  voucher_types: string[];
  companies: TallyCompanyStatus[];
  pending_notifications_count: number;
  last_error: string | null;
  stats: TallyDashboardStats;
  recent_synchronizations: TallySyncLogEntry[];
}

export interface TallyStatusSummary {
  available: boolean;
  connection_status: 'connected' | 'disconnected' | 'error' | 'unavailable';
  last_sync: string | null;
  next_scheduled_sync: string | null;
  connected_companies: number;
  invoices_processed: number;
  inventory_entries_processed: number;
  skipped_invoices: number;
  duplicate_invoices: number;
  model_mismatches: number;
  missing_serials: number;
  sync_failures: number;
  pending_issues: number;
  connection_health: 'healthy' | 'degraded' | 'offline';
  last_error: string | null;
  voucher_types: string[];
}

export class TallyService {
  static async getDashboard(): Promise<TallyDashboardData | null> {
    LoggingService.debug('API', 'Fetching Tally dashboard');
    const client = await ApiClientProvider.getClient();
    try {
      return await client.get<TallyDashboardData>('/api/v1/integrations/tally/dashboard');
    } catch {
      return null;
    }
  }

  static async getSyncStatus(): Promise<TallyStatusSummary> {
    LoggingService.debug('API', 'Fetching Tally sync status');
    const client = await ApiClientProvider.getClient();
    try {
      return await client.get<TallyStatusSummary>('/api/v1/integrations/tally/status');
    } catch {
      return TallyService.toSummary(null);
    }
  }

  static async testConnection(): Promise<{ connected: boolean; message: string }> {
    const client = await ApiClientProvider.getClient();
    return client.post<{ connected: boolean; message: string }>(
      '/api/v1/integrations/tally/connection/test',
    );
  }

  static async triggerSync(companyName?: string): Promise<void> {
    LoggingService.info('API', 'Triggering manual Tally synchronization');
    const client = await ApiClientProvider.getClient();
    await client.post('/api/v1/integrations/tally/sync/trigger', companyName ? { company_name: companyName } : {});
  }

  static async retrySync(): Promise<void> {
    const client = await ApiClientProvider.getClient();
    await client.post('/api/v1/integrations/tally/sync/retry', {});
  }

  static toSummary(data: TallyDashboardData | null): TallyStatusSummary {
    if (!data) {
      return {
        available: false,
        connection_status: 'unavailable',
        last_sync: null,
        next_scheduled_sync: null,
        connected_companies: 0,
        invoices_processed: 0,
        inventory_entries_processed: 0,
        skipped_invoices: 0,
        duplicate_invoices: 0,
        model_mismatches: 0,
        missing_serials: 0,
        sync_failures: 0,
        pending_issues: 0,
        connection_health: 'offline',
        last_error: null,
        voucher_types: [],
      };
    }

    const lastSync =
      data.last_successful_sync_at ??
      data.companies
        .map((company) => company.last_successful_sync_time)
        .filter(Boolean)
        .sort()
        .reverse()[0] ??
      null;

    return {
      available: true,
      connection_status: data.connection_status,
      last_sync: lastSync,
      next_scheduled_sync: data.next_scheduled_sync_at,
      connected_companies: data.companies.length,
      invoices_processed: data.stats.invoices_processed,
      inventory_entries_processed: data.stats.inventory_entries,
      skipped_invoices: 0,
      duplicate_invoices: data.stats.duplicates,
      model_mismatches: data.stats.model_mismatches,
      missing_serials: data.stats.missing_serials,
      sync_failures: data.stats.failures,
      pending_issues: data.pending_notifications_count,
      connection_health:
        data.connection_status === 'connected' && !data.last_error
          ? 'healthy'
          : data.connection_status === 'error'
            ? 'offline'
            : 'degraded',
      last_error: data.last_error,
      voucher_types: data.voucher_types,
    };
  }
}
