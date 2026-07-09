import { useCallback, useEffect, useMemo, useState } from 'react';
import { useDebounce } from '../lib/useDebounce';
import { referenceDataFetchPlan } from '../lib/permissionFetchPlan';
import { salesFiltersToExportParams } from '../lib/salesExport';
import { AuditService, type AuditLogEntry } from '../services/api/AuditService';
import { BrandService, type Brand } from '../services/api/BrandService';
import { LocationService, type Location } from '../services/api/LocationService';
import { ReportService } from '../services/api/ReportService';
import { SalesService, type SaleDetail, type SaleListItem } from '../services/api/SalesService';

export type SalesSortField =
  | 'sold_at'
  | 'invoice_number'
  | 'customer_name'
  | 'serial_number'
  | 'brand_name'
  | 'model_name'
  | 'location_name'
  | 'payment_mode'
  | 'sale_source';

export interface SalespersonOption {
  id: number;
  displayName: string;
}

export interface SalesFilters {
  brandId: number | null;
  locationId: number | null;
  userId: number | null;
  invoiceNumber: string;
  customerName: string;
  paymentMode: string;
  saleSource: '' | 'manual' | 'tally';
  dateFrom: string;
  dateTo: string;
}

export const DEFAULT_SALES_FILTERS: SalesFilters = {
  brandId: null,
  locationId: null,
  userId: null,
  invoiceNumber: '',
  customerName: '',
  paymentMode: '',
  saleSource: '',
  dateFrom: '',
  dateTo: '',
};

export interface SalesWorkspaceState {
  items: SaleListItem[];
  brands: Brand[];
  locations: Location[];
  salespeople: SalespersonOption[];
  loading: boolean;
  error: string | null;
  search: string;
  setSearch: (value: string) => void;
  filters: SalesFilters;
  setFilters: (patch: Partial<SalesFilters>) => void;
  resetFilters: () => void;
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  setPage: (page: number) => void;
  sortField: SalesSortField;
  sortDirection: 'asc' | 'desc';
  toggleSort: (field: SalesSortField) => void;
  selectedId: number | null;
  selectedItem: SaleListItem | null;
  selectItem: (id: number | null) => void;
  saleDetail: SaleDetail | null;
  auditLogs: AuditLogEntry[];
  drawerLoading: boolean;
  refresh: () => Promise<void>;
  exportSales: (format: 'xlsx' | 'pdf') => Promise<void>;
  actionLoading: boolean;
  actionError: string | null;
  clearActionError: () => void;
  cancelSale: (saleId: number, reason?: string | null) => Promise<void>;
}

function parseApiError(err: unknown): string {
  const message = err as { response?: { data?: { detail?: string } }; message?: string };
  return message.response?.data?.detail ?? message.message ?? 'Request failed.';
}

function mergeSalespeople(
  current: SalespersonOption[],
  items: SaleListItem[],
): SalespersonOption[] {
  const map = new Map(current.map((entry) => [entry.id, entry]));
  for (const item of items) {
    if (item.recorded_by_user_id && item.recorded_by_display_name) {
      map.set(item.recorded_by_user_id, {
        id: item.recorded_by_user_id,
        displayName: item.recorded_by_display_name,
      });
    }
  }
  return Array.from(map.values()).sort((a, b) => a.displayName.localeCompare(b.displayName));
}

export function useSalesWorkspace(permissions: string[] = []): SalesWorkspaceState {
  const [items, setItems] = useState<SaleListItem[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [salespeople, setSalespeople] = useState<SalespersonOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filters, setFiltersState] = useState<SalesFilters>(DEFAULT_SALES_FILTERS);
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [saleDetail, setSaleDetail] = useState<SaleDetail | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SalesSortField>('sold_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const debouncedSearch = useDebounce(search, 300);
  const selectedItem = useMemo(
    () => items.find((item) => item.id === selectedId) ?? null,
    [items, selectedId],
  );

  const setFilters = useCallback((patch: Partial<SalesFilters>) => {
    setFiltersState((current) => ({ ...current, ...patch }));
    setPage(1);
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState(DEFAULT_SALES_FILTERS);
    setPage(1);
  }, []);

  const toggleSort = useCallback((field: SalesSortField) => {
    setSortField((currentField) => {
      if (currentField === field) {
        setSortDirection((currentDirection) => (currentDirection === 'asc' ? 'desc' : 'asc'));
        return currentField;
      }
      setSortDirection(field === 'sold_at' ? 'desc' : 'asc');
      return field;
    });
    setPage(1);
  }, []);

  const loadDrawerData = useCallback(
    async (saleId: number) => {
      setDrawerLoading(true);
      try {
        const detail = await SalesService.getSale(saleId);
        setSaleDetail(detail);
        if (detail.inventory_item_id) {
          const plan = referenceDataFetchPlan(permissions);
          if (plan.needsInventoryAudit) {
            const logs = await AuditService.listForInventoryItem(detail.inventory_item_id);
            setAuditLogs(logs);
          } else {
            setAuditLogs([]);
          }
        } else {
          setAuditLogs([]);
        }
      } catch {
        setSaleDetail(null);
        setAuditLogs([]);
      } finally {
        setDrawerLoading(false);
      }
    },
    [permissions],
  );

  const selectItem = useCallback(
    (id: number | null) => {
      setSelectedId(id);
      setSaleDetail(null);
      setAuditLogs([]);
      if (id) void loadDrawerData(id);
    },
    [loadDrawerData],
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await SalesService.listSales({
        page,
        page_size: pageSize,
        search: debouncedSearch.trim() || undefined,
        brand_id: filters.brandId ?? undefined,
        location_id: filters.locationId ?? undefined,
        user_id: filters.userId ?? undefined,
        invoice_number: filters.invoiceNumber.trim() || undefined,
        customer_name: filters.customerName.trim() || undefined,
        payment_mode: filters.paymentMode.trim() || undefined,
        sale_source: filters.saleSource || undefined,
        date_from: filters.dateFrom ? `${filters.dateFrom}T00:00:00Z` : undefined,
        date_to: filters.dateTo ? `${filters.dateTo}T23:59:59Z` : undefined,
        sort_field: sortField,
        sort_direction: sortDirection,
      });
      setItems(result.items);
      setTotalItems(result.total_items);
      setTotalPages(result.total_pages);
      setSalespeople((current) => mergeSalespeople(current, result.items));
    } catch (err: unknown) {
      const message = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(message.response?.data?.detail ?? message.message ?? 'Unable to load sales.');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, filters, page, pageSize, sortDirection, sortField]);

  const exportSales = useCallback(
    async (format: 'xlsx' | 'pdf') => {
      setActionLoading(true);
      setActionError(null);
      try {
        await ReportService.exportReport(
          'sales',
          format,
          salesFiltersToExportParams(filters, debouncedSearch, sortField, sortDirection),
        );
      } catch (err: unknown) {
        const message = parseApiError(err);
        setActionError(message);
        throw new Error(message);
      } finally {
        setActionLoading(false);
      }
    },
    [debouncedSearch, filters, sortDirection, sortField],
  );

  useEffect(() => {
    const plan = referenceDataFetchPlan(permissions);
    if (!plan.needsBrands && !plan.needsLocations) return;
    void Promise.all([
      plan.needsBrands ? BrandService.listBrands() : Promise.resolve([]),
      plan.needsLocations ? LocationService.listLocations() : Promise.resolve([]),
    ])
      .then(([brandList, locationList]) => {
        setBrands(brandList.filter((brand) => brand.is_active));
        setLocations(locationList.filter((location) => location.is_active));
      })
      .catch(() => undefined);
  }, [permissions]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (selectedId && !items.some((item) => item.id === selectedId)) {
      setSelectedId(null);
      setSaleDetail(null);
      setAuditLogs([]);
    }
  }, [items, selectedId]);

  const clearActionError = useCallback(() => {
    setActionError(null);
  }, []);

  const cancelSale = useCallback(
    async (saleId: number, reason?: string | null) => {
      setActionLoading(true);
      setActionError(null);
      try {
        await SalesService.cancelSale(saleId, reason);
        if (selectedId === saleId) {
          setSelectedId(null);
          setSaleDetail(null);
          setAuditLogs([]);
        }
        await refresh();
      } catch (err: unknown) {
        const message = parseApiError(err);
        setActionError(message);
        throw new Error(message);
      } finally {
        setActionLoading(false);
      }
    },
    [refresh, selectedId],
  );

  return {
    items,
    brands,
    locations,
    salespeople,
    loading,
    error,
    search,
    setSearch,
    filters,
    setFilters,
    resetFilters,
    page,
    pageSize,
    totalItems,
    totalPages,
    setPage,
    sortField,
    sortDirection,
    toggleSort,
    selectedId,
    selectedItem,
    selectItem,
    saleDetail,
    auditLogs,
    drawerLoading,
    refresh,
    exportSales,
    actionLoading,
    actionError,
    clearActionError,
    cancelSale,
  };
}
