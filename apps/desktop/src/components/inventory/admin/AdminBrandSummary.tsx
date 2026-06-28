import { MapPin, Package } from 'lucide-react';
import type { BrandInventorySummary } from '../../../lib/inventoryHierarchy';

interface AdminBrandSummaryProps {
  summary: BrandInventorySummary | null;
  brandName?: string | null;
}

export function AdminBrandSummary({ summary, brandName }: AdminBrandSummaryProps): JSX.Element | null {
  if (!summary) return null;

  return (
    <section className="brand-availability-panel" aria-label={`${brandName ?? 'Brand'} stock overview`}>
      <div className="brand-availability-panel__hero">
        <div className="brand-availability-panel__icon" aria-hidden>
          <Package size={22} />
        </div>
        <div>
          <p className="brand-availability-panel__label">Units available now</p>
          <p className="brand-availability-panel__count">{summary.availableUnits}</p>
          {brandName && <p className="brand-availability-panel__brand">{brandName}</p>}
        </div>
      </div>

      {summary.byLocation.length > 0 ? (
        <div className="brand-availability-panel__locations">
          <p className="brand-availability-panel__locations-title">
            <MapPin size={13} aria-hidden />
            By location
          </p>
          <ul className="brand-availability-panel__chips">
            {summary.byLocation.map((row) => (
              <li key={row.locationId} className="brand-availability-panel__chip">
                <span className="brand-availability-panel__chip-name">{row.locationName}</span>
                <span className="brand-availability-panel__chip-count">{row.count}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="brand-availability-panel__empty">No units currently available at any location.</p>
      )}
    </section>
  );
}
