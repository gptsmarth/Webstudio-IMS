import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';
import type { TallyOperationalSummary, TallySyncHistoryEntry } from '../../lib/tallyDisplay';

export interface TallyConnectionStage {
  stage: string;
  label: string;
  success: boolean;
  message: string;
}

export interface TallyConnectionTestResult {
  connected: boolean;
  reachable: boolean;
  host_resolved: boolean;
  tcp_connected: boolean;
  xml_responding: boolean;
  configured_host: string;
  resolved_ip: string | null;
  port: string;
  tally_version: string | null;
  company_name: string | null;
  message: string;
  status: string;
  stages: TallyConnectionStage[];
}

export interface TallyCompanyStatus {
  company_name: string;
  last_successful_sync_time: string | null;
  last_error: string | null;
  connection_status: string;
  connectivity_status?: string;
  sync_in_progress?: boolean;
}

export interface TallyDashboardStats {
  invoices_processed: number;
  inventory_entries: number;
  duplicates: number;
  missing_serials: number;
  model_mismatches: number;
  failures: number;
}

export interface TallyDashboardData {
  connection_status: 'connected' | 'disconnected' | 'error';
  connectivity_status?: string;
  enabled: boolean;
  tally_host: string;
  tally_port: string;
  resolved_ip?: string | null;
  sync_interval_seconds: number;
  next_scheduled_sync_at: string | null;
  last_successful_sync_at: string | null;
  last_successful_connection_at?: string | null;
  last_failed_connection_at?: string | null;
  voucher_types: string[];
  companies: TallyCompanyStatus[];
  pending_notifications_count: number;
  last_error: string | null;
  stats: TallyDashboardStats;
  operational: TallyOperationalSummary;
  recent_synchronizations: TallySyncHistoryEntry[];
}

export interface TallyStatusSummary {
  available: boolean;
  is_connected: boolean;
  connection_label: string;
  connection_status: 'connected' | 'disconnected' | 'error' | 'unavailable';
  connectivity_status?: string;
  resolved_ip?: string | null;
  last_successful_connection_at?: string | null;
  last_failed_connection_at?: string | null;
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
  operational?: TallyOperationalSummary;
  pending_retry: boolean;
  todays_imports: number;
}

export interface TallySyncHistoryFilters {
  status?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export type { TallyOperationalSummary, TallySyncHistoryEntry };

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

  static async getSyncHistory(filters: TallySyncHistoryFilters = {}): Promise<TallySyncHistoryEntry[]> {
    const client = await ApiClientProvider.getClient();
    const params = new URLSearchParams();
    if (filters.status) params.set('status', filters.status);
    if (filters.date_from) params.set('date_from', filters.date_from);
    if (filters.date_to) params.set('date_to', filters.date_to);
    if (filters.search) params.set('search', filters.search);
    if (filters.limit) params.set('limit', String(filters.limit));
    if (filters.offset) params.set('offset', String(filters.offset));
    const query = params.toString();
    return client.get<TallySyncHistoryEntry[]>(
      `/api/v1/integrations/tally/sync/history${query ? `?${query}` : ''}`,
    );
  }

  static async exportSyncHistory(filters: TallySyncHistoryFilters = {}): Promise<void> {
    const client = await ApiClientProvider.getClient();
    const params = new URLSearchParams();
    if (filters.status) params.set('status', filters.status);
    if (filters.date_from) params.set('date_from', filters.date_from);
    if (filters.date_to) params.set('date_to', filters.date_to);
    if (filters.search) params.set('search', filters.search);
    const query = params.toString();
    const blob = await client.getBlob(
      `/api/v1/integrations/tally/sync/history/export${query ? `?${query}` : ''}`,
    );
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'tally-sync-history.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  }

  static async testConnection(): Promise<TallyConnectionTestResult> {
    const client = await ApiClientProvider.getClient();
    return client.post<TallyConnectionTestResult>(
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
        is_connected: false,
        connection_label: 'Disconnected',
        connection_status: 'unavailable',
        connectivity_status: 'offline',
        resolved_ip: null,
        last_successful_connection_at: null,
        last_failed_connection_at: null,
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
        pending_retry: false,
        todays_imports: 0,
      };
    }

    const operational = data.operational;
    const lastSync =
      data.last_successful_sync_at ??
      data.companies
        .map((company) => company.last_successful_sync_time)
        .filter(Boolean)
        .sort()
        .reverse()[0] ??
      null;

    return {
      available: data.enabled,
      is_connected: operational.is_connected,
      connection_label: operational.connection_label,
      connection_status: data.connection_status,
      connectivity_status: data.connectivity_status,
      resolved_ip: data.resolved_ip ?? null,
      last_successful_connection_at: data.last_successful_connection_at ?? null,
      last_failed_connection_at: data.last_failed_connection_at ?? null,
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
      connection_health: operational.sync_health,
      last_error: data.last_error,
      voucher_types: data.voucher_types,
      operational,
      pending_retry: operational.pending_retry,
      todays_imports: operational.todays_imports,
    };
  }
}
