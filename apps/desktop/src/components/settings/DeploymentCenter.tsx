import { useCallback, useEffect, useState } from 'react';
import {
  CheckCircle2,
  Download,
  FileText,
  History,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
  Trash2,
  Upload,
} from 'lucide-react';
import { formatDateTime } from '../../lib/datetime';
import {
  DeploymentCenterService,
  type DeploymentAnalytics,
  type DeploymentCenterDashboard,
  type DeploymentEventItem,
  type DeploymentPackageItem,
} from '../../services/api/DeploymentCenterService';
import { ModalPortal } from '../ModalPortal';
import { Readonly, Section } from './settingsShared';

interface DeploymentCenterProps {
  canModify: boolean;
}

type ApprovalAction = 'deploy' | 'rollback' | 'delete' | null;

export function DeploymentCenter({ canModify }: DeploymentCenterProps): JSX.Element {
  const [dashboard, setDashboard] = useState<DeploymentCenterDashboard | null>(null);
  const [analytics, setAnalytics] = useState<DeploymentAnalytics | null>(null);
  const [history, setHistory] = useState<DeploymentEventItem[]>([]);
  const [logs, setLogs] = useState<DeploymentEventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [approvalAction, setApprovalAction] = useState<ApprovalAction>(null);
  const [approvalJobId, setApprovalJobId] = useState<number | null>(null);
  const [approved, setApproved] = useState(false);
  const [logsOpen, setLogsOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [dash, hist, logRows, analyticsPayload] = await Promise.all([
        DeploymentCenterService.getDashboard(),
        DeploymentCenterService.getHistory(1, 20),
        DeploymentCenterService.getLogs(1, 50),
        DeploymentCenterService.getAnalytics(),
      ]);
      setDashboard(dash);
      setAnalytics(analyticsPayload);
      setHistory(hist.items);
      setLogs(logRows.items);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runAction = async (key: string, action: () => Promise<unknown>) => {
    setBusy(key);
    setMessage(null);
    try {
      await action();
      await load();
      setMessage('Action completed successfully.');
    } catch {
      setMessage('Action failed. Check server logs for details.');
    } finally {
      setBusy(null);
    }
  };

  const openApproval = (action: ApprovalAction, jobId?: number) => {
    setApprovalAction(action);
    setApprovalJobId(jobId ?? null);
    setApproved(false);
  };

  const confirmApproval = async () => {
    if (!approved || !approvalAction) return;
    if (approvalAction === 'deploy' && approvalJobId != null) {
      await runAction('deploy', () => DeploymentCenterService.deploy(approvalJobId, true));
    } else if (approvalAction === 'rollback') {
      await runAction('rollback', () => DeploymentCenterService.rollback(true));
    } else if (approvalAction === 'delete' && approvalJobId != null) {
      await runAction('delete', () => DeploymentCenterService.deletePackage(approvalJobId, true));
    }
    setApprovalAction(null);
    setApprovalJobId(null);
    setApproved(false);
  };

  const statusLabel = dashboard?.deployment_status?.replace(/_/g, ' ') ?? '—';

  return (
    <div className="stg-backup-admin">
      <Section title="Deployment Center">
        <p className="stg-muted">
          Enterprise release management for this WEBSTUDIO Server. Downloads come from GitHub via
          the server only. Deployment always requires administrator approval — packages are never
          applied automatically.
        </p>

        {loading && !dashboard ? <p className="stg-loading">Loading deployment status…</p> : null}

        {dashboard && (
          <>
            <div className="stg-backup-admin__dashboard">
              <div
                className={`stg-backup-health stg-backup-health--${dashboard.compatibility_status === 'compatible' ? 'healthy' : dashboard.compatibility_status === 'update_available' ? 'warning' : 'degraded'}`}
              >
                <ShieldCheck size={16} aria-hidden />
                <div>
                  <strong>
                    Compatibility: {dashboard.compatibility_status.replace(/_/g, ' ')}
                  </strong>
                  <p className="stg-muted">Deployment status: {statusLabel}</p>
                </div>
              </div>
              <div className="stg-readonly-grid">
                <Readonly label="Current version" value={dashboard.current_version ?? '—'} />
                <Readonly label="Latest version" value={dashboard.latest_version ?? '—'} />
                <Readonly label="Downloaded version" value={dashboard.downloaded_version ?? '—'} />
                <Readonly label="Release channel" value={dashboard.release_channel} />
                <Readonly label="Build number" value={String(dashboard.build_number ?? '—')} />
                <Readonly
                  label="Git commit"
                  value={dashboard.git_short ?? dashboard.git_commit ?? '—'}
                />
                <Readonly
                  label="Release date"
                  value={dashboard.release_date ? formatDateTime(dashboard.release_date) : '—'}
                />
                <Readonly label="Updates folder" value={dashboard.updates_root} />
                <Readonly label="GitHub repo" value={dashboard.github_repo || '—'} />
                <Readonly
                  label="Auto deploy"
                  value={dashboard.auto_deploy ? 'Enabled' : 'Disabled'}
                />
              </div>
            </div>

            <div className="stg-backup-admin__toolbar">
              <div className="stg-backup-admin__exports">
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  disabled={!!busy}
                  onClick={() => void runAction('refresh', () => DeploymentCenterService.refresh())}
                >
                  <RefreshCw size={14} /> Refresh
                </button>
                {canModify && (
                  <>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      disabled={!!busy}
                      onClick={() =>
                        void runAction('check', () => DeploymentCenterService.checkUpdates())
                      }
                    >
                      <Search size={14} /> Check updates
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      disabled={!!busy}
                      onClick={() =>
                        void runAction('download', () => DeploymentCenterService.download())
                      }
                    >
                      <Download size={14} /> Download
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      disabled={!!busy}
                      onClick={() => setLogsOpen(true)}
                    >
                      <FileText size={14} /> View logs
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      disabled={!!busy}
                      onClick={() => openApproval('rollback')}
                    >
                      <RotateCcw size={14} /> Rollback
                    </button>
                  </>
                )}
              </div>
            </div>

            {message && <p className="stg-backup-result">{message}</p>}

            <h3 className="stg-subtitle">Downloaded packages</h3>
            <PackageTable
              packages={dashboard.downloaded_packages}
              canModify={canModify}
              busy={busy}
              onValidate={(jobId) =>
                void runAction(`validate-${jobId}`, () => DeploymentCenterService.validate(jobId))
              }
              onDeploy={(jobId) => openApproval('deploy', jobId)}
              onDelete={(jobId) => openApproval('delete', jobId)}
            />

            <h3 className="stg-subtitle">
              <History size={14} aria-hidden /> Deployment history
            </h3>
            <EventTable events={history} />

            {analytics && (
              <>
                <h3 className="stg-subtitle">Deployment analytics</h3>
                <p className="stg-muted">
                  Generated {formatDateTime(analytics.generated_at)} — release downloads, failures,
                  scheduler recovery, and client version distribution.
                </p>
                <div className="stg-readonly-grid">
                  <Readonly
                    label="Pending downloads"
                    value={String(analytics.summary.pending_downloads)}
                  />
                  <Readonly
                    label="Failed downloads"
                    value={String(analytics.summary.failed_downloads)}
                  />
                  <Readonly
                    label="Retry queue"
                    value={String(analytics.summary.retry_queue_size)}
                  />
                  <Readonly
                    label="Failed deployments"
                    value={String(analytics.summary.failed_deployments)}
                  />
                  <Readonly
                    label="Failed rollbacks"
                    value={String(analytics.summary.failed_rollbacks)}
                  />
                  <Readonly
                    label="Last GitHub sync"
                    value={
                      analytics.summary.last_github_sync_at
                        ? formatDateTime(analytics.summary.last_github_sync_at)
                        : '—'
                    }
                  />
                  <Readonly
                    label="GitHub sync status"
                    value={analytics.summary.last_github_sync_status ?? '—'}
                  />
                  <Readonly
                    label="Rollback records"
                    value={String(analytics.summary.rollback_total)}
                  />
                </div>

                <h4 className="stg-subtitle">Retry queue</h4>
                <SimpleTable
                  emptyLabel="No jobs waiting for retry."
                  headers={['Version', 'Status', 'Attempts', 'Next retry', 'Error']}
                  rows={analytics.retry_queue.map((job) => [
                    String(job.release_version ?? '—'),
                    String(job.status ?? '—'),
                    `${String(job.attempt_count ?? 0)}/${String(job.max_attempts ?? 0)}`,
                    job.next_retry_at ? formatDateTime(String(job.next_retry_at)) : '—',
                    String(job.error_message ?? '—'),
                  ])}
                />

                <h4 className="stg-subtitle">Deployment failures</h4>
                <SimpleTable
                  emptyLabel="No deployment failures recorded."
                  headers={['Time', 'Kind', 'Action', 'Version', 'Error']}
                  rows={analytics.deployment_failures.map((item) => [
                    item.timestamp ? formatDateTime(String(item.timestamp)) : '—',
                    String(item.kind ?? '—'),
                    String(item.action ?? '—'),
                    String(item.release_version ?? '—'),
                    String(item.error_message ?? '—'),
                  ])}
                />

                <h4 className="stg-subtitle">Deployment durations</h4>
                <SimpleTable
                  emptyLabel="No completed deployment runs yet."
                  headers={['Run', 'Version', 'Status', 'Duration (s)', 'Completed']}
                  rows={analytics.deployment_durations.map((item) => [
                    String(item.run_id ?? '—'),
                    String(item.release_version ?? '—'),
                    String(item.status ?? '—'),
                    String(item.duration_seconds ?? '—'),
                    item.completed_at ? formatDateTime(String(item.completed_at)) : '—',
                  ])}
                />

                <h4 className="stg-subtitle">Health check history</h4>
                <SimpleTable
                  emptyLabel="No health check results recorded."
                  headers={['Source', 'Run', 'Status', 'Time', 'Detail']}
                  rows={analytics.health_check_history.map((item) => [
                    String(item.source ?? '—'),
                    String(item.run_id ?? '—'),
                    String(item.status ?? '—'),
                    item.timestamp ? formatDateTime(String(item.timestamp)) : '—',
                    JSON.stringify(item.detail ?? {}),
                  ])}
                />

                <h4 className="stg-subtitle">Desktop version distribution</h4>
                <VersionDistributionTable rows={analytics.desktop_version_distribution} />

                <h4 className="stg-subtitle">Mobile version distribution</h4>
                <VersionDistributionTable rows={analytics.mobile_version_distribution} />

                <h4 className="stg-subtitle">Rollback history</h4>
                <SimpleTable
                  emptyLabel="No rollback runs recorded."
                  headers={['Run', 'From', 'To', 'Status', 'Completed']}
                  rows={analytics.rollback_history.map((item) => [
                    String(item.run_id ?? '—'),
                    String(item.from_release_version ?? '—'),
                    String(item.to_release_version ?? '—'),
                    String(item.status ?? '—'),
                    item.completed_at ? formatDateTime(String(item.completed_at)) : '—',
                  ])}
                />

                <h4 className="stg-subtitle">GitHub polling</h4>
                <div className="stg-readonly-grid">
                  <Readonly
                    label="Polling interval"
                    value={
                      analytics.github_polling_history.polling_interval_seconds != null
                        ? `${String(analytics.github_polling_history.polling_interval_seconds)}s`
                        : '—'
                    }
                  />
                  <Readonly
                    label="Last shutdown"
                    value={
                      analytics.github_polling_history.last_shutdown_at
                        ? formatDateTime(String(analytics.github_polling_history.last_shutdown_at))
                        : '—'
                    }
                  />
                  <Readonly
                    label="Last recovery"
                    value={
                      analytics.github_polling_history.last_recovery_at
                        ? formatDateTime(String(analytics.github_polling_history.last_recovery_at))
                        : '—'
                    }
                  />
                </div>

                <h4 className="stg-subtitle">Scheduler recovery</h4>
                <SimpleTable
                  emptyLabel="No scheduler recovery data."
                  headers={['Scheduler', 'Last run', 'Status', 'Next run', 'Recovered']}
                  rows={analytics.scheduler_recovery.map((item) => [
                    String(item.scheduler_key ?? '—'),
                    item.last_run_at ? formatDateTime(String(item.last_run_at)) : '—',
                    String(item.last_run_status ?? '—'),
                    item.next_run_at ? formatDateTime(String(item.next_run_at)) : '—',
                    item.recovered ? 'Yes' : 'No',
                  ])}
                />
              </>
            )}
          </>
        )}
      </Section>

      {approvalAction && (
        <ModalPortal>
          <div className="modal-backdrop" role="presentation">
            <div
              className="modal"
              role="dialog"
              aria-modal="true"
              aria-label="Administrator approval"
            >
              <h2>Administrator approval required</h2>
              <p className="stg-muted">
                Confirm that you approve this {approvalAction} action. WEBSTUDIO never deploys
                releases automatically.
              </p>
              <label className="stg-field">
                <input
                  type="checkbox"
                  checked={approved}
                  onChange={(event) => setApproved(event.target.checked)}
                />
                <span className="stg-field__label">
                  I am the administrator and I approve this action
                </span>
              </label>
              <div className="stg-actions">
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => setApprovalAction(null)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  disabled={!approved || !!busy}
                  onClick={() => void confirmApproval()}
                >
                  Confirm
                </button>
              </div>
            </div>
          </div>
        </ModalPortal>
      )}

      {logsOpen && (
        <ModalPortal>
          <div className="modal-backdrop" role="presentation">
            <div
              className="modal modal--wide"
              role="dialog"
              aria-modal="true"
              aria-label="Deployment logs"
            >
              <h2>Deployment logs</h2>
              <EventTable events={logs} />
              <div className="stg-actions">
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => setLogsOpen(false)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </ModalPortal>
      )}
    </div>
  );
}

function PackageTable({
  packages,
  canModify,
  busy,
  onValidate,
  onDeploy,
  onDelete,
}: {
  packages: DeploymentPackageItem[];
  canModify: boolean;
  busy: string | null;
  onValidate: (jobId: number) => void;
  onDeploy: (jobId: number) => void;
  onDelete: (jobId: number) => void;
}): JSX.Element {
  if (!packages.length) {
    return <p className="stg-muted">No downloaded packages yet.</p>;
  }
  return (
    <div className="stg-backup-admin__table-wrap">
      <table className="stg-backup-admin__table">
        <thead>
          <tr>
            <th>Version</th>
            <th>Build</th>
            <th>Status</th>
            <th>Validated</th>
            <th>Checksums</th>
            <th>Completed</th>
            {canModify && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {packages.map((pkg) => (
            <tr key={pkg.job_id}>
              <td>{pkg.release_version}</td>
              <td>{pkg.build_number}</td>
              <td>{pkg.status}</td>
              <td>{pkg.manifest_validated ? 'Yes' : 'No'}</td>
              <td>{pkg.checksums_verified ? 'Yes' : 'No'}</td>
              <td>{pkg.completed_at ? formatDateTime(pkg.completed_at) : '—'}</td>
              {canModify && (
                <td>
                  <div className="stg-backup-admin__actions">
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      disabled={!!busy}
                      onClick={() => onValidate(pkg.job_id)}
                    >
                      <CheckCircle2 size={14} /> Validate
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      disabled={!!busy || !pkg.manifest_validated}
                      onClick={() => onDeploy(pkg.job_id)}
                    >
                      <Upload size={14} /> Deploy
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      disabled={!!busy}
                      onClick={() => onDelete(pkg.job_id)}
                    >
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function VersionDistributionTable({
  rows,
}: {
  rows: DeploymentAnalytics['desktop_version_distribution'];
}): JSX.Element {
  if (!rows.length) {
    return <p className="stg-muted">No client version observations yet.</p>;
  }
  return (
    <SimpleTable
      emptyLabel="No client version observations yet."
      headers={['Platform', 'Version', 'Observations', 'Channel', 'Last seen']}
      rows={rows.map((row) => [
        row.platform,
        row.client_version,
        String(row.observation_count),
        row.release_channel ?? '—',
        formatDateTime(row.last_seen_at),
      ])}
    />
  );
}

function SimpleTable({
  headers,
  rows,
  emptyLabel,
}: {
  headers: string[];
  rows: string[][];
  emptyLabel: string;
}): JSX.Element {
  if (!rows.length) {
    return <p className="stg-muted">{emptyLabel}</p>;
  }
  return (
    <div className="stg-backup-admin__table-wrap">
      <table className="stg-backup-admin__table">
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${headers[0]}-${index}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${index}-${cellIndex}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EventTable({ events }: { events: DeploymentEventItem[] }): JSX.Element {
  if (!events.length) {
    return <p className="stg-muted">No deployment events recorded yet.</p>;
  }
  return (
    <div className="stg-backup-admin__table-wrap">
      <table className="stg-backup-admin__table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Action</th>
            <th>Status</th>
            <th>Version</th>
            <th>Approved</th>
            <th>Detail</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td>{formatDateTime(event.created_at)}</td>
              <td>{event.event_type}</td>
              <td>{event.status}</td>
              <td>{event.release_version ?? '—'}</td>
              <td>{event.administrator_approved ? 'Yes' : 'No'}</td>
              <td>{event.error_message ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
