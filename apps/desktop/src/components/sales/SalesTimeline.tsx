import type { AuditLogEntry } from '../../services/api/AuditService';
import { formatDateTime } from '../../lib/datetime';

export interface SalesTimelineEvent {
  id: string;
  label: string;
  date: string;
  user: string | null;
  location: string | null;
  description: string | null;
}

export function buildSalesTimelineEvents(
  logs: AuditLogEntry[],
  locationName: string | null,
): SalesTimelineEvent[] {
  const events: SalesTimelineEvent[] = [];

  for (const log of logs) {
    if (log.action === 'CREATE' && log.entity_type === 'sale') {
      events.push({
        id: log.id,
        label: 'Sold',
        date: log.created_at,
        user: log.actor_display_name,
        location: locationName,
        description: log.description,
      });
      continue;
    }

    if (log.action === 'STATUS_CHANGE' && log.new_value?.status === 'sold') {
      events.push({
        id: log.id,
        label: 'Marked sold',
        date: log.created_at,
        user: log.actor_display_name,
        location: locationName,
        description: log.description,
      });
      continue;
    }

    if (log.source === 'TALLY_SYNC') {
      events.push({
        id: log.id,
        label: 'Tally synced',
        date: log.created_at,
        user: log.actor_display_name,
        location: locationName,
        description: log.description,
      });
    }
  }

  return events.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
}

interface SalesTimelineProps {
  events: SalesTimelineEvent[];
}

export function SalesTimeline({ events }: SalesTimelineProps): JSX.Element {
  if (events.length === 0) {
    return <p className="sales-drawer__muted">No timeline events recorded.</p>;
  }

  return (
    <ol className="sales-timeline">
      {events.map((event) => (
        <li key={event.id} className="sales-timeline__item">
          <span className="sales-timeline__label">{event.label}</span>
          <span className="sales-timeline__meta">{formatDateTime(event.date)}</span>
          {event.user && <span className="sales-timeline__meta">{event.user}</span>}
          {event.location && <span className="sales-timeline__meta">{event.location}</span>}
          {event.description && <span className="sales-timeline__desc">{event.description}</span>}
        </li>
      ))}
    </ol>
  );
}
