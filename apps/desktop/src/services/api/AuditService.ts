import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export type AuditAction =
  | 'CREATE'
  | 'UPDATE'
  | 'ARCHIVE'
  | 'RESTORE'
  | 'STATUS_CHANGE'
  | 'LOCATION_CHANGE'
  | 'SYSTEM_ACTION';

export type AuditSource = 'MANUAL' | 'TALLY_SYNC' | 'BACKGROUND_JOB' | 'SYSTEM';

export interface AuditLogEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  inventory_item_id: string | null;
  actor_user_id: number | null;
  actor_display_name: string | null;
  actor_role: string | null;
  action: AuditAction;
  source: AuditSource;
  field_name: string | null;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  description: string | null;
  created_at: string;
}

export interface AuditListEntry extends AuditLogEntry {
  module: string;
  operation: string;
  serial_number: string | null;
  location_name: string | null;
  invoice_number: string | null;
  model_number: string | null;
  result: string;
}

export interface AuditLogDetail extends AuditListEntry {
  request_id: string | null;
  correlation_id: string | null;
  related_inventory_item_id: string | null;
  related_sale_id: string | null;
  related_tally_sync: boolean;
}

export interface AuditListParams {
  entity_type?: string;
  entity_id?: string;
  inventory_item_id?: string;
  serial_number?: string;
  actor_user_id?: number;
  actor_role?: string;
  action?: AuditAction;
  source?: AuditSource;
  location_id?: number;
  invoice_number?: string;
  model_number?: string;
  search?: string;
  result?: 'success' | 'failure';
  created_at_from?: string;
  created_at_to?: string;
  page?: number;
  page_size?: number;
}

export interface AuditListResult {
  items: AuditListEntry[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

interface ListMeta {
  page?: number;
  page_size?: number;
  total_items?: number;
  total_pages?: number;
}

export class AuditService {
  static async listLogs(params?: AuditListParams): Promise<AuditListResult> {
    LoggingService.debug('API', 'Fetching audit logs', params as unknown as Record<string, unknown>);
    const client = await ApiClientProvider.getClient();
    const response = await client.getRaw<AuditListEntry[], ListMeta>('/api/v1/audit_logs', {
      page: 1,
      page_size: 50,
      ...params,
    } as Record<string, unknown>);
    return {
      items: response.data,
      page: response.meta?.page ?? params?.page ?? 1,
      page_size: response.meta?.page_size ?? params?.page_size ?? 50,
      total_items: response.meta?.total_items ?? response.data.length,
      total_pages: response.meta?.total_pages ?? 1,
    };
  }

  static async getLog(auditLogId: string): Promise<AuditLogDetail> {
    LoggingService.debug('API', 'Fetching audit log detail', { auditLogId });
    const client = await ApiClientProvider.getClient();
    return client.get<AuditLogDetail>(`/api/v1/audit_logs/${auditLogId}`);
  }

  static async listForInventoryItem(inventoryItemId: string, pageSize = 100): Promise<AuditListEntry[]> {
    const result = await this.listLogs({
      inventory_item_id: inventoryItemId,
      page_size: pageSize,
    });
    return result.items;
  }

  static async listLifecycleBySerial(serialNumber: string, pageSize = 100): Promise<AuditListEntry[]> {
    LoggingService.debug('API', 'Fetching audit lifecycle', { serialNumber });
    const client = await ApiClientProvider.getClient();
    const response = await client.getRaw<AuditListEntry[], ListMeta>(
      `/api/v1/audit_logs/lifecycle/by-serial/${encodeURIComponent(serialNumber)}`,
      { page: 1, page_size: pageSize } as Record<string, unknown>,
    );
    return response.data;
  }
}
