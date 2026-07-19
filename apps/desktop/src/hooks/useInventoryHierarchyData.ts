import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDebounce } from '../lib/useDebounce';
import { permissionsDependencyKey, referenceDataFetchPlan } from '../lib/permissionFetchPlan';
import { BrandService, type Brand } from '../services/api/BrandService';
import { DashboardService, type DashboardDistribution } from '../services/api/DashboardService';
import { InventoryService, type InventoryItemDetail } from '../services/api/InventoryService';
import { LocationService, type Location } from '../services/api/LocationService';
import { ProductModelService, type ProductModel } from '../services/api/ProductModelService';
import type { HierarchySearchField } from '../lib/hierarchySearch';
import {
  buildBrandSummaries,
  buildModelRows,
  matchesModelSearch,
  type BrandInventorySummary,
  type ModelInventoryRow,
} from '../lib/inventoryHierarchy';

export interface InventoryHierarchyData {
  brands: Brand[];
  models: ProductModel[];
  locations: Location[];
  distribution: DashboardDistribution | null;
  brandSummaries: BrandInventorySummary[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  modelsForBrand: (brandId: number) => {
    all: ModelInventoryRow[];
    inStock: ModelInventoryRow[];
    zeroStock: ModelInventoryRow[];
  };
  filterModels: (
    brandId: number,
    search: string,
    includeZeroStock: boolean,
    searchField?: HierarchySearchField,
  ) => ModelInventoryRow[];
  filterStockModels: (
    brandId: number,
    search: string,
    searchField?: HierarchySearchField,
  ) => ModelInventoryRow[];
  filterInventoryModels: (
    brandId: number,
    search: string,
    searchField?: HierarchySearchField,
  ) => ModelInventoryRow[];
  unitsForModel: (modelId: string, availableOnly?: boolean) => InventoryItemDetail[];
  sampleItemForModel: (modelId: string) => InventoryItemDetail | null;
}

async function fetchAllInventoryItems(): Promise<InventoryItemDetail[]> {
  const items: InventoryItemDetail[] = [];
  let page = 1;
  let totalPages = 1;

  while (page <= totalPages) {
    const result = await InventoryService.listItems({
      include_archived: false,
      page_size: 100,
      page,
    });
    items.push(...result.items);
    totalPages = result.total_pages;
    page += 1;
  }

  return items;
}

export function useInventoryHierarchyData(permissions: string[] = []): InventoryHierarchyData {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [models, setModels] = useState<ProductModel[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [items, setItems] = useState<InventoryItemDetail[]>([]);
  const [distribution, setDistribution] = useState<DashboardDistribution | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const permissionsRef = useRef(permissions);
  permissionsRef.current = permissions;
  const permissionsKey = permissionsDependencyKey(permissions);

  const refresh = useCallback(
    async (options?: { silent?: boolean }) => {
      const silent = options?.silent === true;
      if (!silent) {
        setLoading(true);
        setError(null);
      }
      try {
        const plan = referenceDataFetchPlan(permissionsRef.current);
        const [brandList, modelList, locationList, dist, inventoryItems] = await Promise.all([
          plan.needsBrands ? BrandService.listBrands() : Promise.resolve([]),
          plan.needsProductModels
            ? ProductModelService.listModels({ archived: false })
            : Promise.resolve([]),
          plan.needsLocations ? LocationService.listLocations() : Promise.resolve([]),
          plan.needsDistribution ? DashboardService.getDistribution() : Promise.resolve(null),
          plan.needsInventoryItems ? fetchAllInventoryItems() : Promise.resolve([]),
        ]);
        setBrands(brandList);
        setModels(modelList);
        setLocations(locationList.filter((location) => location.is_active));
        setDistribution(dist);
        setItems(inventoryItems);
        if (!silent) setError(null);
      } catch (err: unknown) {
        if (!silent) {
          const message = err as { message?: string };
          setError(message.message ?? 'Unable to load inventory data.');
        }
      } finally {
        if (!silent) setLoading(false);
      }
    },
    [permissionsKey],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Quiet refresh when the window regains focus (e.g. after a Tally sale elsewhere).
  // No periodic polling — totals update from local mutations immediately and on focus.
  useEffect(() => {
    const onFocus = () => {
      void refresh({ silent: true });
    };
    window.addEventListener('focus', onFocus);
    return () => {
      window.removeEventListener('focus', onFocus);
    };
  }, [refresh]);

  const brandSummaries = useMemo(
    () => buildBrandSummaries(brands, distribution?.by_brand ?? [], items),
    [brands, distribution?.by_brand, items],
  );

  const itemsByModel = useMemo(() => {
    const map = new Map<string, InventoryItemDetail[]>();
    for (const item of items) {
      const bucket = map.get(item.product_model_id) ?? [];
      bucket.push(item);
      map.set(item.product_model_id, bucket);
    }
    return map;
  }, [items]);

  const modelsForBrand = useCallback(
    (brandId: number) => buildModelRows(models, distribution?.by_product_model ?? [], brandId),
    [distribution?.by_product_model, models],
  );

  const filterModels = useCallback(
    (
      brandId: number,
      search: string,
      includeZeroStock: boolean,
      searchField: HierarchySearchField = 'all',
    ) => {
      const { inStock, zeroStock } = modelsForBrand(brandId);
      const pool = includeZeroStock ? [...inStock, ...zeroStock] : inStock;
      if (!search.trim()) return pool;
      return pool.filter((row) => {
        const units = itemsByModel.get(row.model.id) ?? [];
        return matchesModelSearch(row.model, units, search, searchField);
      });
    },
    [itemsByModel, modelsForBrand],
  );

  const filterInventoryModels = useCallback(
    (brandId: number, search: string, searchField: HierarchySearchField = 'all') => {
      const { all } = modelsForBrand(brandId);
      if (!search.trim()) return all;
      return all.filter((row) => {
        const units = itemsByModel.get(row.model.id) ?? [];
        return matchesModelSearch(row.model, units, search, searchField);
      });
    },
    [itemsByModel, modelsForBrand],
  );

  const filterStockModels = useCallback(
    (brandId: number, search: string, searchField: HierarchySearchField = 'all') => {
      const { inStock } = modelsForBrand(brandId);
      if (!search.trim()) return inStock;
      return inStock.filter((row) => {
        const units = itemsByModel.get(row.model.id) ?? [];
        return matchesModelSearch(row.model, units, search, searchField);
      });
    },
    [itemsByModel, modelsForBrand],
  );

  const unitsForModel = useCallback(
    (modelId: string, availableOnly = false) => {
      const modelItems = itemsByModel.get(modelId) ?? [];
      if (!availableOnly) return modelItems;
      return modelItems.filter((item) => item.status !== 'sold' && !item.is_archived);
    },
    [itemsByModel],
  );

  const sampleItemForModel = useCallback(
    (modelId: string) => itemsByModel.get(modelId)?.[0] ?? null,
    [itemsByModel],
  );

  return {
    brands,
    models,
    locations,
    distribution,
    brandSummaries,
    loading,
    error,
    refresh,
    modelsForBrand,
    filterModels,
    filterStockModels,
    filterInventoryModels,
    unitsForModel,
    sampleItemForModel,
  };
}

export function useDebouncedHierarchySearch(search: string, delay = 250): string {
  return useDebounce(search, delay);
}
