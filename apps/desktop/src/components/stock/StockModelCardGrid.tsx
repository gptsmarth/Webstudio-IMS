import { useMemo } from 'react';
import type { ModelInventoryRow } from '../../lib/inventoryHierarchy';
import { StockModelCard } from './StockModelCard';

interface StockModelCardGridProps {
  rows: ModelInventoryRow[];
  loading?: boolean;
  showPrice?: boolean;
  onSelect: (modelId: string, label: string) => void;
  /** When true, only models with available units are shown (Stock tab). */
  availableOnly?: boolean;
}

export function StockModelCardGrid({
  rows,
  loading,
  showPrice = false,
  onSelect,
  availableOnly = false,
}: StockModelCardGridProps): JSX.Element {
  const visibleRows = useMemo(
    () => (availableOnly ? rows.filter((row) => row.availableUnits > 0) : rows),
    [availableOnly, rows],
  );

  if (loading) {
    return (
      <div className="stock-model-card-grid">
        {Array.from({ length: 6 }).map((_, index) => (
          <div
            key={index}
            className="skeleton stock-model-card stock-model-card--skeleton"
            aria-hidden
          />
        ))}
      </div>
    );
  }

  if (visibleRows.length === 0) {
    return (
      <div className="hierarchy-empty hierarchy-empty--panel">
        <p>No in-stock models for this brand match your search.</p>
      </div>
    );
  }

  return (
    <div className="stock-model-card-grid">
      {visibleRows.map((row) => (
        <StockModelCard
          key={row.model.id}
          row={row}
          showPrice={showPrice}
          onSelect={() =>
            onSelect(row.model.id, `${row.model.model_number} · ${row.model.model_name}`)
          }
        />
      ))}
    </div>
  );
}
