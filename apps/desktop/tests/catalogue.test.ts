import { describe, expect, it } from 'vitest';
import {
  brandLogoSrc,
  canWriteCatalogue,
  catalogueStatusLabel,
  locationTypeLabel,
  matchesSearch,
  paginateItems,
} from '../src/lib/catalogue';
import { countModelsByBrand } from '../src/components/catalogue/BrandsTab';

describe('catalogue utilities', () => {
  it('checks write permissions', () => {
    expect(canWriteCatalogue(['brands:create', 'locations:edit'])).toBe(true);
    expect(canWriteCatalogue(['brands:view', 'locations:view'])).toBe(false);
  });

  it('paginates items', () => {
    const items = [1, 2, 3, 4, 5];
    expect(paginateItems(items, 1, 2)).toEqual([1, 2]);
    expect(paginateItems(items, 2, 2)).toEqual([3, 4]);
  });

  it('matches search text', () => {
    expect(matchesSearch('dell', ['Dell Technologies', 'Laptop'])).toBe(true);
    expect(matchesSearch('hp', ['Dell Technologies'])).toBe(false);
  });

  it('formats labels', () => {
    expect(catalogueStatusLabel(true)).toBe('Active');
    expect(locationTypeLabel('warehouse')).toBe('Warehouse');
  });

  it('resolves brand logo source', () => {
    expect(brandLogoSrc('Dell')).toContain('assets/brand-logos/');
    expect(brandLogoSrc('Dell', 'hp.svg')).toContain('assets/brand-logos/hp.svg');
    expect(brandLogoSrc('ASUS Laptops')).toContain('assets/brand-logos/asus.svg');
    expect(brandLogoSrc('Dell')).toMatch(/\.svg$/);
  });

  it('counts active models per brand only', () => {
    const map = countModelsByBrand([
      {
        id: '1',
        brand_id: 2,
        brand_name: 'Dell',
        model_number: 'X',
        model_name: 'XPS',
        cpu: '',
        gpu: null,
        ram_gb: 16,
        storage_value: '512',
        storage_unit: 'GB',
        storage_type: 'SSD',
        status: 'active',
        display: null,
        color_options: null,
        product_image_url: null,
        search_aliases: null,
        notes: null,
      },
      {
        id: '2',
        brand_id: 2,
        brand_name: 'Dell',
        model_number: 'Y',
        model_name: 'Inspiron',
        cpu: '',
        gpu: null,
        ram_gb: 8,
        storage_value: '256',
        storage_unit: 'GB',
        storage_type: 'SSD',
        status: 'archived',
        display: null,
        color_options: null,
        product_image_url: null,
        search_aliases: null,
        notes: null,
      },
    ]);
    expect(map.get(2)).toBe(1);
  });
});
