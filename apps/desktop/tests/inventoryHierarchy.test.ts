import { describe, expect, it } from 'vitest';
import { buildBrandSummaries, buildModelRows, matchesModelSearch } from '../src/lib/inventoryHierarchy';
import { findModelByNumber } from '../src/lib/productSpecLookup';
import type { Brand } from '../src/services/api/BrandService';
import type { ProductModel } from '../src/services/api/ProductModelService';

const brands: Brand[] = [{ id: 1, name: 'ASUS', short_name: null, logo_filename: null, display_order: 0, is_active: true }];
const models: ProductModel[] = [{
  id: 'm1',
  brand_id: 1,
  brand_name: 'ASUS',
  model_number: 'X151VA-AB5321WS',
  model_name: 'Vivobook 15',
  cpu: 'Intel i5',
  gpu: 'RTX 4060',
  ram_gb: 16,
  storage_value: '512',
  storage_unit: 'GB',
  storage_type: 'SSD',
  status: 'active',
  display: '15.6"',
  color_options: 'Black',
  product_image_url: null,
  search_aliases: null,
  notes: null,
}];

describe('inventory hierarchy', () => {
  it('matches partial model search terms', () => {
    expect(matchesModelSearch(models[0], null, 'vivobook')).toBe(true);
    expect(matchesModelSearch(models[0], null, '5321')).toBe(true);
    expect(matchesModelSearch(models[0], null, '4060')).toBe(true);
    expect(matchesModelSearch(models[0], null, 'macbook')).toBe(false);
  });

  it('finds model by number within brand', () => {
    expect(findModelByNumber(models, 'x151va-ab5321ws', 1)?.id).toBe('m1');
    expect(findModelByNumber(models, 'x151va-ab5321ws', 2)).toBeNull();
  });

  it('splits zero stock models', () => {
    const rows = buildModelRows(models, [{ id: 'm1', name: 'Vivobook', available: 0, sold: 2, total: 2 }], 1);
    expect(rows.zeroStock).toHaveLength(1);
    expect(rows.inStock).toHaveLength(0);
    expect(rows.all).toHaveLength(1);
  });

  it('includes catalog-only models in all rows', () => {
    const rows = buildModelRows(
      [...models, { ...models[0], id: 'm2', model_number: 'EMPTY-1', model_name: 'Empty' }],
      [{ id: 'm1', name: 'Vivobook', available: 2, sold: 0, total: 2 }],
      1,
    );
    expect(rows.all).toHaveLength(2);
    expect(rows.inStock).toHaveLength(1);
    expect(rows.zeroStock).toHaveLength(0);
  });
});
