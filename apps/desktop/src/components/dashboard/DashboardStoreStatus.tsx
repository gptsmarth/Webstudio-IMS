import type { DistributionGroup } from '../../services/api/DashboardService';
import { DashboardEmptyState } from './DashboardWidget';

interface DashboardStoreStatusProps {
  locations: DistributionGroup[];
  loading: boolean;
}

export function DashboardStoreStatus({
  locations,
  loading,
}: DashboardStoreStatusProps): JSX.Element {
  if (loading) {
    return (
      <ul className="dash-store-status">
        {Array.from({ length: 3 }, (_, index) => (
          <li key={index} className="dash-store-status__item skeleton" />
        ))}
      </ul>
    );
  }

  const rows = [...locations].sort((a, b) => a.name.localeCompare(b.name));

  if (rows.length === 0) {
    return (
      <DashboardEmptyState
        title="No store status"
        description="Active locations will appear once configured in the system."
      />
    );
  }

  return (
    <ul className="dash-store-status">
      {rows.map((location) => {
        const status = location.available > 0 ? 'Stocked' : 'Empty';
        const tone = location.available > 0 ? 'ok' : 'empty';
        return (
          <li key={location.id} className="dash-store-status__item">
            <div className="dash-store-status__main">
              <span className="dash-store-status__name">{location.name}</span>
              <span className={`dash-store-status__badge dash-store-status__badge--${tone}`}>
                {status}
              </span>
            </div>
            <span className="dash-store-status__meta">{location.available} available</span>
          </li>
        );
      })}
    </ul>
  );
}
