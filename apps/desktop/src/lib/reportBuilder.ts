import { dateInputToRange, resolveDatePreset, type DatePreset } from './reportDatePresets';
import type { BuilderReportType, ReportQueryParams } from '../services/api/ReportService';

export type InventoryStatusFilter = '' | 'available' | 'sold' | 'archived';
export type LocationTypeFilter = '' | 'warehouse' | 'retail_floor' | 'other';
export type SaleSourceFilter = '' | 'manual' | 'tally';
export type SyncStatusFilter = '' | 'unread' | 'read' | 'resolved';
export type TallyOutcomeFilter =
  | ''
  | 'processed'
  | 'skipped'
  | 'duplicate'
  | 'missing_serial'
  | 'missing_model'
  | 'model_mismatch';

export interface ReportBuilderFilters {
  search: string;
  datePreset: DatePreset;
  dateFrom: string;
  dateTo: string;
  brandId: number | null;
  locationId: number | null;
  locationType: LocationTypeFilter;
  productModelId: string | null;
  serialNumber: string;
  inventoryStatus: InventoryStatusFilter;
  color: string;
  userId: number | null;
  invoiceNumber: string;
  customerName: string;
  paymentMode: string;
  saleSource: SaleSourceFilter;
  auditAction: string;
  auditSource: string;
  actorRole: string;
  notificationType: string;
  syncStatus: SyncStatusFilter;
  tallyOutcome: TallyOutcomeFilter;
  company: string;
}

export const DEFAULT_REPORT_FILTERS: ReportBuilderFilters = {
  search: '',
  datePreset: '',
  dateFrom: '',
  dateTo: '',
  brandId: null,
  locationId: null,
  locationType: '',
  productModelId: null,
  serialNumber: '',
  inventoryStatus: '',
  color: '',
  userId: null,
  invoiceNumber: '',
  customerName: '',
  paymentMode: '',
  saleSource: '',
  auditAction: '',
  auditSource: '',
  actorRole: '',
  notificationType: '',
  syncStatus: '',
  tallyOutcome: '',
  company: '',
};

const TALLY_OUTCOME_TO_TYPE: Record<Exclude<TallyOutcomeFilter, ''>, string> = {
  processed: 'tally_sync_completed',
  skipped: 'sync_failure',
  duplicate: 'duplicate_sale',
  missing_serial: 'serial_number_missing',
  missing_model: 'product_model_missing',
  model_mismatch: 'product_model_mismatch',
};

export function tallyOutcomeNotificationType(outcome: TallyOutcomeFilter): string | undefined {
  if (!outcome) return undefined;
  return TALLY_OUTCOME_TO_TYPE[outcome];
}

export function buildReportQueryParams(
  reportType: BuilderReportType,
  filters: ReportBuilderFilters,
  page: number,
  pageSize: number,
  sortField: string | null,
  sortDirection: 'asc' | 'desc',
): ReportQueryParams {
  const presetRange =
    filters.datePreset && filters.datePreset !== 'custom'
      ? resolveDatePreset(filters.datePreset)
      : dateInputToRange(filters.dateFrom, filters.dateTo);

  const params: ReportQueryParams = {
    page,
    page_size: pageSize,
    search: filters.search.trim() || undefined,
    brand_id: filters.brandId ?? undefined,
    location_id: filters.locationId ?? undefined,
    location_type: filters.locationType || undefined,
    product_model_id: filters.productModelId ?? undefined,
    serial_number: filters.serialNumber.trim() || undefined,
    sort_field: sortField ?? undefined,
    sort_direction: sortDirection,
  };

  if (reportType === 'inventory') {
    params.color = filters.color.trim() || undefined;
    params.date_from = presetRange.from || undefined;
    params.date_to = presetRange.to || undefined;
    if (filters.inventoryStatus === 'available') {
      params.status = 'available';
      params.is_archived = false;
    } else if (filters.inventoryStatus === 'sold') {
      params.status = 'sold';
    } else if (filters.inventoryStatus === 'archived') {
      params.is_archived = true;
    }
  }

  if (reportType === 'sales') {
    params.date_from = presetRange.from || undefined;
    params.date_to = presetRange.to || undefined;
    params.user_id = filters.userId ?? undefined;
    params.invoice_number = filters.invoiceNumber.trim() || undefined;
    params.customer_name = filters.customerName.trim() || undefined;
    params.payment_mode = filters.paymentMode.trim() || undefined;
    params.sale_source = filters.saleSource || undefined;
  }

  if (reportType === 'audit') {
    params.date_from = presetRange.from || undefined;
    params.date_to = presetRange.to || undefined;
    params.user_id = filters.userId ?? undefined;
    params.audit_action = filters.auditAction || undefined;
    params.audit_source = filters.auditSource || undefined;
    params.actor_role = filters.actorRole.trim() || undefined;
  }

  if (reportType === 'tally') {
    params.date_from = presetRange.from || undefined;
    params.date_to = presetRange.to || undefined;
    params.notification_category = 'tally_sync';
    params.status = filters.syncStatus || undefined;
    const outcomeType = tallyOutcomeNotificationType(filters.tallyOutcome);
    params.notification_type = outcomeType ?? (filters.notificationType || undefined);
    if (filters.invoiceNumber.trim()) {
      params.search = filters.invoiceNumber.trim();
    } else if (filters.company.trim()) {
      params.search = filters.company.trim();
    }
  }

  return params;
}

export const REPORT_TYPE_LABELS: Record<BuilderReportType, string> = {
  inventory: 'Inventory',
  sales: 'Sales',
  audit: 'Audit',
  tally: 'Tally',
};
