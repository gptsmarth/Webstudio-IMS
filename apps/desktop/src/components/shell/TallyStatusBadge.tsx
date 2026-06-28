import { RefreshCw } from 'lucide-react';

export type TallyStatus = 'connected' | 'syncing' | 'error' | 'unavailable';

interface TallyStatusBadgeProps {
  status: TallyStatus;
  compact?: boolean;
}

const LABELS: Record<TallyStatus, string> = {
  connected: 'Tally OK',
  syncing: 'Tally Sync',
  error: 'Tally Error',
  unavailable: 'Tally N/A',
};

export function TallyStatusBadge({ status, compact }: TallyStatusBadgeProps): JSX.Element {
  return (
    <div
      className={`app-status-badge${compact ? ' app-status-badge--compact' : ''}`}
      role="status"
      title={`Tally integration: ${LABELS[status]}`}
    >
      <RefreshCw
        size={12}
        aria-hidden
        style={{
          color:
            status === 'connected'
              ? 'var(--color-success)'
              : status === 'syncing'
                ? 'var(--color-primary-500)'
                : status === 'error'
                  ? 'var(--color-danger)'
                  : 'var(--color-text-tertiary)',
        }}
      />
      {!compact && <span>{LABELS[status]}</span>}
    </div>
  );
}
