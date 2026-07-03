import type { HealthLive, HealthReady } from '../../services/api/HealthService';

interface DashboardSystemStatusProps {
  api: HealthLive | null;
  database: HealthReady | null;
  loading: boolean;
}

function statusClass(value: string): string {
  if (value === 'ok' || value === 'ready') return 'dash-status-ok';
  if (value === 'failed' || value === 'not_ready') return 'dash-status-bad';
  return 'dash-status-warn';
}

export function DashboardSystemStatus({
  api,
  database,
  loading,
}: DashboardSystemStatusProps): JSX.Element {
  if (loading) return <div className="skeleton dash-system__skeleton" />;

  return (
    <dl className="dash-system">
      <div>
        <dt>API status</dt>
        <dd className={statusClass(api?.status ?? 'unknown')}>{api?.status ?? 'unknown'}</dd>
      </div>
      <div>
        <dt>Database</dt>
        <dd className={statusClass(database?.checks.database ?? 'unknown')}>
          {database?.checks.database ?? 'unknown'}
        </dd>
      </div>
      <div>
        <dt>Migrations</dt>
        <dd className={statusClass(database?.checks.migrations ?? 'unknown')}>
          {database?.checks.migrations ?? 'unknown'}
        </dd>
      </div>
      <div>
        <dt>Disk space</dt>
        <dd className={statusClass(database?.checks.disk_space ?? 'unknown')}>
          {database?.checks.disk_space ?? 'unknown'}
        </dd>
      </div>
    </dl>
  );
}
