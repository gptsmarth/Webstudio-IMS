import { RefreshCw } from 'lucide-react';
import { formatDateTime, formatRelativeTime } from '../../lib/datetime';
import { formatCountdown, tallyHealthLabel } from '../../lib/tallyDisplay';
import { useLiveCountdown } from '../../hooks/useLiveCountdown';
import type { TallyStatusSummary } from '../../services/api/TallyService';

interface TallyReadinessPanelProps {
  tally: TallyStatusSummary;
  loading?: boolean;
  onSync?: () => void;
  syncing?: boolean;
  fullPage?: boolean;
}

export function TallyReadinessPanel({
  tally,
  loading,
  onSync,
  syncing,
}: TallyReadinessPanelProps): JSX.Element {
  const operational = tally.operational;
  const pendingRetry = operational?.pending_retry ?? tally.pending_retry;
  const liveRetrySeconds = useLiveCountdown(
    pendingRetry ? (operational?.retry_countdown_seconds ?? null) : null,
  );

  if (loading) {
    return <div className="skeleton tally-panel__skeleton" />;
  }

  const connected = operational?.is_connected ?? tally.is_connected;
  const health = operational?.sync_health ?? tally.connection_health;
  const todaysImports = operational?.imported_today ?? tally.todays_imports;
  const retryLabel =
    liveRetrySeconds != null
      ? formatCountdown(liveRetrySeconds)
      : operational?.retry_countdown_label;

  return (
    <div className="tally-dashboard-widget">
      <div className="tally-dashboard-widget__grid">
        <div className="tally-dashboard-widget__metric">
          <span className="tally-dashboard-widget__label">Tally connected</span>
          <span className={`tally-dashboard-widget__value ${connected ? 'is-ok' : 'is-warn'}`}>
            {connected ? 'Yes' : 'No'}
          </span>
        </div>
        <div className="tally-dashboard-widget__metric">
          <span className="tally-dashboard-widget__label">Last sync</span>
          <span className="tally-dashboard-widget__value" title={tally.last_sync ?? undefined}>
            {tally.last_sync ? formatRelativeTime(tally.last_sync) : '—'}
          </span>
        </div>
        <div className="tally-dashboard-widget__metric">
          <span className="tally-dashboard-widget__label">Pending retry</span>
          <span className={`tally-dashboard-widget__value ${pendingRetry ? 'is-warn' : ''}`}>
            {pendingRetry ? (retryLabel ?? 'Waiting') : 'No'}
          </span>
        </div>
        <div className="tally-dashboard-widget__metric">
          <span className="tally-dashboard-widget__label">Today&apos;s imports</span>
          <span className="tally-dashboard-widget__value">{todaysImports}</span>
        </div>
        <div className="tally-dashboard-widget__metric">
          <span className="tally-dashboard-widget__label">Sync health</span>
          <span
            className={`tally-dashboard-widget__value tally-dashboard-widget__value--${health}`}
          >
            {tallyHealthLabel(health)}
          </span>
        </div>
      </div>

      {tally.last_sync && (
        <p className="tally-dashboard-widget__meta">
          Last successful sync: {formatDateTime(tally.last_sync)}
        </p>
      )}

      {tally.last_error && <p className="tally-panel__error">{tally.last_error}</p>}

      {!tally.available && (
        <p className="tally-panel__hint">
          Enable Tally synchronization under Settings → Tally to import sales automatically.
        </p>
      )}

      {onSync && tally.available && (
        <button
          type="button"
          className="btn btn-secondary btn-sm tally-panel__sync"
          onClick={onSync}
          disabled={syncing}
        >
          <RefreshCw size={14} aria-hidden className={syncing ? 'sales-spin' : undefined} />
          {syncing ? 'Syncing…' : 'Sync now'}
        </button>
      )}
    </div>
  );
}
