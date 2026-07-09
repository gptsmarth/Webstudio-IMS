import { useCallback, useEffect, useMemo, useState } from 'react';
import { useDebounce } from '../lib/useDebounce';
import { referenceDataFetchPlan } from '../lib/permissionFetchPlan';
import { parseApiError } from '../lib/apiError';
import { sanitizeCreateProductModelPayload } from '../lib/productModelPayload';
import { BrandService, type Brand } from '../services/api/BrandService';
import { LocationService, type Location } from '../services/api/LocationService';
import {
  InventoryService,
  type InventoryItemDetail,
  type InventoryListParams,
  type InventoryStatus,
  type MarkSoldRequest,
  type SaleDetail,
} from '../services/api/InventoryService';
import { ProductModelService, type ProductModel } from '../services/api/ProductModelService';
import type { AddInventoryBatchRequest } from '../components/inventory/AddInventoryDialog';
import type { AddLaptopWizardRequest } from '../components/inventory/AddLaptopWizard';
import { ReportService } from '../services/api/ReportService';
import { inventoryFiltersToExportParams } from '../lib/inventoryExport';
import { AuditService, type AuditLogEntry } from '../services/api/AuditService';
import { useInventoryStore } from '../store';

export type InventorySortField = 'serial_number' | 'status' | 'color' | 'updated_at' | 'created_at';

export interface InventoryFilters {
  brandId: number | null;
  locationId: number | null;
  status: InventoryStatus | '' | 'archived';
  color: string;
  createdDateFrom: string;
  createdDateTo: string;
  includeArchived: boolean;
}

export const DEFAULT_FILTERS: InventoryFilters = {
  brandId: null,
  locationId: null,
  status: '',
  color: '',
  createdDateFrom: '',
  createdDateTo: '',
  includeArchived: false,
};

export interface InventoryWorkspaceState {
  items: InventoryItemDetail[];
  brands: Brand[];
  locations: Location[];
  loading: boolean;
  error: string | null;
  search: string;
  setSearch: (value: string) => void;
  filters: InventoryFilters;
  setFilters: (patch: Partial<InventoryFilters>) => void;
  resetFilters: () => void;
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  setPage: (page: number) => void;
  sortField: InventorySortField;
  sortDirection: 'asc' | 'desc';
  toggleSort: (field: InventorySortField) => void;
  selectedId: string | null;
  selectedItem: InventoryItemDetail | null;
  selectItem: (id: string | null) => void;
  auditLogs: AuditLogEntry[];
  saleDetail: SaleDetail | null;
  productModel: ProductModel | null;
  siblingUnits: InventoryItemDetail[];
  drawerLoading: boolean;
  refresh: () => Promise<void>;
  refreshSelected: () => Promise<void>;
  transferLocation: (locationId: number) => Promise<void>;
  markSold: (payload: MarkSoldRequest) => Promise<void>;
  archiveItem: (id?: string) => Promise<void>;
  restoreItem: (id?: string) => Promise<void>;
  updateItem: (patch: { serial_number?: string; color?: string }) => Promise<void>;
  addInventoryBatch: (payload: AddInventoryBatchRequest) => Promise<void>;
  addLaptopWizard: (payload: AddLaptopWizardRequest) => Promise<void>;
  exportInventory: (format: 'xlsx' | 'pdf') => Promise<void>;
  productModels: ProductModel[];
  loadProductModels: (brandId: number | null) => Promise<void>;
  actionLoading: boolean;
  actionError: string | null;
  clearActionError: () => void;
}

function filtersToParams(
  filters: InventoryFilters,
  search: string,
  page: number,
  pageSize: number,
  sort: string,
): InventoryListParams {
  const params: InventoryListParams = {
    page,
    page_size: pageSize,
    sort,
    include_archived: filters.includeArchived,
  };

  if (search.trim()) params.search = search.trim();
  if (filters.brandId) params.brand_id = filters.brandId;
  if (filters.locationId) params.current_location_id = filters.locationId;
  if (filters.color.trim()) params.color = filters.color.trim();
  if (filters.createdDateFrom) params.created_at_from = filters.createdDateFrom;
  if (filters.createdDateTo) params.created_at_to = filters.createdDateTo;

  if (filters.status === 'archived') {
    params.is_archived = true;
  } else if (filters.status) {
    params.status = filters.status;
    params.is_archived = false;
  }

  return params;
}

function extractSaleFromAudit(logs: AuditLogEntry[]): SaleDetail | null {
  for (const log of logs) {
    const value = log.new_value;
    if (!value) continue;
    if (typeof value.invoice_number === 'string') {
      return {
        id: 0,
        inventory_item_id: log.inventory_item_id ?? '',
        serial_number: typeof value.serial_number === 'string' ? value.serial_number : '',
        sale_source: log.source === 'TALLY_SYNC' ? 'tally' : 'manual',
        sold_at: log.created_at,
        invoice_number: value.invoice_number,
        customer_name: typeof value.customer_name === 'string' ? value.customer_name : null,
        payment_mode: typeof value.payment_mode === 'string' ? value.payment_mode : null,
        sale_amount: typeof value.sale_amount === 'number' ? value.sale_amount : null,
        notes: typeof value.remarks === 'string' ? value.remarks : null,
        recorded_by_user_id: log.actor_user_id,
        created_at: log.created_at,
      };
    }
  }
  return null;
}

export function useInventoryWorkspace(permissions: string[] = []): InventoryWorkspaceState {
  const focus = useInventoryStore((state) => state.focus);
  const clearFocus = useInventoryStore((state) => state.clearFocus);

  const [items, setItems] = useState<InventoryItemDetail[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filters, setFiltersState] = useState<InventoryFilters>(DEFAULT_FILTERS);
  const [productModels, setProductModels] = useState<ProductModel[]>([]);
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [sortField, setSortField] = useState<InventorySortField>('updated_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [saleDetail, setSaleDetail] = useState<SaleDetail | null>(null);
  const [productModel, setProductModel] = useState<ProductModel | null>(null);
  const [siblingUnits, setSiblingUnits] = useState<InventoryItemDetail[]>([]);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const clearActionError = useCallback(() => setActionError(null), []);

  const debouncedSearch = useDebounce(search, 300);
  const sort = `${sortField}:${sortDirection}`;

  const selectedItem = useMemo(
    () => items.find((item) => item.id === selectedId) ?? null,
    [items, selectedId],
  );

  const setFilters = useCallback((patch: Partial<InventoryFilters>) => {
    setFiltersState((current) => ({ ...current, ...patch }));
    setPage(1);
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState(DEFAULT_FILTERS);
    setPage(1);
  }, []);

  const toggleSort = useCallback((field: InventorySortField) => {
    setSortField((currentField) => {
      if (currentField === field) {
        setSortDirection((currentDir) => (currentDir === 'asc' ? 'desc' : 'asc'));
        return currentField;
      }
      setSortDirection('asc');
      return field;
    });
    setPage(1);
  }, []);

  const loadReferenceData = useCallback(async () => {
    const plan = referenceDataFetchPlan(permissions);
    const [brandList, locationList] = await Promise.all([
      plan.needsBrands ? BrandService.listBrands() : Promise.resolve([]),
      plan.needsLocations ? LocationService.listLocations() : Promise.resolve([]),
    ]);
    setBrands(brandList.filter((brand) => brand.is_active));
    setLocations(locationList.filter((location) => location.is_active));
  }, [permissions]);

  const loadProductModels = useCallback(
    async (brandId: number | null) => {
      const plan = referenceDataFetchPlan(permissions);
      if (!plan.needsProductModels) {
        setProductModels([]);
        return;
      }
      try {
        const models = await ProductModelService.listModels(brandId ?? undefined);
        setProductModels(models);
      } catch {
        setProductModels([]);
      }
    },
    [permissions],
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await InventoryService.listItems(
        filtersToParams(filters, debouncedSearch, page, pageSize, sort),
      );
      setItems(result.items);
      setTotalItems(result.total_items);
      setTotalPages(result.total_pages);
    } catch (err: unknown) {
      setError(parseApiError(err));
      setItems([]);
      setTotalItems(0);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, filters, page, pageSize, sort]);

  const loadDrawerData = useCallback(
    async (itemId: string) => {
      const plan = referenceDataFetchPlan(permissions);
      setDrawerLoading(true);
      try {
        const item = await InventoryService.getItem(itemId);
        const [logs, siblingsResult, model] = await Promise.all([
          plan.needsInventoryAudit
            ? AuditService.listForInventoryItem(itemId)
            : Promise.resolve([]),
          plan.needsInventoryItems
            ? InventoryService.listItems({
                product_model_id: item.product_model_id,
                page_size: 50,
                include_archived: true,
              })
            : Promise.resolve({ items: [] }),
          plan.needsProductModels
            ? ProductModelService.getModel(item.product_model_id).catch(() => null)
            : Promise.resolve(null),
        ]);
        setItems((current) => current.map((row) => (row.id === itemId ? item : row)));
        setAuditLogs(logs);
        setSaleDetail(extractSaleFromAudit(logs));
        setProductModel(model);
        setSiblingUnits(siblingsResult.items);
      } catch {
        setAuditLogs([]);
        setSaleDetail(null);
        setProductModel(null);
        setSiblingUnits([]);
      } finally {
        setDrawerLoading(false);
      }
    },
    [permissions],
  );

  const selectItem = useCallback(
    (id: string | null) => {
      setSelectedId(id);
      if (id) void loadDrawerData(id);
      else {
        setAuditLogs([]);
        setSaleDetail(null);
        setProductModel(null);
        setSiblingUnits([]);
      }
    },
    [loadDrawerData],
  );

  const refreshSelected = useCallback(async () => {
    if (!selectedId) return;
    await loadDrawerData(selectedId);
    await refresh();
  }, [loadDrawerData, refresh, selectedId]);

  useEffect(() => {
    void loadReferenceData().catch(() => {
      // Reference data failure is non-fatal; filters degrade gracefully.
    });
  }, [loadReferenceData]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!focus) return;
    if (focus.search) setSearch(focus.search);
    if (focus.itemId) selectItem(focus.itemId);
    clearFocus();
  }, [focus, clearFocus, selectItem]);

  const runAction = useCallback(
    async (operation: () => Promise<void>) => {
      setActionLoading(true);
      setActionError(null);
      try {
        await operation();
        await refreshSelected();
      } catch (err: unknown) {
        const message = parseApiError(err);
        setActionError(message);
        throw new Error(message);
      } finally {
        setActionLoading(false);
      }
    },
    [refreshSelected],
  );

  const transferLocation = useCallback(
    async (locationId: number) => {
      if (!selectedId) return;
      await runAction(async () => {
        await InventoryService.transferLocation(selectedId, locationId);
      });
    },
    [runAction, selectedId],
  );

  const markSold = useCallback(
    async (payload: MarkSoldRequest) => {
      if (!selectedId) return;
      await runAction(async () => {
        const response = await InventoryService.markSold(selectedId, payload);
        setSaleDetail(response.sale);
      });
    },
    [runAction, selectedId],
  );

  const archiveItem = useCallback(
    async (id?: string) => {
      const targetId = id ?? selectedId;
      if (!targetId) return;
      await runAction(async () => {
        await InventoryService.archiveItem(targetId);
      });
    },
    [runAction, selectedId],
  );

  const restoreItem = useCallback(
    async (id?: string) => {
      const targetId = id ?? selectedId;
      if (!targetId) return;
      await runAction(async () => {
        await InventoryService.restoreItem(targetId);
      });
    },
    [runAction, selectedId],
  );

  const updateItem = useCallback(
    async (patch: { serial_number?: string; color?: string }) => {
      if (!selectedId) return;
      await runAction(async () => {
        await InventoryService.updateItem(selectedId, patch);
      });
    },
    [runAction, selectedId],
  );

  const addInventoryBatch = useCallback(
    async (payload: AddInventoryBatchRequest) => {
      setActionLoading(true);
      setActionError(null);
      try {
        let modelId = payload.productModelId;
        if (payload.mode === 'new' && payload.newProductModel) {
          const model = await ProductModelService.createModel(
            sanitizeCreateProductModelPayload(payload.newProductModel),
          );
          modelId = model.id;
          await loadProductModels(payload.newProductModel.brand_id);
        }
        if (!modelId) throw new Error('Product model is required.');

        let lastCreated: InventoryItemDetail | null = null;
        for (const serialNumber of payload.serialNumbers) {
          lastCreated = await InventoryService.createItem({
            serial_number: serialNumber,
            product_model_id: modelId,
            color: payload.color,
            current_location_id: payload.current_location_id,
            status: payload.status,
          });
        }

        if (lastCreated) {
          setSelectedId(lastCreated.id);
          await loadDrawerData(lastCreated.id);
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
    [loadDrawerData, loadProductModels, refresh],
  );

  const addLaptopWizard = useCallback(
    async (payload: AddLaptopWizardRequest) => {
      setActionLoading(true);
      setActionError(null);
      try {
        let modelId = payload.productModelId;
        if (payload.mode === 'new' && payload.newProductModel) {
          const model = await ProductModelService.createModel(
            sanitizeCreateProductModelPayload(payload.newProductModel),
          );
          modelId = model.id;
          await loadProductModels(payload.newProductModel.brand_id);
        }
        if (!modelId) throw new Error('Product model is required.');

        let lastCreated: InventoryItemDetail | null = null;
        for (const unit of payload.units) {
          lastCreated = await InventoryService.createItem({
            serial_number: unit.serial_number.trim(),
            product_model_id: modelId,
            color: unit.color.trim(),
            current_location_id: unit.current_location_id,
            status: payload.status,
            purchase_price: unit.purchase_price ?? undefined,
          });
        }

        if (lastCreated) {
          setSelectedId(lastCreated.id);
          await loadDrawerData(lastCreated.id);
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
    [loadDrawerData, loadProductModels, refresh],
  );

  const exportInventory = useCallback(
    async (format: 'xlsx' | 'pdf') => {
      setActionError(null);
      try {
        await ReportService.exportReport(
          'inventory',
          format,
          inventoryFiltersToExportParams(filters, debouncedSearch, sortField, sortDirection),
        );
      } catch (err: unknown) {
        setActionError(parseApiError(err));
        throw err;
      }
    },
    [debouncedSearch, filters, sortDirection, sortField],
  );

  return {
    items,
    brands,
    locations,
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
    auditLogs,
    saleDetail,
    productModel,
    siblingUnits,
    drawerLoading,
    refresh,
    refreshSelected,
    transferLocation,
    markSold,
    archiveItem,
    restoreItem,
    updateItem,
    addInventoryBatch,
    addLaptopWizard,
    exportInventory,
    productModels,
    loadProductModels,
    actionLoading,
    actionError,
    clearActionError,
  };
}
