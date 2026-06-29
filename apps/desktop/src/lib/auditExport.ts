import type { AuditFilters } from '../hooks/useAuditWorkspace';
import type { ReportQueryParams } from '../services/api/ReportService';

export function auditFiltersToExportParams(
  filters: AuditFilters,
  search: string,
): ReportQueryParams {
  return {
    search: search.trim() || undefined,
    user_id: filters.userId ?? undefined,
    actor_role: filters.role || undefined,
    audit_action: filters.operation || undefined,
    audit_source: filters.source || undefined,
    security_only: (filters.securityOnly || filters.module === 'Security') ? true : undefined,
    audit_severity: filters.severity || undefined,
    location_id: filters.locationId ?? undefined,
    serial_number: filters.serialNumber.trim() || undefined,
    invoice_number: filters.invoiceNumber.trim() || undefined,
    date_from: filters.dateFrom ? `${filters.dateFrom}T00:00:00Z` : undefined,
    date_to: filters.dateTo ? `${filters.dateTo}T23:59:59Z` : undefined,
  };
}

export function hasActiveAuditFilters(filters: AuditFilters, search: string): boolean {
  return Boolean(
    search.trim()
    || filters.userId
    || filters.role
    || filters.operation
    || filters.module
    || filters.source
    || filters.locationId
    || filters.result
    || filters.serialNumber.trim()
    || filters.invoiceNumber.trim()
    || filters.modelNumber.trim()
    || filters.dateFrom
    || filters.dateTo
    || filters.severity
    || filters.securityOnly
    || filters.module === 'Security'
  );
}
