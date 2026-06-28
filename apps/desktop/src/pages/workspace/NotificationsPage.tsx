import { useMemo, useState } from 'react';
import { AlertCircle, Archive, Check, Search } from 'lucide-react';
import { useDebounce } from '../../lib/useDebounce';
import {
  matchesNotificationSearch,
  notificationCategoryBadgeClass,
  notificationCategoryLabel,
  notificationTypeLabel,
  parseNotificationDescription,
} from '../../lib/notificationCategories';
import { formatRelativeTime } from '../../lib/datetime';
import { useNotificationCenter } from '../../hooks/useNotificationCenter';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';

export function NotificationsPage(): JSX.Element {
  const center = useNotificationCenter();
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'' | 'info' | 'warning' | 'error'>('');
  const debouncedSearch = useDebounce(search, 250);

  const filtered = useMemo(() => center.items.filter((item) => {
    if (categoryFilter && item.severity !== categoryFilter) return false;
    return matchesNotificationSearch(item, debouncedSearch);
  }), [categoryFilter, center.items, debouncedSearch]);

  return (
    <div className="notif-page animate-fade-in">
      <header className="notif-page__header">
        <WorkspacePageBack />
        <div className="notif-page__title-row">
          <div className="notif-page__title-block">
            <h1 className="notif-page__title">Notification Center</h1>
            <p className="notif-page__subtitle">
              Information, warnings, and critical alerts from inventory, sales, transfers, and Tally sync.
            </p>
          </div>
          <span className="badge badge-neutral notif-page__count">{center.unreadCount} unread</span>
        </div>
      </header>

      <div className="notif-page__panel">
        <div className="toolbar-row notif-page__toolbar">
          <label className="toolbar-field notif-page__search-field">
            <span className="toolbar-field__label">Search</span>
            <div className="toolbar-search-control">
              <Search size={14} className="toolbar-search-control__icon" aria-hidden />
              <input
                className="input"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search notifications…"
              />
            </div>
          </label>
          <label className="toolbar-field notif-page__filter-field">
            <span className="toolbar-field__label">Category</span>
            <select
              className="input"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value as typeof categoryFilter)}
            >
              <option value="">All categories</option>
              <option value="info">Information</option>
              <option value="warning">Warning</option>
              <option value="error">Critical</option>
            </select>
          </label>
        </div>

        {center.loading && (
          <div className="notif-page__skeleton">
            {Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton notif-card__skeleton" />)}
          </div>
        )}

        {!center.loading && filtered.length === 0 && (
          <div className="notif-page__empty">
            <AlertCircle size={20} aria-hidden />
            <p>No notifications match your filters.</p>
          </div>
        )}

        <ul className="notif-page__list">
        {!center.loading && filtered.map((item) => {
          const parsed = parseNotificationDescription(item.title, item.description);
          return (
          <li
            key={item.id}
            className={`notif-card notif-card--${item.severity} ${item.is_read ? '' : 'notif-card--unread'}`}
          >
            <div className="notif-card__head">
              <span className={`badge ${notificationCategoryBadgeClass(item.severity)} notif-card__badge`}>
                {notificationCategoryLabel(item.severity)}
              </span>
              <span className="notif-card__type">{notificationTypeLabel(item.notification_type)}</span>
              <time className="notif-card__time">{formatRelativeTime(item.created_at)}</time>
            </div>
            <div className="notif-card__body">
              <h2 className="notif-card__title">{item.title}</h2>
              <p className="notif-card__desc">{parsed.summary || item.description}</p>
              {parsed.details.length > 0 && (
                <dl className="struct-panel__rows notif-card__details">
                  {parsed.details.map((row) => (
                    <div key={row.key} className="struct-panel__row">
                      <dt>{row.label}</dt>
                      <dd className={row.label.toLowerCase().includes('id') ? 'col-mono' : undefined}>{row.value}</dd>
                    </div>
                  ))}
                </dl>
              )}
              {item.serial_number && <p className="notif-card__serial col-mono">Serial {item.serial_number}</p>}
            </div>
            <div className="notif-card__actions">
              {!item.is_read && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void center.markRead(item.id)}>
                  <Check size={14} aria-hidden />
                  Mark read
                </button>
              )}
              {!item.is_resolved && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void center.archive(item.id)}>
                  <Archive size={14} aria-hidden />
                  Archive
                </button>
              )}
            </div>
          </li>
          );
        })}
        </ul>
      </div>
    </div>
  );
}
