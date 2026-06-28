import type { DistributionGroup } from '../../services/api/DashboardService';
import { locationSharePercent } from '../../lib/dashboard';
import { DashboardEmptyState } from './DashboardWidget';

interface DashboardInventoryDistributionProps {
  totalAvailable: number;
  locations: DistributionGroup[];
  loading: boolean;
}

export function DashboardInventoryDistribution({
  totalAvailable,
  locations,
  loading,
}: DashboardInventoryDistributionProps): JSX.Element {
  if (loading) {
    return (
      <div className="dash-distribution">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="dash-distribution__row skeleton" />
        ))}
      </div>
    );
  }

  const activeLocations = [...locations]
    .filter((location) => location.total > 0 || location.available > 0)
    .sort((a, b) => b.available - a.available);

  if (activeLocations.length === 0) {
    return (
      <DashboardEmptyState
        title="No inventory distribution"
        description="Available units by location will appear once laptops are assigned."
      />
    );
  }

  return (
    <div className="dash-inventory-distribution">
      <div className="dash-inventory-distribution__total">
        <span className="dash-inventory-distribution__total-label">Total available inventory</span>
        <span className="dash-inventory-distribution__total-value">{totalAvailable.toLocaleString()}</span>
      </div>

      <div className="dash-distribution">
        {activeLocations.map((location) => {
          const percent = locationSharePercent(location.available, totalAvailable);
          const barWidth = totalAvailable > 0 ? Math.max(4, percent) : 0;
          return (
            <div key={location.id} className="dash-distribution__row">
              <div className="dash-distribution__label">
                <span>{location.name}</span>
                <span className="dash-distribution__count">
                  {location.available.toLocaleString()} available · {percent}%
                </span>
              </div>
              <div className="dash-distribution__track" aria-hidden>
                <div className="dash-distribution__bar" style={{ width: `${barWidth}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
