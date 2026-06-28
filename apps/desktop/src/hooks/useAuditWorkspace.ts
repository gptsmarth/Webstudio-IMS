import { useCallback, useEffect, useState } from 'react';
import { useDebounce } from '../lib/useDebounce';
import { auditFiltersToExportParams } from '../lib/auditExport';
import type { AuditViewMode } from '../lib/audit';
import { LocationService, type Location } from '../services/api/LocationService';
import { ReportService } from '../services/api/ReportService';
import { UserService, type UserSummary } from '../services/api/UserService';
import {
  AuditService,
  type AuditListEntry,
  type AuditLogDetail,
  type AuditAction,
  type AuditSource,
} from '../services/api/AuditService';

export interface AuditFilters {
  userId: number | null;
  role: string;
  operation: AuditAction | '';
  module: string;
  source: AuditSource | '';
  locationId: number | null;
  result: '' | 'success' | 'failure';
  serialNumber: string;
  invoiceNumber: string;
  modelNumber: string;
  dateFrom: string;
  dateTo: string;
}

export const DEFAULT_AUDIT_FILTERS: AuditFilters = {
  userId: null,
  role: '',
  operation: '',
  module: '',
  source: '',
  locationId: null,
  result: '',
  serialNumber: '',
  invoiceNumber: '',
  modelNumber: '',
  dateFrom: '',
  dateTo: '',
};

export interface AuditWorkspaceState {
  items: AuditListEntry[];
  users: UserSummary[];
  locations: Location[];
  loading: boolean;
  error: string | null;
  search: string;
  setSearch: (value: string) => void;
  filters: AuditFilters;
  setFilters: (patch: Partial<AuditFilters>) => void;
  resetFilters: () => void;
  viewMode: AuditViewMode;
  setViewMode: (mode: AuditViewMode) => void;
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  setPage: (page: number) => void;
  selectedId: string | null;
  selectedEntry: AuditLogDetail | null;
  selectEntry: (id: string | null) => void;
  drawerLoading: boolean;
  refresh: () => Promise<void>;
  exportAudit: (format: 'xlsx' | 'pdf') => Promise<void>;
  actionLoading: boolean;
  actionError: string | null;
  clearActionError: () => void;
}

export function useAuditWorkspace(): AuditWorkspaceState {
  const [items, setItems] = useState<AuditListEntry[]>([]);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filters, setFiltersState] = useState<AuditFilters>(DEFAULT_AUDIT_FILTERS);
  const [viewMode, setViewMode] = useState<AuditViewMode>('table');
  const [page, setPage] = useState(1);
  const pageSize = 25;
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<AuditLogDetail | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const debouncedSearch = useDebounce(search, 300);

  const setFilters = useCallback((patch: Partial<AuditFilters>) => {
    setFiltersState((current) => ({ ...current, ...patch }));
    setPage(1);
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState(DEFAULT_AUDIT_FILTERS);
    setPage(1);
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const [userResult, locationRows] = await Promise.all([
          UserService.listUsers({ page_size: 100 }),
          LocationService.listLocations(),
        ]);
        setUsers(userResult.items);
        setLocations(locationRows);
      } catch {
        setUsers([]);
        setLocations([]);
      }
    })();
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await AuditService.listLogs({
        page,
        page_size: pageSize,
        search: debouncedSearch.trim() || undefined,
        actor_user_id: filters.userId ?? undefined,
        actor_role: filters.role || undefined,
        action: filters.operation || undefined,
        entity_type: filters.module ? mapModuleToEntityType(filters.module) : undefined,
        source: filters.source || undefined,
        location_id: filters.locationId ?? undefined,
        result: filters.result || undefined,
        serial_number: filters.serialNumber.trim() || undefined,
        invoice_number: filters.invoiceNumber.trim() || undefined,
        model_number: filters.modelNumber.trim() || undefined,
        created_at_from: filters.dateFrom ? `${filters.dateFrom}T00:00:00Z` : undefined,
        created_at_to: filters.dateTo ? `${filters.dateTo}T23:59:59Z` : undefined,
      });
      setItems(result.items);
      setTotalItems(result.total_items);
      setTotalPages(result.total_pages);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to load audit logs.');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, debouncedSearch, filters]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const selectEntry = useCallback((id: string | null) => {
    setSelectedId(id);
    if (!id) setSelectedEntry(null);
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setDrawerLoading(true);
    void (async () => {
      try {
        const detail = await AuditService.getLog(selectedId);
        if (!cancelled) setSelectedEntry(detail);
      } catch (err: unknown) {
        if (cancelled) return;
        const message = err as { message?: string };
        setActionError(message.message ?? 'Unable to load audit details.');
      } finally {
        if (!cancelled) setDrawerLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const exportAudit = useCallback(
    async (format: 'xlsx' | 'pdf') => {
      setActionLoading(true);
      setActionError(null);
      try {
        await ReportService.exportReport(
          'audit',
          format,
          auditFiltersToExportParams(filters, debouncedSearch),
        );
      } catch (err: unknown) {
        const message = err as { message?: string };
        setActionError(message.message ?? 'Export failed.');
        throw err;
      } finally {
        setActionLoading(false);
      }
    },
    [filters, debouncedSearch],
  );

  return {
    items,
    users,
    locations,
    loading,
    error,
    search,
    setSearch,
    filters,
    setFilters,
    resetFilters,
    viewMode,
    setViewMode,
    page,
    pageSize,
    totalItems,
    totalPages,
    setPage,
    selectedId,
    selectedEntry,
    selectEntry,
    drawerLoading,
    refresh,
    exportAudit,
    actionLoading,
    actionError,
    clearActionError: () => setActionError(null),
  };
}

function mapModuleToEntityType(module: string): string | undefined {
  const map: Record<string, string> = {
    Inventory: 'inventory_item',
    Sales: 'sale',
    Catalogue: 'brand',
    Users: 'user',
    System: 'system',
    Notifications: 'notification',
    Reports: 'report',
  };
  return map[module];
}
