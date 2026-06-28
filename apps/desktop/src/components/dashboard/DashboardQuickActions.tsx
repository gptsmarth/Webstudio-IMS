import {
  FileSpreadsheet,
  PackagePlus,
  RefreshCw,
  Search,
  ShoppingBag,
  Truck,
} from 'lucide-react';
import type { UserRole, WorkspaceRoute } from '../../config/navigation';
import { useNavigationStore, useSearchStore } from '../../store';

interface DashboardQuickActionsProps {
  role: UserRole;
  onTallySync: () => void;
  syncingTally: boolean;
}

const ACTIONS: {
  id: string;
  label: string;
  icon: typeof Search;
  route?: WorkspaceRoute;
  search?: boolean;
  adminOnly?: boolean;
  tally?: boolean;
}[] = [
  { id: 'add', label: 'Add Laptop', icon: PackagePlus, route: 'inventory' },
  { id: 'search', label: 'Search', icon: Search, search: true },
  { id: 'transfer', label: 'Transfer', icon: Truck, route: 'inventory' },
  { id: 'sold', label: 'Mark Sold', icon: ShoppingBag, route: 'inventory' },
  { id: 'sales', label: 'Sales', icon: ShoppingBag, route: 'sales' },
  { id: 'reports', label: 'Reports & Export', icon: FileSpreadsheet, route: 'reports', adminOnly: true },
  { id: 'tally', label: 'Run Tally Sync', icon: RefreshCw, tally: true, adminOnly: true },
];

export function DashboardQuickActions({ role, onTallySync, syncingTally }: DashboardQuickActionsProps): JSX.Element {
  const { setRoute } = useNavigationStore();
  const { open: openSearch } = useSearchStore();
  const isAdmin = role === 'main_admin' || role === 'admin';

  const visible = ACTIONS.filter((action) => !action.adminOnly || isAdmin);

  return (
    <div className="dash-quick-actions" role="toolbar" aria-label="Quick actions">
      {visible.map((action) => {
        const Icon = action.icon;
        return (
          <button
            key={action.id}
            type="button"
            className="dash-quick-action"
            disabled={action.tally && syncingTally}
            onClick={() => {
              if (action.search) {
                openSearch();
                return;
              }
              if (action.tally) {
                void onTallySync();
                return;
              }
              if (action.route) {
                setRoute(action.route);
              }
            }}
          >
            <Icon size={15} aria-hidden />
            <span>{action.tally && syncingTally ? 'Syncing…' : action.label}</span>
          </button>
        );
      })}
    </div>
  );
}
