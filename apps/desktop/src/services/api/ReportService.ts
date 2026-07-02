import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';
import { triggerBlobDownload } from '../../lib/downloadBlob';

export type BuilderReportType = 'inventory' | 'sales' | 'audit' | 'tally';
export type ExportFormat = 'xlsx' | 'pdf';
export type ExportReportType = 'inventory' | 'sales' | 'audit' | 'notification';

export interface ReportQueryParams {
  page?: number;
  page_size?: number;
  date_from?: string;
  date_to?: string;
  purchase_date_from?: string;
  purchase_date_to?: string;
  brand_id?: number;
  location_id?: number;
  location_type?: string;
  product_model_id?: string;
  user_id?: number;
  status?: string;
  is_archived?: boolean;
  serial_number?: string;
  color?: string;
  invoice_number?: string;
  customer_name?: string;
  payment_mode?: string;
  sale_source?: string;
  audit_action?: string;
  audit_source?: string;
  actor_role?: string;
  security_only?: boolean;
  audit_severity?: string;
  notification_type?: string;
  notification_category?: string;
  search?: string;
  sort_field?: string;
  sort_direction?: 'asc' | 'desc';
}

interface ListMeta {
  page?: number;
  page_size?: number;
  total_items?: number;
  total_pages?: number;
}

export interface InventoryReportRow {
  serial_number: string;
  brand_name: string;
  model_number: string;
  model_name: string;
  color: string;
  location_name: string;
  status: string;
  is_archived: boolean;
  purchase_date: string | null;
  created_at: string;
}

export interface SalesReportRow {
  serial_number: string;
  brand_name: string;
  model_number: string;
  model_name: string;
  location_name: string;
  invoice_number: string;
  customer_name: string | null;
  payment_mode: string | null;
  sale_source: string;
  sold_at: string;
  recorded_by_user_id: number | null;
  recorded_by_display_name: string | null;
}

export interface AuditReportRow {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  source: string;
  actor_display_name: string | null;
  actor_user_id: number | null;
  description: string | null;
  serial_number: string | null;
  created_at: string;
}

export interface NotificationReportRow {
  id: number;
  notification_type: string;
  title: string;
  description: string;
  category: string;
  severity: string;
  status: string;
  created_at: string;
  resolved_at: string | null;
}

export interface ReportPreviewResult<T> {
  rows: T[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  summary?: { total_rows: number; by_status: Record<string, number> };
}

function previewPath(reportType: BuilderReportType): string {
  if (reportType === 'tally') return '/api/v1/reports/notifications';
  return `/api/v1/reports/${reportType}`;
}

function exportReportType(reportType: BuilderReportType): ExportReportType {
  return reportType === 'tally' ? 'notification' : reportType;
}

export class ReportService {
  static async preview<T>(
    reportType: BuilderReportType,
    params: ReportQueryParams,
  ): Promise<ReportPreviewResult<T>> {
    LoggingService.debug('API', `Preview ${reportType} report`, params as Record<string, unknown>);
    const client = await ApiClientProvider.getClient();
    const response = await client.getRaw<{ rows: T[]; summary?: ReportPreviewResult<T>['summary'] }, ListMeta>(
      previewPath(reportType),
      params as Record<string, unknown>,
    );
    const meta = response.meta ?? {};
    return {
      rows: response.data.rows,
      summary: response.data.summary,
      page: meta.page ?? params.page ?? 1,
      page_size: meta.page_size ?? params.page_size ?? 50,
      total_items: meta.total_items ?? response.data.rows.length,
      total_pages: meta.total_pages ?? 1,
    };
  }

  static async exportReport(reportType: BuilderReportType, format: ExportFormat, params: ReportQueryParams): Promise<void> {
    LoggingService.info('API', `Export ${reportType} report`, { format });
    const client = await ApiClientProvider.getClient();
    const queryParams: Record<string, unknown> = {
      report_type: exportReportType(reportType),
      format,
    };

    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return;
      if (typeof value === 'boolean') {
        queryParams[key] = value ? 'true' : 'false';
        return;
      }
      queryParams[key] = value;
    });

    const blob = await client.getBlob('/api/v1/reports/export', queryParams);
    triggerBlobDownload(blob, `report-${reportType}.${format}`);
  }
}
