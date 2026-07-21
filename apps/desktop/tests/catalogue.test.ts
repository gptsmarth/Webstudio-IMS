import { describe, expect, it } from 'vitest';
import {
  brandLogoSrc,
  canWriteCatalogue,
  catalogueStatusLabel,
  extractCatalogueModelNumber,
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

  it('extracts catalogue model number from marketing names', () => {
    expect(extractCatalogueModelNumber('Vivobook Go 14 OLED UX3405CA-QL1014WS')).toBe(
      'UX3405CA-QL1014WS',
    );
    expect(extractCatalogueModelNumber('ASUS F1504FA-BQ2113WS')).toBe('F1504FA-BQ2113WS');
    expect(extractCatalogueModelNumber('Epson L3350')).toBe('Epson L3350');
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
