import { create } from 'zustand';
import type { WorkspaceRoute } from '../config/navigation';

interface NavigationState {
  currentRoute: WorkspaceRoute;
  setRoute: (route: WorkspaceRoute) => void;
}

export const useNavigationStore = create<NavigationState>((set) => ({
  currentRoute: 'dashboard',
  setRoute: (route) => set({ currentRoute: route }),
}));
