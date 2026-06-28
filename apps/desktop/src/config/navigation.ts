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
  roles: UserRole[];
  description: string;
}

export const NAV_ITEMS: NavItemConfig[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    group: 'operations',
    roles: ['main_admin', 'admin'],
    description: 'What is happening in inventory today.',
  },
  {
    id: 'stock',
    label: 'Stock',
    icon: Boxes,
    group: 'operations',
    roles: ['main_admin', 'admin', 'salesperson'],
    description: 'Browse available laptops by brand and model for customer assistance.',
  },
  {
    id: 'inventory',
    label: 'Inventory',
    icon: Package,
    group: 'operations',
    roles: ['main_admin', 'admin'],
    description: 'Receive, transfer, and manage serial-tracked inventory by brand and model.',
  },
  {
    id: 'sales',
    label: 'Sales',
    icon: ShoppingBag,
    group: 'operations',
    roles: ['main_admin', 'admin'],
    description: 'Completed sales, invoices, and customer records.',
  },
  {
    id: 'catalogue',
    label: 'Catalogue',
    icon: Layers,
    group: 'operations',
    roles: ['main_admin', 'admin'],
    description: 'Brands and store locations.',
  },
  {
    id: 'notifications',
    label: 'Notifications',
    icon: Bell,
    group: 'operations',
    roles: ['main_admin', 'admin'],
    description: 'Inventory alerts, Tally sync notifications, and system messages.',
  },
  {
    id: 'reports',
    label: 'Report Center',
    icon: FileSpreadsheet,
    group: 'administration',
    roles: ['main_admin', 'admin'],
    description: 'Inventory, sales, audit exports and report previews.',
  },
  {
    id: 'users',
    label: 'Users',
    icon: Users,
    group: 'administration',
    roles: ['main_admin'],
    description: 'User accounts, roles, and access management.',
  },
  {
    id: 'audit',
    label: 'Audit Center',
    icon: ScrollText,
    group: 'administration',
    roles: ['main_admin'],
    description: 'Immutable history of business and system events with timeline and exports.',
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: Settings,
    group: 'system',
    roles: ['main_admin'],
    description: 'System configuration and integration preferences.',
  },
];

export const NAV_GROUPS: { id: NavItemConfig['group']; label: string }[] = [
  { id: 'operations', label: 'Operations' },
  { id: 'administration', label: 'Administration' },
  { id: 'system', label: 'System' },
];

export function navItemsForRole(role: UserRole): NavItemConfig[] {
  return NAV_ITEMS.filter((item) => item.roles.includes(role));
}

export function defaultRouteForRole(role: UserRole): WorkspaceRoute {
  return role === 'salesperson' ? 'stock' : 'dashboard';
}

export function isRouteAllowedForRole(route: WorkspaceRoute, role: UserRole): boolean {
  const item = navItemByRoute(route);
  if (!item) return false;
  return item.roles.includes(role);
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
