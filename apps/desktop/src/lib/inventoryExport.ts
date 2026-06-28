import type { InventoryFilters } from '../hooks/useInventoryWorkspace';
import type { ReportQueryParams } from '../services/api/ReportService';

export function inventoryFiltersToExportParams(
  filters: InventoryFilters,
  search: string,
  sortField: string,
  sortDirection: 'asc' | 'desc',
): ReportQueryParams {
  const params: ReportQueryParams = {
    sort_field: sortField,
    sort_direction: sortDirection,
    search: search.trim() || undefined,
    brand_id: filters.brandId ?? undefined,
    location_id: filters.locationId ?? undefined,
    color: filters.color.trim() || undefined,
    date_from: filters.createdDateFrom ? `${filters.createdDateFrom}T00:00:00` : undefined,
    date_to: filters.createdDateTo ? `${filters.createdDateTo}T23:59:59` : undefined,
  };

  if (filters.status === 'archived') {
    params.is_archived = true;
  } else if (filters.status) {
    params.status = filters.status;
    params.is_archived = false;
  } else if (filters.includeArchived) {
    // Export API has no include_archived flag; omit is_archived to include all rows.
  } else {
    params.is_archived = false;
  }

  return params;
}

export function hasActiveInventoryFilters(filters: InventoryFilters, search: string): boolean {
  return Boolean(
    search.trim()
    || filters.brandId
    || filters.locationId
    || filters.status
    || filters.color.trim()
    || filters.createdDateFrom
    || filters.createdDateTo
    || filters.includeArchived,
  );
}
