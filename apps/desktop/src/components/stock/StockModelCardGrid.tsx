import { forwardRef, useMemo, type ReactNode } from 'react';
import type { ModelInventoryRow } from '../../lib/inventoryHierarchy';
import { StockModelCard } from './StockModelCard';

interface StockModelCardGridProps {
  rows: ModelInventoryRow[];
  loading?: boolean;
  showPrice?: boolean;
  showLivePrice?: boolean;
  onSelect: (modelId: string, label: string) => void;
  /** When true, only models with available units are shown (Stock tab). */
  availableOnly?: boolean;
}

export const StockModelCardGrid = forwardRef<HTMLDivElement, StockModelCardGridProps>(
  function StockModelCardGrid(
    { rows, loading, showPrice = false, showLivePrice = false, onSelect, availableOnly = false },
    ref,
  ) {
    const visibleRows = useMemo(
      () => (availableOnly ? rows.filter((row) => row.availableUnits > 0) : rows),
      [availableOnly, rows],
    );

    // Always render the same ref-bearing wrapper regardless of loading/empty/content
    // state — swapping between separate <div ref={ref}> elements per branch would
    // mount a brand-new DOM node (scrollTop reset to 0) every time the state changes,
    // silently undoing whatever scroll position was just restored.
    let body: ReactNode;
    if (loading) {
      body = Array.from({ length: 6 }).map((_, index) => (
        <div
          key={index}
          className="skeleton stock-model-card stock-model-card--skeleton"
          aria-hidden
        />
      ));
    } else if (visibleRows.length === 0) {
      body = (
        <div className="hierarchy-empty hierarchy-empty--panel" style={{ gridColumn: '1 / -1' }}>
          <p>No in-stock models for this brand match your search.</p>
        </div>
      );
    } else {
      body = visibleRows.map((row) => (
        <StockModelCard
          key={row.model.id}
          row={row}
          showPrice={showPrice}
          showLivePrice={showLivePrice}
          onSelect={() =>
            onSelect(row.model.id, `${row.model.model_number} · ${row.model.model_name}`)
          }
        />
      ));
    }

    return (
      <div ref={ref} className="stock-model-card-grid">
        {body}
      </div>
    );
  },
);
