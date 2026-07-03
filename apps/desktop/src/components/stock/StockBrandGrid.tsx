import { ChevronRight, Package } from 'lucide-react';
import { brandLogoSrc } from '../../lib/catalogue';
import type { BrandInventorySummary } from '../../lib/inventoryHierarchy';
import { InventoryBrandCell } from '../inventory/InventoryBrandCell';

interface StockBrandGridProps {
  summaries: BrandInventorySummary[];
  loading?: boolean;
  onSelect: (brandId: number, brandName: string) => void;
  /** Compact square tiles for Stock; detailed cards for Inventory admin. */
  variant?: 'compact' | 'detailed';
  showSoldUnits?: boolean;
}

export function StockBrandGrid({
  summaries,
  loading,
  onSelect,
  variant = 'compact',
  showSoldUnits = false,
}: StockBrandGridProps): JSX.Element {
  if (loading) {
    if (variant === 'detailed') {
      return (
        <div className="hierarchy-grid hierarchy-grid--brands">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="skeleton hierarchy-card hierarchy-card--brand" />
          ))}
        </div>
      );
    }
    return (
      <div className="stock-brand-grid">
        {Array.from({ length: 12 }).map((_, index) => (
          <div key={index} className="skeleton stock-brand-tile" aria-hidden />
        ))}
      </div>
    );
  }

  if (summaries.length === 0) {
    return (
      <div className="hierarchy-empty">
        <Package size={24} aria-hidden />
        <p>No brands in catalogue yet. Add brands from Catalogue.</p>
      </div>
    );
  }

  if (variant === 'detailed') {
    return (
      <div className="hierarchy-grid hierarchy-grid--brands">
        {summaries.map((summary) => (
          <button
            key={summary.brandId}
            type="button"
            className="hierarchy-card hierarchy-card--brand"
            onClick={() => onSelect(summary.brandId, summary.brandName)}
          >
            <div className="hierarchy-card__head">
              <InventoryBrandCell brandName={summary.brandName} />
              <ChevronRight size={16} aria-hidden className="hierarchy-card__chevron" />
            </div>
            <dl className="hierarchy-card__stats">
              <div>
                <dt>Available</dt>
                <dd>{summary.availableUnits}</dd>
              </div>
              <div>
                <dt>Total</dt>
                <dd>{summary.totalUnits}</dd>
              </div>
              {showSoldUnits && (
                <div>
                  <dt>Sold</dt>
                  <dd>{summary.soldUnits}</dd>
                </div>
              )}
            </dl>
            {summary.byLocation.length > 0 && (
              <ul className="hierarchy-card__locations">
                {summary.byLocation.slice(0, 3).map((row) => (
                  <li key={row.locationId}>
                    <span>{row.locationName}</span>
                    <span>{row.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="stock-brand-grid">
      {summaries.map((summary) => {
        const logoSrc = brandLogoSrc(summary.brandName, summary.logoFilename);
        return (
          <button
            key={summary.brandId}
            type="button"
            className="stock-brand-tile"
            onClick={() => onSelect(summary.brandId, summary.brandName)}
            aria-label={`Browse ${summary.brandName} models`}
          >
            <span className="stock-brand-tile__logo-wrap">
              <img src={logoSrc} alt="" className="stock-brand-tile__logo" loading="lazy" />
            </span>
            <span className="stock-brand-tile__name">{summary.brandName}</span>
          </button>
        );
      })}
    </div>
  );
}
