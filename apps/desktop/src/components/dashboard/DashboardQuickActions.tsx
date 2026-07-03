import { FileSpreadsheet, PackagePlus, RefreshCw, Search, ShoppingBag, Truck } from 'lucide-react';
import type { WorkspaceRoute } from '../../config/navigation';
import { P } from '../../services/PermissionService';
import { useNavigationStore, useSearchStore } from '../../store';

interface DashboardQuickActionsProps {
  permissions: string[];
  onTallySync: () => void;
  syncingTally: boolean;
}

const ACTIONS: {
  id: string;
  label: string;
  icon: typeof Search;
  route?: WorkspaceRoute;
  search?: boolean;
  permission?: string;
  tally?: boolean;
}[] = [
  {
    id: 'add',
    label: 'Add Laptop',
    icon: PackagePlus,
    route: 'inventory',
    permission: P.inventory.create,
  },
  { id: 'search', label: 'Search', icon: Search, search: true },
  {
    id: 'transfer',
    label: 'Transfer',
    icon: Truck,
    route: 'inventory',
    permission: P.inventory.transfer,
  },
  {
    id: 'sold',
    label: 'Mark Sold',
    icon: ShoppingBag,
    route: 'inventory',
    permission: P.sales.create,
  },
  { id: 'sales', label: 'Sales', icon: ShoppingBag, route: 'sales', permission: P.sales.view },
  {
    id: 'reports',
    label: 'Reports & Export',
    icon: FileSpreadsheet,
    route: 'reports',
    permission: P.reports.view,
  },
  {
    id: 'tally',
    label: 'Run Tally Sync',
    icon: RefreshCw,
    tally: true,
    permission: P.tally.runSync,
  },
];

export function DashboardQuickActions({
  permissions,
  onTallySync,
  syncingTally,
}: DashboardQuickActionsProps): JSX.Element {
  const { setRoute } = useNavigationStore();
  const { open: openSearch } = useSearchStore();
  const granted = new Set(permissions);

  const visible = ACTIONS.filter((action) => !action.permission || granted.has(action.permission));

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
