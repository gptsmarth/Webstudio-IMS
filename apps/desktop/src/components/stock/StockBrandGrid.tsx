import { forwardRef } from 'react';
import { ChevronRight, Package } from 'lucide-react';
import type { BrandInventorySummary } from '../../lib/inventoryHierarchy';
import { BrandLogoImage } from '../branding/BrandLogoImage';
import { InventoryBrandCell } from '../inventory/InventoryBrandCell';

interface StockBrandGridProps {
  summaries: BrandInventorySummary[];
  loading?: boolean;
  onSelect: (brandId: number, brandName: string) => void;
  /** Compact square tiles for Stock; detailed cards for Inventory admin. */
  variant?: 'compact' | 'detailed';
  showSoldUnits?: boolean;
}

export const StockBrandGrid = forwardRef<HTMLDivElement, StockBrandGridProps>(
  function StockBrandGrid(
    { summaries, loading, onSelect, variant = 'compact', showSoldUnits = false },
    ref,
  ) {
    if (loading) {
      if (variant === 'detailed') {
        return (
          <div ref={ref} className="hierarchy-grid hierarchy-grid--brands">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="skeleton hierarchy-card hierarchy-card--brand" />
            ))}
          </div>
        );
      }
      return (
        <div ref={ref} className="stock-brand-grid">
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
        <div ref={ref} className="hierarchy-grid hierarchy-grid--brands">
          {summaries.map((summary) => (
            <button
              key={summary.brandId}
              type="button"
              className="hierarchy-card hierarchy-card--brand"
              onClick={() => onSelect(summary.brandId, summary.brandName)}
            >
              <div className="hierarchy-card__head">
                <InventoryBrandCell
                  brandName={summary.brandName}
                  logoFilename={summary.logoFilename}
                />
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
                <div>
                  <dt>Laptops</dt>
                  <dd>{summary.laptopUnits}</dd>
                </div>
                <div>
                  <dt>Accessories</dt>
                  <dd>{summary.accessoryUnits}</dd>
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
      <div ref={ref} className="stock-brand-grid">
        {summaries.map((summary) => (
          <button
            key={summary.brandId}
            type="button"
            className="stock-brand-tile"
            onClick={() => onSelect(summary.brandId, summary.brandName)}
            aria-label={`Browse ${summary.brandName} models`}
          >
            <span className="stock-brand-tile__logo-wrap">
              <BrandLogoImage
                brand={summary.brandName}
                logoFilename={summary.logoFilename}
                className="stock-brand-tile__logo"
              />
            </span>
            <span className="stock-brand-tile__name">{summary.brandName}</span>
          </button>
        ))}
      </div>
    );
  },
);
