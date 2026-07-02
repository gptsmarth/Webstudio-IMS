import { P } from '../../services/PermissionService';
import { AuditService } from '../api/AuditService';
import { BrandService } from '../api/BrandService';
import { InventoryService } from '../api/InventoryService';
import { LocationService } from '../api/LocationService';
import { NotificationService } from '../api/NotificationService';
import { ProductModelService } from '../api/ProductModelService';
import { SalesService } from '../api/SalesService';

const PROVIDER_PERMISSIONS: Record<string, string> = {
  inventory: P.inventory.view,
  sales: P.sales.view,
  brands: P.brands.view,
  models: P.productModels.view,
  locations: P.locations.view,
  notifications: P.notifications.view,
  audit: P.audit.view,
};

export type SearchEntityType =
  | 'serial'
  | 'brand'
  | 'product_model'
  | 'location'
  | 'invoice'
  | 'customer'
  | 'notification'
  | 'audit';

export interface SearchResult {
  id: string;
  type: SearchEntityType;
  title: string;
  subtitle?: string;
  inventoryId?: string;
  group: string;
}

export interface SearchProvider {
  id: string;
  label: string;
  entityType: SearchEntityType;
  search: (query: string) => Promise<SearchResult[]> | SearchResult[];
}

async function searchInventory(query: string, limit = 6): Promise<SearchResult[]> {
  const result = await InventoryService.listItems({ search: query, page_size: limit });
  return result.items.map((item) => ({
    id: `inv-${item.id}`,
    type: 'serial',
    group: 'Inventory',
    title: item.serial_number,
    subtitle: `${item.brand_name} · ${item.model_name} · ${item.current_location_name}`,
    inventoryId: item.id,
  }));
}

async function searchSales(query: string, limit = 5): Promise<SearchResult[]> {
  const result = await SalesService.listSales({ search: query, page_size: limit });
  return result.items.map((sale) => ({
    id: `sale-${sale.id}`,
    type: 'invoice',
    group: 'Sales',
    title: sale.invoice_number,
    subtitle: `${sale.customer_name ?? 'Customer'} · ${sale.serial_number}`,
    inventoryId: sale.inventory_item_id ?? undefined,
  }));
}

async function searchBrands(query: string): Promise<SearchResult[]> {
  const brands = await BrandService.listBrands();
  const term = query.toLowerCase();
  return brands
    .filter((brand) => brand.name.toLowerCase().includes(term))
    .slice(0, 5)
    .map((brand) => ({
      id: `brand-${brand.id}`,
      type: 'brand',
      group: 'Brands',
      title: brand.name,
      subtitle: 'Brand',
    }));
}

async function searchProductModels(query: string): Promise<SearchResult[]> {
  const models = await ProductModelService.listModels();
  const term = query.toLowerCase();
  return models
    .filter((model) =>
      model.model_number.toLowerCase().includes(term)
      || model.model_name.toLowerCase().includes(term)
      || (model.brand_name ?? '').toLowerCase().includes(term),
    )
    .slice(0, 5)
    .map((model) => ({
      id: `model-${model.id}`,
      type: 'product_model',
      group: 'Product Models',
      title: `${model.model_number} — ${model.model_name}`,
      subtitle: model.brand_name ?? 'Product model',
    }));
}

async function searchLocations(query: string): Promise<SearchResult[]> {
  const locations = await LocationService.listLocations();
  const term = query.toLowerCase();
  return locations
    .filter((location) => location.name.toLowerCase().includes(term))
    .slice(0, 5)
    .map((location) => ({
      id: `location-${location.id}`,
      type: 'location',
      group: 'Locations',
      title: location.name,
      subtitle: 'Location',
    }));
}

async function searchNotifications(query: string): Promise<SearchResult[]> {
  const result = await NotificationService.listNotifications({ page_size: 20 });
  const term = query.toLowerCase();
  return result.items
    .filter((item) => [item.title, item.description, item.serial_number ?? ''].some((f) => f.toLowerCase().includes(term)))
    .slice(0, 5)
    .map((item) => ({
      id: `notif-${item.id}`,
      type: 'notification',
      group: 'Notifications',
      title: item.title,
      subtitle: item.notification_type.replaceAll('_', ' '),
    }));
}

async function searchAudit(query: string): Promise<SearchResult[]> {
  const result = await AuditService.listLogs({ page_size: 20 });
  const term = query.toLowerCase();
  return result.items
    .filter((item) => [item.description ?? '', item.action, item.actor_display_name ?? ''].some((f) => f.toLowerCase().includes(term)))
    .slice(0, 5)
    .map((item) => ({
      id: `audit-${item.id}`,
      type: 'audit',
      group: 'Audit Logs',
      title: item.action.replaceAll('_', ' '),
      subtitle: item.description ?? item.actor_display_name ?? 'Audit entry',
    }));
}

export const SEARCH_PROVIDERS: SearchProvider[] = [
  { id: 'inventory', label: 'Inventory', entityType: 'serial', search: searchInventory },
  { id: 'sales', label: 'Sales', entityType: 'invoice', search: searchSales },
  { id: 'brands', label: 'Brands', entityType: 'brand', search: searchBrands },
  { id: 'models', label: 'Product Models', entityType: 'product_model', search: searchProductModels },
  { id: 'locations', label: 'Locations', entityType: 'location', search: searchLocations },
  { id: 'notifications', label: 'Notifications', entityType: 'notification', search: searchNotifications },
  { id: 'audit', label: 'Audit Logs', entityType: 'audit', search: searchAudit },
];

export interface GroupedSearchResults {
  group: string;
  items: SearchResult[];
}

export async function runGlobalSearch(query: string, permissions?: string[]): Promise<SearchResult[]> {
  const trimmed = query.trim();
  if (!trimmed) return [];

  const granted = new Set(permissions ?? []);
  const providers = SEARCH_PROVIDERS.filter((provider) => {
    const required = PROVIDER_PERMISSIONS[provider.id];
    return required ? granted.has(required) : true;
  });

  try {
    const batches = await Promise.all(providers.map((provider) => Promise.resolve(provider.search(trimmed))));
    return batches.flat().slice(0, 24);
  } catch {
    return [];
  }
}

export function groupSearchResults(results: SearchResult[]): GroupedSearchResults[] {
  const map = new Map<string, SearchResult[]>();
  for (const result of results) {
    const list = map.get(result.group) ?? [];
    list.push(result);
    map.set(result.group, list);
  }
  return [...map.entries()].map(([group, items]) => ({ group, items }));
}

const RECENT_KEY = 'webstudio.search.recent';
const RECENT_LIMIT = 8;

export function loadRecentSearches(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as string[];
  } catch {
    return [];
  }
}

export function saveRecentSearch(query: string): void {
  const trimmed = query.trim();
  if (!trimmed) return;
  const recent = loadRecentSearches().filter((entry) => entry.toLowerCase() !== trimmed.toLowerCase());
  recent.unshift(trimmed);
  localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, RECENT_LIMIT)));
}
