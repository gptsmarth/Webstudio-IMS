import { create } from 'zustand';
import type { HierarchySearchField } from '../lib/hierarchySearch';

export type HierarchyLevel = 'brands' | 'models' | 'serials';

const STOCK_SHOW_SELLING_PRICE_KEY = 'webstudio_stock_show_selling_price';

function readShowSellingPrice(): boolean {
  if (typeof window === 'undefined') return true;
  const stored = localStorage.getItem(STOCK_SHOW_SELLING_PRICE_KEY);
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
  showZeroStock: boolean;
  showSellingPrice: boolean;
  openBrand: (brandId: number, brandName: string) => void;
  openModel: (modelId: string, modelLabel: string) => void;
  goToBrands: () => void;
  goToModels: () => void;
  setSearch: (value: string) => void;
  setSearchField: (value: HierarchySearchField) => void;
  setShowZeroStock: (value: boolean) => void;
  setShowSellingPrice: (value: boolean) => void;
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
  showZeroStock: false,
  showSellingPrice: readShowSellingPrice(),
};

function createHierarchyNavStore(defaultShowZeroStock = false) {
  const initial = { ...INITIAL, showZeroStock: defaultShowZeroStock };

  return create<HierarchyNavState>((set) => ({
    ...initial,
    openBrand: (brandId, brandName) => set((state) => ({
      level: 'models',
      brandId,
      brandName,
      modelId: null,
      modelLabel: null,
      search: '',
      searchField: state.searchField,
      showZeroStock: state.showZeroStock,
    })),
    openModel: (modelId, modelLabel) => set({
      level: 'serials',
      modelId,
      modelLabel,
    }),
    goToBrands: () => set({ ...initial }),
    goToModels: () => set((state) => ({
      level: 'models',
      modelId: null,
      modelLabel: null,
      search: state.search,
      searchField: state.searchField,
      showZeroStock: state.showZeroStock,
    })),
    setSearch: (search) => set({ search }),
    setSearchField: (searchField) => set({ searchField }),
    setShowZeroStock: (showZeroStock) => set({ showZeroStock }),
    setShowSellingPrice: (showSellingPrice) => {
      localStorage.setItem(STOCK_SHOW_SELLING_PRICE_KEY, String(showSellingPrice));
      set({ showSellingPrice });
    },
    reset: () => set({ ...initial, showSellingPrice: readShowSellingPrice() }),
  }));
}

/** Stock module navigation (all roles). */
export const useStockNavStore = createHierarchyNavStore(false);

/** Admin inventory navigation (admin / main_admin). */
export const useInventoryNavStore = createHierarchyNavStore(true);
