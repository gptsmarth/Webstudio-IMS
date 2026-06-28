import { ArrowRight, CheckCircle2 } from 'lucide-react';
import type { NotificationDetail } from '../../services/api/NotificationService';
import { formatRelativeTime } from '../../lib/datetime';
import { useNavigationStore } from '../../store';
import { DashboardEmptyState, DashboardSkeleton, DashboardWidget } from './DashboardWidget';

interface DashboardNotificationsPanelProps {
  items: NotificationDetail[];
  unreadCount: number;
  loading: boolean;
  onResolve: (id: number) => Promise<void>;
  onMarkRead?: (id: number) => Promise<void>;
}

function severityClass(severity: NotificationDetail['severity']): string {
  switch (severity) {
    case 'error':
      return 'dash-severity dash-severity--critical';
    case 'warning':
      return 'dash-severity dash-severity--warning';
    default:
      return 'dash-severity dash-severity--info';
  }
}

function severityLabel(severity: NotificationDetail['severity']): string {
  if (severity === 'error') return 'critical';
  return severity;
}

export function DashboardNotificationsPanel({
  items,
  unreadCount,
  loading,
  onResolve,
  onMarkRead,
}: DashboardNotificationsPanelProps): JSX.Element {
  const { setRoute } = useNavigationStore();

  const counts = items.reduce(
    (acc, item) => {
      if (item.severity === 'error') acc.critical += 1;
      else if (item.severity === 'warning') acc.warning += 1;
      else acc.info += 1;
      return acc;
    },
    { critical: 0, warning: 0, info: 0 },
  );

  return (
    <DashboardWidget
      title="Notifications"
      subtitle={`${unreadCount} unread`}
      action={(
        <button type="button" className="dash-link-btn" onClick={() => setRoute('notifications')}>
          View all
          <ArrowRight size={14} aria-hidden />
        </button>
      )}
    >
      {loading ? (
        <DashboardSkeleton rows={4} />
      ) : (
        <>
          <div className="dash-notification-counts">
            <span className="dash-severity dash-severity--critical">Critical {counts.critical}</span>
            <span className="dash-severity dash-severity--warning">Warning {counts.warning}</span>
            <span className="dash-severity dash-severity--info">Info {counts.info}</span>
          </div>

          {items.length === 0 ? (
            <DashboardEmptyState
              title="All clear"
              description="No open notifications require attention."
            />
          ) : (
            <ul className="dash-notification-list">
              {items.slice(0, 6).map((item) => (
                <li key={item.id} className="dash-notification-item">
                  <div className="dash-notification-item__main">
                    <span className={severityClass(item.severity)}>{severityLabel(item.severity)}</span>
                    <div>
                      <p className="dash-notification-item__title">{item.title}</p>
                      <p className="dash-notification-item__meta">
                        {formatRelativeTime(item.created_at)}
                        {!item.is_read && <span className="dash-notification-item__unread">Unread</span>}
                      </p>
                    </div>
                  </div>
                  <div className="dash-notification-item__actions">
                    {!item.is_read && onMarkRead && (
                      <button type="button" className="btn btn-ghost btn-sm" onClick={() => void onMarkRead(item.id)}>
                        Mark read
                      </button>
                    )}
                    {!item.is_resolved && (
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => void onResolve(item.id)}
                        title="Archive notification"
                      >
                        <CheckCircle2 size={14} aria-hidden />
                        Archive
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </DashboardWidget>
  );
}
