import { create } from 'zustand';
import type { HierarchySearchField } from '../lib/hierarchySearch';
import type { ProductCategoryFilter } from '../lib/productCategory';

export type HierarchyLevel = 'brands' | 'models' | 'serials';

const STOCK_SHOW_SELLING_PRICE_KEY = 'webstudio_stock_show_selling_price';
const STOCK_SHOW_LIVE_PRICE_KEY = 'webstudio_stock_show_live_price';

function readShowSellingPrice(): boolean {
  if (typeof window === 'undefined') return true;
  const stored = localStorage.getItem(STOCK_SHOW_SELLING_PRICE_KEY);
  if (stored === 'false') return false;
  return true;
}

function readShowLivePrice(): boolean {
  if (typeof window === 'undefined') return true;
  const stored = localStorage.getItem(STOCK_SHOW_LIVE_PRICE_KEY);
  if (stored === 'false') return false;
  return true;
}

export interface HierarchyNavState {
  level: HierarchyLevel;
  brandId: number | null;
  brandName: string | null;
  modelId: string | null;
  modelLabel: string | null;
  search: string;
  searchField: HierarchySearchField;
  productCategoryFilter: ProductCategoryFilter;
  showZeroStock: boolean;
  showSellingPrice: boolean;
  showLivePrice: boolean;
  scrollTops: Record<string, number>;
  setScrollTop: (key: string, value: number) => void;
  getScrollTop: (key: string) => number | undefined;
  openBrand: (brandId: number, brandName: string) => void;
  openModel: (modelId: string, modelLabel: string) => void;
  goToBrands: () => void;
  goToModels: () => void;
  setSearch: (value: string) => void;
  setSearchField: (value: HierarchySearchField) => void;
  setProductCategoryFilter: (value: ProductCategoryFilter) => void;
  setShowZeroStock: (value: boolean) => void;
  setShowSellingPrice: (value: boolean) => void;
  setShowLivePrice: (value: boolean) => void;
  reset: () => void;
}

const INITIAL = {
  level: 'brands' as HierarchyLevel,
  brandId: null,
  brandName: null,
  modelId: null,
  modelLabel: null,
  search: '',
  searchField: 'all' as HierarchySearchField,
  productCategoryFilter: 'all' as ProductCategoryFilter,
  showZeroStock: false,
  showSellingPrice: readShowSellingPrice(),
  showLivePrice: readShowLivePrice(),
  scrollTops: {},
};

function createHierarchyNavStore(defaultShowZeroStock = false) {
  const initial = { ...INITIAL, showZeroStock: defaultShowZeroStock };

  return create<HierarchyNavState>((set, get) => ({
    ...initial,
    setScrollTop: (key, value) =>
      set((state) => ({
        scrollTops: { ...state.scrollTops, [key]: value },
      })),
    getScrollTop: (key) => get().scrollTops[key],
    openBrand: (brandId, brandName) =>
      set((state) => ({
        level: 'models',
        brandId,
        brandName,
        modelId: null,
        modelLabel: null,
        search: '',
        searchField: state.searchField,
        showZeroStock: state.showZeroStock,
      })),
    openModel: (modelId, modelLabel) =>
      set({
        level: 'serials',
        modelId,
        modelLabel,
      }),
    goToBrands: () =>
      set((state) => ({
        ...initial,
        scrollTops: state.scrollTops,
        showSellingPrice: state.showSellingPrice,
        showLivePrice: state.showLivePrice,
      })),
    goToModels: () =>
      set((state) => ({
        level: 'models',
        modelId: null,
        modelLabel: null,
        search: state.search,
        searchField: state.searchField,
        showZeroStock: state.showZeroStock,
        scrollTops: state.scrollTops,
      })),
    setSearch: (search) => set({ search }),
    setSearchField: (searchField) => set({ searchField }),
    setProductCategoryFilter: (productCategoryFilter) => set({ productCategoryFilter }),
    setShowZeroStock: (showZeroStock) => set({ showZeroStock }),
    setShowSellingPrice: (showSellingPrice) => {
      localStorage.setItem(STOCK_SHOW_SELLING_PRICE_KEY, String(showSellingPrice));
      set({ showSellingPrice });
    },
    setShowLivePrice: (showLivePrice) => {
      localStorage.setItem(STOCK_SHOW_LIVE_PRICE_KEY, String(showLivePrice));
      set({ showLivePrice });
    },
    reset: () =>
      set({
        ...initial,
        showSellingPrice: readShowSellingPrice(),
        showLivePrice: readShowLivePrice(),
      }),
  }));
}

/** Stock module navigation (all roles). */
export const useStockNavStore = createHierarchyNavStore(false);

/** Admin inventory navigation (admin / main_admin). */
export const useInventoryNavStore = createHierarchyNavStore(true);
