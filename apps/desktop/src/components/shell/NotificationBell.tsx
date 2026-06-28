import { Bell } from 'lucide-react';

interface NotificationBellProps {
  count?: number;
  onClick?: () => void;
}

export function NotificationBell({ count = 0, onClick }: NotificationBellProps): JSX.Element {
  return (
    <button
      type="button"
      className="app-toolbar-icon-btn"
      onClick={onClick}
      aria-label={count > 0 ? `${count} unread notifications` : 'Notifications'}
    >
      <Bell size={16} aria-hidden />
      {count > 0 && (
        <span className="app-toolbar-badge" aria-hidden>
          {count > 9 ? '9+' : count}
        </span>
      )}
    </button>
  );
}
