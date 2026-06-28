import type { RecentActivityEntry } from '../../services/api/DashboardService';
import { formatActivityType } from '../../lib/dashboard';
import { formatRelativeTime } from '../../lib/datetime';
import { DashboardEmptyState, DashboardSkeleton, DashboardWidget } from './DashboardWidget';

interface DashboardActivityFeedProps {
  title: string;
  subtitle: string;
  items: RecentActivityEntry[];
  loading: boolean;
  activityTypes: string[];
}

export function DashboardActivityFeed({
  title,
  subtitle,
  items,
  loading,
  activityTypes,
}: DashboardActivityFeedProps): JSX.Element {
  const filtered = items.filter((item) => activityTypes.includes(item.activity_type));

  return (
    <DashboardWidget title={title} subtitle={subtitle}>
      {loading ? (
        <DashboardSkeleton rows={4} />
      ) : filtered.length === 0 ? (
        <DashboardEmptyState title="No recent events" description="Activity will appear here as operations occur." />
      ) : (
        <ul className="dash-feed">
          {filtered.slice(0, 6).map((item) => (
            <li key={item.id} className="dash-feed__item">
              <span className="dash-feed__action">{formatActivityType(item.activity_type)}</span>
              <span className="dash-feed__meta">{item.actor_display_name ?? 'System'} · {formatRelativeTime(item.created_at)}</span>
              {item.description && <span className="dash-feed__desc">{item.description}</span>}
            </li>
          ))}
        </ul>
      )}
    </DashboardWidget>
  );
}
