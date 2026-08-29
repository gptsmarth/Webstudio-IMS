import { forwardRef, type ReactNode } from 'react';
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
    const isDetailed = variant === 'detailed';
    const gridClassName = isDetailed ? 'hierarchy-grid hierarchy-grid--brands' : 'stock-brand-grid';

    // Always render the same ref-bearing wrapper regardless of loading/empty/content
    // state — swapping between separate <div ref={ref}> elements per branch would
    // mount a brand-new DOM node (scrollTop reset to 0) every time the state changes,
    // silently undoing whatever scroll position was just restored.
    let body: ReactNode;
    if (loading) {
      body = isDetailed
        ? Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="skeleton hierarchy-card hierarchy-card--brand" />
          ))
        : Array.from({ length: 12 }).map((_, index) => (
            <div key={index} className="skeleton stock-brand-tile" aria-hidden />
          ));
    } else if (summaries.length === 0) {
      body = (
        <div className="hierarchy-empty" style={{ gridColumn: '1 / -1' }}>
          <Package size={24} aria-hidden />
          <p>No brands in catalogue yet. Add brands from Catalogue.</p>
        </div>
      );
    } else if (isDetailed) {
      body = summaries.map((summary) => (
        <button
          key={summary.brandId}
          type="button"
          className="hierarchy-card hierarchy-card--brand"
          onClick={() => onSelect(summary.brandId, summary.brandName)}
        >
          <div className="hierarchy-card__head">
            <InventoryBrandCell brandName={summary.brandName} logoFilename={summary.logoFilename} />
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
      ));
    } else {
      body = summaries.map((summary) => (
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
      ));
    }

    return (
      <div ref={ref} className={gridClassName}>
        {body}
      </div>
    );
  },
);
