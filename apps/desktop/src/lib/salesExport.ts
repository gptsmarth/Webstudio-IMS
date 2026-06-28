import type { SalesFilters } from '../hooks/useSalesWorkspace';
import type { ReportQueryParams } from '../services/api/ReportService';

export function salesFiltersToExportParams(
  filters: SalesFilters,
  search: string,
  sortField: string,
  sortDirection: 'asc' | 'desc',
): ReportQueryParams {
  return {
    sort_field: sortField,
    sort_direction: sortDirection,
    search: search.trim() || undefined,
    brand_id: filters.brandId ?? undefined,
    location_id: filters.locationId ?? undefined,
    user_id: filters.userId ?? undefined,
    invoice_number: filters.invoiceNumber.trim() || undefined,
    customer_name: filters.customerName.trim() || undefined,
    payment_mode: filters.paymentMode.trim() || undefined,
    sale_source: filters.saleSource || undefined,
    date_from: filters.dateFrom ? `${filters.dateFrom}T00:00:00Z` : undefined,
    date_to: filters.dateTo ? `${filters.dateTo}T23:59:59Z` : undefined,
  };
}

export function hasActiveSalesFilters(filters: SalesFilters, search: string): boolean {
  return Boolean(
    search.trim()
    || filters.brandId
    || filters.locationId
    || filters.userId
    || filters.invoiceNumber.trim()
    || filters.customerName.trim()
    || filters.paymentMode.trim()
    || filters.saleSource
    || filters.dateFrom
    || filters.dateTo,
  );
}
