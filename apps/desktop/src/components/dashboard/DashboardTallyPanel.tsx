import type { TallyStatusSummary } from '../../services/api/TallyService';
import { formatDateTime } from '../../lib/datetime';
import { DashboardEmptyState, DashboardSkeleton } from './DashboardWidget';

interface DashboardTallyPanelProps {
  tally: TallyStatusSummary;
  loading: boolean;
}

function healthLabel(health: TallyStatusSummary['connection_health']): string {
  switch (health) {
    case 'healthy':
      return 'Healthy';
    case 'degraded':
      return 'Degraded';
    default:
      return 'Offline';
  }
}

export function DashboardTallyPanel({ tally, loading }: DashboardTallyPanelProps): JSX.Element {
  if (loading) {
    return <DashboardSkeleton rows={4} />;
  }

  if (!tally.available) {
    return (
      <DashboardEmptyState
        title="Tally integration unavailable"
        description="Connection status will appear when the Tally integration service is configured."
      />
    );
  }

  return (
    <dl className="dash-tally-grid">
      <div className="dash-tally-item">
        <dt>Connected</dt>
        <dd className={tally.connection_status === 'connected' ? 'dash-tally-ok' : 'dash-tally-warn'}>
          {tally.connection_status === 'connected' ? 'Yes' : 'No'}
        </dd>
      </div>
      <div className="dash-tally-item">
        <dt>Last sync</dt>
        <dd>{formatDateTime(tally.last_sync)}</dd>
      </div>
      <div className="dash-tally-item">
        <dt>Invoices processed</dt>
        <dd>{tally.invoices_processed}</dd>
      </div>
      <div className="dash-tally-item">
        <dt>Pending issues</dt>
        <dd className={tally.pending_issues > 0 ? 'dash-tally-warn' : undefined}>{tally.pending_issues}</dd>
      </div>
      <div className="dash-tally-item dash-tally-item--wide">
        <dt>Connection health</dt>
        <dd>{healthLabel(tally.connection_health)}</dd>
        {tally.last_error && <p className="dash-tally-error">{tally.last_error}</p>}
      </div>
    </dl>
  );
}
