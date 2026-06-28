import type { InventoryItemDetail } from '../services/api/InventoryService';
import { InventoryService } from '../services/api/InventoryService';

export interface LocationUnitCount {
  locationId: number;
  locationName: string;
  count: number;
}

export interface ProductModelUnitSummary {
  totalUnits: number;
  availableUnits: number;
  soldUnits: number;
  byLocation: LocationUnitCount[];
}

export function summarizeProductModelUnits(items: InventoryItemDetail[]): ProductModelUnitSummary {
  const active = items.filter((item) => !item.is_archived);
  const soldUnits = active.filter((item) => item.status === 'sold').length;
  const availableUnits = active.filter((item) =>
    item.status === 'available' || item.status === 'received' || item.status === 'reserved',
  ).length;

  const locationMap = new Map<number, LocationUnitCount>();
  for (const item of active.filter((entry) => entry.status !== 'sold')) {
    const existing = locationMap.get(item.current_location_id);
    if (existing) {
      existing.count += 1;
    } else {
      locationMap.set(item.current_location_id, {
        locationId: item.current_location_id,
        locationName: item.current_location_name,
        count: 1,
      });
    }
  }

  const byLocation = [...locationMap.values()].sort((a, b) =>
    a.locationName.localeCompare(b.locationName),
  );

  return {
    totalUnits: active.length,
    availableUnits,
    soldUnits,
    byLocation,
  };
}

export async function fetchAllInventoryForModel(productModelId: string): Promise<InventoryItemDetail[]> {
  const items: InventoryItemDetail[] = [];
  let page = 1;
  let totalPages = 1;

  while (page <= totalPages) {
    const result = await InventoryService.listItems({
      product_model_id: productModelId,
      include_archived: true,
      page_size: 100,
      page,
    });
    items.push(...result.items);
    totalPages = result.total_pages;
    page += 1;
  }

  return items;
}
