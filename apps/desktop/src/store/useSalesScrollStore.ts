import { create } from 'zustand';

interface SalesScrollState {
  scrollTops: Record<string, number>;
  getScrollTop: (key: string) => number | undefined;
  setScrollTop: (key: string, value: number) => void;
}

/**
 * Persists the sales table's scroll offset across SalesPage unmount/remount
 * (e.g. switching sidebar sections and back), mirroring the pattern already
 * used for Stock/Inventory hierarchy scroll (useHierarchyScrollRef + a
 * module-level store survives the page's own component lifecycle).
 */
export const useSalesScrollStore = create<SalesScrollState>((set, get) => ({
  scrollTops: {},
  getScrollTop: (key) => get().scrollTops[key],
  setScrollTop: (key, value) =>
    set((state) => ({ scrollTops: { ...state.scrollTops, [key]: value } })),
}));
