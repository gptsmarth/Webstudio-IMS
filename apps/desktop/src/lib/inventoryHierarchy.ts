import type { DistributionGroup } from '../services/api/DashboardService';
import type { InventoryItemDetail } from '../services/api/InventoryService';
import type { ProductModel } from '../services/api/ProductModelService';
import type { Brand } from '../services/api/BrandService';
import type { HierarchySearchField } from './hierarchySearch';
import type { ProductCategoryFilter } from './productCategory';
import { formatInventorySpecs } from './inventory';

export interface BrandInventorySummary {
  brandId: number;
  brandName: string;
  logoFilename: string | null;
  totalUnits: number;
  availableUnits: number;
  soldUnits: number;
  byLocation: Array<{ locationId: number; locationName: string; count: number }>;
}

export interface ModelInventoryRow {
  model: ProductModel;
  availableUnits: number;
  soldUnits: number;
  totalUnits: number;
  isZeroStock: boolean;
  specsLabel: string;
}

export function buildBrandSummaries(
  brands: Brand[],
  distributionByBrand: DistributionGroup[],
  items: InventoryItemDetail[],
): BrandInventorySummary[] {
  const distMap = new Map(distributionByBrand.map((row) => [row.id, row]));

  return brands
    .filter((brand) => brand.is_active)
    .map((brand) => {
      const dist = distMap.get(String(brand.id));
      const brandItems = items.filter((item) => item.brand_id === brand.id && !item.is_archived);
      const locationMap = new Map<
        number,
        { locationId: number; locationName: string; count: number }
      >();

      for (const item of brandItems.filter((entry) => entry.status !== 'sold')) {
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

      return {
        brandId: brand.id,
        brandName: brand.name,
        logoFilename: brand.logo_filename,
        totalUnits: dist?.total ?? brandItems.length,
        availableUnits:
          dist?.available ?? brandItems.filter((entry) => entry.status !== 'sold').length,
        soldUnits: dist?.sold ?? brandItems.filter((entry) => entry.status === 'sold').length,
        byLocation: [...locationMap.values()].sort((a, b) =>
          a.locationName.localeCompare(b.locationName),
        ),
      };
    })
    .sort((a, b) => a.brandName.localeCompare(b.brandName));
}

export function buildModelRows(
  models: ProductModel[],
  distributionByModel: DistributionGroup[],
  brandId: number,
): { all: ModelInventoryRow[]; inStock: ModelInventoryRow[]; zeroStock: ModelInventoryRow[] } {
  const distMap = new Map(distributionByModel.map((row) => [row.id, row]));
  const brandModels = models.filter(
    (model) => model.brand_id === brandId && model.status !== 'archived',
  );

  const rows: ModelInventoryRow[] = brandModels.map((model) => {
    const dist = distMap.get(model.id);
    const availableUnits = dist?.available ?? 0;
    const soldUnits = dist?.sold ?? 0;
    const totalUnits = dist?.total ?? availableUnits + soldUnits;
    return {
      model,
      availableUnits,
      soldUnits,
      totalUnits,
      isZeroStock: availableUnits === 0 && totalUnits > 0,
      specsLabel: formatInventorySpecs(model),
    };
  });

  rows.sort((a, b) => a.model.model_number.localeCompare(b.model.model_number));

  return {
    all: rows,
    inStock: rows.filter((row) => row.availableUnits > 0),
    zeroStock: rows.filter((row) => row.isZeroStock),
  };
}

export function matchesCategoryFilter(
  model: ProductModel,
  filter: ProductCategoryFilter,
): boolean {
  if (filter === 'all') return true;
  return (model.category ?? 'laptop') === filter;
}

export function matchesModelSearch(
  model: ProductModel,
  sampleItem: InventoryItemDetail | null,
  query: string,
  field: HierarchySearchField = 'all',
): boolean {
  const term = query.trim().toLowerCase();
  if (!term) return true;

  const fieldMap: Record<HierarchySearchField, string[]> = {
    all: [
      model.model_number,
      model.model_name,
      model.part_number ?? '',
      model.cpu ?? '',
      model.gpu ?? '',
      model.display ?? '',
      model.search_aliases ?? '',
      sampleItem?.serial_number ?? '',
    ],
    model_number: [model.model_number, model.part_number ?? ''],
    model_name: [model.model_name],
    gpu: [model.gpu ?? ''],
    cpu: [model.cpu ?? ''],
    display: [model.display ?? ''],
    serial: [sampleItem?.serial_number ?? ''],
  };

  return fieldMap[field].some((value) => value.toLowerCase().includes(term));
}
