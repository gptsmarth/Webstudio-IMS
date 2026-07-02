import { describe, expect, it } from 'vitest';
import { buildStockModelSpecLines, parseNotesSpecLines, pickStockCardHighlightSpecs, stockAvailabilityLabel } from '../src/lib/stockModelCard';
import type { ProductModel } from '../src/services/api/ProductModelService';

const baseModel: ProductModel = {
  id: '1',
  brand_id: 1,
  brand_name: 'ASUS',
  model_number: 'UX3407QA-QD259WS',
  model_name: 'ASUS Zenbook A14',
  cpu: 'Snapdragon X X1 26 100 Processor',
  gpu: 'Qualcomm Adreno',
  ram_gb: 16,
  storage_value: '512',
  storage_unit: 'GB',
  storage_type: 'SSD',
  status: 'active',
  display: '14" WUXGA OLED 60Hz',
  color_options: 'Ponder Blue, Jade Black',
  product_image_url: 'https://example.com/laptop.jpg',
  search_aliases: null,
  notes: [
    'Operating system: Windows 11 Home',
    'Battery: 75 Wh',
    'Weight: 1.2 kg',
    'Connectivity: Wi-Fi 7, Bluetooth 5.4, 2× USB-C',
    '---',
    'Matched official ASUS India listing',
  ].join('\n'),
};

describe('stockModelCard', () => {
  it('builds retailer-style spec lines with Gemini extras', () => {
    const lines = buildStockModelSpecLines(baseModel);
    expect(lines.map((l) => l.label)).toEqual([
      'Processor',
      'Graphics',
      'Memory',
      'Storage',
      'Display',
      'Colors',
      'Operating system',
      'Battery',
      'Weight',
      'Connectivity',
    ]);
    expect(lines[0].value).toContain('Snapdragon');
    expect(lines[3].value).toContain('512');
    expect(lines[4].value).toBe('14" WUXGA OLED 60Hz');
    expect(lines.find((l) => l.label === 'Operating system')?.value).toBe('Windows 11 Home');
  });

  it('parses structured notes before source separator', () => {
    const lines = parseNotesSpecLines(baseModel.notes);
    expect(lines).toHaveLength(4);
    expect(lines[0]).toEqual({ label: 'Operating system', value: 'Windows 11 Home' });
  });

  it('formats availability label', () => {
    expect(stockAvailabilityLabel(1)).toBe('1 unit available');
    expect(stockAvailabilityLabel(5)).toBe('5 units available');
  });

  it('picks highlight specs for retailer cards', () => {
    const lines = buildStockModelSpecLines(baseModel);
    const highlights = pickStockCardHighlightSpecs(lines);
    expect(highlights.map((line) => line.label)).toEqual(['Processor', 'Memory', 'Storage', 'Display']);
  });
});
