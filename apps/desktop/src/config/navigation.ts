import type { LucideIcon } from 'lucide-react';
import {
  LayoutDashboard,
  Package,
  ShoppingBag,
  Layers,
  Users,
  ScrollText,
  Bell,
  FileSpreadsheet,
  Settings,
  Boxes,
} from 'lucide-react';
import { ROUTE_PERMISSIONS } from '../services/PermissionService';

export type UserRole = 'main_admin' | 'admin' | 'salesperson';

export type WorkspaceRoute =
  | 'dashboard'
  | 'stock'
  | 'inventory'
  | 'sales'
  | 'catalogue'
  | 'notifications'
  | 'reports'
  | 'users'
  | 'audit'
  | 'settings';

export interface NavItemConfig {
  id: WorkspaceRoute;
  label: string;
  icon: LucideIcon;
  group: 'operations' | 'administration' | 'system';
  /** Minimum permission required to see this route. */
  permission: string;
  description: string;
}

export const NAV_ITEMS: NavItemConfig[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    group: 'operations',
    permission: ROUTE_PERMISSIONS.dashboard,
    description: 'What is happening in inventory today.',
  },
  {
    id: 'stock',
    label: 'Stock',
    icon: Boxes,
    group: 'operations',
    permission: ROUTE_PERMISSIONS.stock,
    description: 'Browse available laptops by brand and model for customer assistance.',
  },
  {
    id: 'inventory',
    label: 'Inventory',
    icon: Package,
    group: 'operations',
    permission: ROUTE_PERMISSIONS.inventory,
    description: 'Receive, transfer, and manage serial-tracked inventory by brand and model.',
  },
  {
    id: 'sales',
    label: 'Sales',
    icon: ShoppingBag,
    group: 'operations',
    permission: ROUTE_PERMISSIONS.sales,
    description: 'Completed sales, invoices, and customer records.',
  },
  {
    id: 'catalogue',
    label: 'Catalogue',
    icon: Layers,
    group: 'operations',
    permission: ROUTE_PERMISSIONS.catalogue,
    description: 'Brands and store locations.',
  },
  {
    id: 'notifications',
    label: 'Notifications',
    icon: Bell,
    group: 'operations',
    permission: ROUTE_PERMISSIONS.notifications,
    description: 'Inventory alerts, Tally sync notifications, and system messages.',
  },
  {
    id: 'reports',
    label: 'Report Center',
    icon: FileSpreadsheet,
    group: 'administration',
    permission: ROUTE_PERMISSIONS.reports,
    description: 'Inventory, sales, audit exports and report previews.',
  },
  {
    id: 'users',
    label: 'Users',
    icon: Users,
    group: 'administration',
    permission: ROUTE_PERMISSIONS.users,
    description: 'User accounts, roles, and access management.',
  },
  {
    id: 'audit',
    label: 'Audit Center',
    icon: ScrollText,
    group: 'administration',
    permission: ROUTE_PERMISSIONS.audit,
    description: 'Immutable history of business and system events with timeline and exports.',
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: Settings,
    group: 'system',
    permission: ROUTE_PERMISSIONS.settings,
    description: 'System configuration and integration preferences.',
  },
];

export const NAV_GROUPS: { id: NavItemConfig['group']; label: string }[] = [
  { id: 'operations', label: 'Operations' },
  { id: 'administration', label: 'Administration' },
  { id: 'system', label: 'System' },
];

export function navItemsForPermissions(permissions: string[]): NavItemConfig[] {
  const granted = new Set(permissions);
  return NAV_ITEMS.filter((item) => granted.has(item.permission));
}

/** @deprecated Use navItemsForPermissions — kept for tests migrating to permission model. */
export function navItemsForRole(role: UserRole): NavItemConfig[] {
  const rolePermissions: Record<UserRole, string[]> = {
    main_admin: NAV_ITEMS.map((item) => item.permission),
    admin: NAV_ITEMS.filter((item) => item.id !== 'users' && item.id !== 'audit' && item.id !== 'settings').map((item) => item.permission),
    salesperson: [ROUTE_PERMISSIONS.stock],
  };
  return navItemsForPermissions(rolePermissions[role] ?? []);
}

export function defaultRouteForPermissions(permissions: string[]): WorkspaceRoute {
  const items = navItemsForPermissions(permissions);
  const preferred: WorkspaceRoute[] = ['dashboard', 'stock', 'inventory', 'sales'];
  for (const route of preferred) {
    if (items.some((item) => item.id === route)) {
      return route;
    }
  }
  return items[0]?.id ?? 'stock';
}

export function defaultRouteForRole(role: UserRole): WorkspaceRoute {
  return defaultRouteForPermissions(
    navItemsForRole(role).map((item) => item.permission),
  );
}

export function isRouteAllowedForPermissions(route: WorkspaceRoute, permissions: string[]): boolean {
  const required = ROUTE_PERMISSIONS[route];
  return required ? new Set(permissions).has(required) : false;
}

export function isRouteAllowedForRole(route: WorkspaceRoute, role: UserRole): boolean {
  return navItemsForRole(role).some((item) => item.id === route);
}

export function navItemByRoute(route: WorkspaceRoute): NavItemConfig | undefined {
  return NAV_ITEMS.find((item) => item.id === route);
}

export function breadcrumbTrail(route: WorkspaceRoute): { label: string; route?: WorkspaceRoute }[] {
  const current = navItemByRoute(route);
  return [
    { label: 'WEBSTUDIO IMS' },
    { label: current?.label ?? 'Page', route },
  ];
}
