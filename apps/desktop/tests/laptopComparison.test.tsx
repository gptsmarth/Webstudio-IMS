import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { ComparisonTable } from '../src/components/comparison/ComparisonTable';
import { navItemsForPermissions } from '../src/config/navigation';
import {
  addComparisonSlot,
  comparisonRows,
  initialComparisonSlots,
  removeComparisonSlot,
  setComparisonLaptop,
} from '../src/lib/laptopComparison';
import type { ComparisonLaptop } from '../src/services/api/ComparisonService';

const savedRam =
  '16 GB DDR5 4800 MHz, dual channel, two replaceable modules. Maximum supported capacity 64 GB.';
const processor =
  'Intel Core i5-1335U, 10 cores, 12 threads, 12 MB Intel Smart Cache, up to 4.60 GHz';

function fixture(source: 'inventory' | 'external'): ComparisonLaptop {
  return {
    source,
    brand: source === 'inventory' ? 'ASUS' : 'Lenovo',
    model_number: source === 'inventory' ? 'X1504VAP-IN011WS' : '21M7ABCD',
    model_name: null,
    model_id: source === 'inventory' ? 'internal-guid' : null,
    image_url: null,
    managed_image: false,
    available_units: source === 'inventory' ? 2 : null,
    selling_price: source === 'inventory' ? '66999.22' : null,
    saved_notes:
      source === 'inventory'
        ? 'Memory type: ' +
          savedRam +
          '\nCPU cache: 12 MB\nWarranty: 2 years\nAmbient light sensor: Factory fitted\nPrivate staff aside\n---\nSource note'
        : null,
    specifications: [
      {
        component: 'Processor',
        detail: source === 'inventory' ? 'Intel Core i5-1335U' : processor,
      },
    ],
  };
}

describe('laptop comparison', () => {
  it('starts with two columns and lets inventory staff see the tab', () => {
    const slots = initialComparisonSlots();
    expect(slots).toHaveLength(2);
    expect(slots.every((slot) => slot.laptop === null)).toBe(true);
    expect(navItemsForPermissions(['inventory:view']).map(({ id }) => id)).toContain('comparison');
    expect(navItemsForPermissions([]).map(({ id }) => id)).not.toContain('comparison');
    const html = renderToStaticMarkup(<ComparisonTable slots={slots} onSelect={() => undefined} />);
    expect(html.match(/From Inventory/g)).toHaveLength(2);
    expect(html.match(/Outside Inventory/g)).toHaveLength(2);
    expect(html).not.toContain('Remove laptop');
  });

  it('adds or removes optional columns while keeping other models', () => {
    const model = fixture('inventory');
    let slots = initialComparisonSlots();
    slots = setComparisonLaptop(slots, 1, model);
    slots = addComparisonSlot(slots, 3);
    slots = addComparisonSlot(slots, 4);
    slots = setComparisonLaptop(slots, 4, fixture('external'));
    expect(addComparisonSlot(slots, 5)).toBe(slots);
    const fourColumns = renderToStaticMarkup(<ComparisonTable slots={slots} />);
    expect(fourColumns).toContain('Remove laptop 3');
    expect(fourColumns).toContain('Remove laptop 4');
    slots = removeComparisonSlot(slots, 3);
    expect(slots).toHaveLength(3);
    expect(slots[0].laptop).toBe(model);
    expect(slots[2].laptop?.source).toBe('external');
    expect(renderToStaticMarkup(<ComparisonTable slots={slots} />)).toContain('Remove laptop 3');
    slots = removeComparisonSlot(slots, 4);
    expect(removeComparisonSlot(slots, 2)).toBe(slots);
  });

  it('groups complete saved and researched values and marks unavailable data', () => {
    let slots = setComparisonLaptop(initialComparisonSlots(), 1, fixture('inventory'));
    slots = setComparisonLaptop(slots, 2, fixture('external'));
    const rows = comparisonRows(slots);
    const cpu = rows.find((row) => row.heading === 'Processor');
    expect(cpu?.values[0]).toEqual(['Intel Core i5-1335U', 'CPU cache: 12 MB']);
    expect(cpu?.values[1]).toEqual([processor]);
    expect(cpu?.differs).toBe(true);
    expect(rows.find((row) => row.heading === 'RAM')?.values).toEqual([
      ['Memory type: ' + savedRam],
      [],
    ]);
    expect(rows.find((row) => row.heading === 'Display')?.differs).toBe(false);
    expect(rows.some((row) => row.heading === 'Ambient light sensor')).toBe(true);
    expect(rows.some((row) => row.heading === 'CPU cache')).toBe(false);

    const html = renderToStaticMarkup(
      <ComparisonTable slots={slots} customer showSellingPrice={false} />,
    );
    expect(html).toContain(savedRam);
    expect(html).toContain(processor);
    expect(html).toContain('Not available');
    expect(html).toContain('External Research');
    expect(html).toContain('In Stock');
    expect(html).toContain('Photo unavailable');
    expect(html).toContain('data-different="true"');
    expect(html).not.toContain('internal-guid');
    expect(html).not.toContain('From Inventory');
    expect(html).not.toContain('Remove laptop');
    expect(html).not.toContain('66,999');
    expect(html).not.toContain('Source note');
    expect(html).not.toContain('Private staff aside');
    const specs = comparisonRows(slots, true);
    expect(specs.some((row) => row.heading === 'Operating system and warranty')).toBe(true);
  });
});
