import { ArrowRight } from 'lucide-react';
import type { RecentActivityEntry } from '../../services/api/DashboardService';
import { extractActivityLocation, formatActivityType } from '../../lib/dashboard';
import { formatRelativeTime } from '../../lib/datetime';
import { useNavigationStore } from '../../store';
import { DashboardEmptyState, DashboardSkeleton, DashboardWidget } from './DashboardWidget';

interface DashboardRecentActivityProps {
  items: RecentActivityEntry[];
  loading: boolean;
}

export function DashboardRecentActivity({
  items,
  loading,
}: DashboardRecentActivityProps): JSX.Element {
  const { setRoute } = useNavigationStore();

  return (
    <DashboardWidget
      title="Recent Activity"
      subtitle="Latest operational events"
      action={
        <button type="button" className="dash-link-btn" onClick={() => setRoute('audit')}>
          View all
          <ArrowRight size={14} aria-hidden />
        </button>
      }
    >
      {loading ? (
        <DashboardSkeleton rows={5} />
      ) : items.length === 0 ? (
        <DashboardEmptyState
          title="No recent activity"
          description="Inventory changes, transfers, and sales will appear here."
        />
      ) : (
        <div className="dash-table-wrap">
          <table className="dash-table">
            <thead>
              <tr>
                <th scope="col">Actor</th>
                <th scope="col">Action</th>
                <th scope="col">Location</th>
                <th scope="col" className="dash-table__time">
                  When
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.actor_display_name ?? 'System'}</td>
                  <td>{formatActivityType(item.activity_type)}</td>
                  <td>{extractActivityLocation(item.description)}</td>
                  <td className="dash-table__time">{formatRelativeTime(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </DashboardWidget>
  );
}
