import { create } from 'zustand';

export interface InventoryFocus {
  itemId?: string;
  search?: string;
}

interface InventoryState {
  focus: InventoryFocus | null;
  setFocus: (focus: InventoryFocus) => void;
  clearFocus: () => void;
}

export const useInventoryStore = create<InventoryState>((set) => ({
  focus: null,
  setFocus: (focus) => set({ focus }),
  clearFocus: () => set({ focus: null }),
}));
