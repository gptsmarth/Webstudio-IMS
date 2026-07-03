import { Wifi, WifiOff } from 'lucide-react';

export type ConnectionStatus = 'online' | 'offline' | 'checking';

interface ConnectionBadgeProps {
  status: ConnectionStatus;
  label?: string;
  compact?: boolean;
}

export function ConnectionBadge({ status, label, compact }: ConnectionBadgeProps): JSX.Element {
  const isOnline = status === 'online';
  const text = label ?? (status === 'checking' ? 'Checking…' : isOnline ? 'Connected' : 'Offline');

  return (
    <div
      className={`app-status-badge${compact ? ' app-status-badge--compact' : ''}`}
      role="status"
      aria-live="polite"
      title={text}
    >
      {isOnline ? (
        <Wifi size={12} aria-hidden style={{ color: 'var(--color-success)' }} />
      ) : (
        <WifiOff
          size={12}
          aria-hidden
          style={{ color: status === 'checking' ? 'var(--color-warning)' : 'var(--color-danger)' }}
        />
      )}
      {!compact && <span>{text}</span>}
    </div>
  );
}
