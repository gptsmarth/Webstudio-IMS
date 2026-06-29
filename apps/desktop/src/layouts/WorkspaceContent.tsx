import { useEffect } from 'react';
import { defaultRouteForPermissions, isRouteAllowedForPermissions, type WorkspaceRoute } from '../config/navigation';
import { useAuthStore, useNavigationStore } from '../store';
import {
  AuditPage,
  CataloguePage,
  DashboardPage,
  InventoryPage,
  NotificationsPage,
  ReportsPage,
  SalesPage,
  SettingsPage,
  StockPage,
  UsersPage,
} from '../pages/workspace';

const ROUTE_COMPONENTS: Record<WorkspaceRoute, () => JSX.Element> = {
  dashboard: DashboardPage,
  stock: StockPage,
  inventory: InventoryPage,
  sales: SalesPage,
  catalogue: CataloguePage,
  users: UsersPage,
  audit: AuditPage,
  notifications: NotificationsPage,
  reports: ReportsPage,
  settings: SettingsPage,
};

export function WorkspaceContent(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const currentRoute = useNavigationStore((state) => state.currentRoute);
  const setRoute = useNavigationStore((state) => state.setRoute);

  useEffect(() => {
    if (!session) return;
    if (!isRouteAllowedForPermissions(currentRoute, session.permissions)) {
      setRoute(defaultRouteForPermissions(session.permissions));
    }
  }, [currentRoute, session, setRoute]);

  const permissions = session?.permissions ?? [];
  const safeRoute: WorkspaceRoute = isRouteAllowedForPermissions(currentRoute, permissions)
    ? currentRoute
    : defaultRouteForPermissions(permissions);
  const PageComponent = ROUTE_COMPONENTS[safeRoute] ?? StockPage;

  return <PageComponent key={safeRoute} />;
}

/** Keyboard shortcut: Cmd/Ctrl + K opens global search */
export function useGlobalSearchShortcut(open: () => void): void {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        open();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open]);
}
