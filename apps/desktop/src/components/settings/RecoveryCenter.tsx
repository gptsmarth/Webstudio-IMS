import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Database,
  HardDrive,
  HeartPulse,
  Server,
  ShieldCheck,
  Wand2,
} from 'lucide-react';
import { formatDateTime } from '../../lib/datetime';
import { formatBytes } from '../../lib/settings';
import {
  SettingsService,
  type RecoveryCenterDashboard,
  type RecoveryReports,
} from '../../services/api/SettingsService';

interface RecoveryCenterProps {
  canManageBackup: boolean;
  canViewRestore: boolean;
  canExecuteRestore: boolean;
  onOpenWizard: () => void;
  onOpenNetworkWizard: () => void;
  onOpenOfficeDeploymentWizard: () => void;
  onOpenRestore: () => void;
  onRunBackup: () => Promise<void>;
}

function statusClass(value: string): string {
  if (value === 'healthy' || value === 'ok' || value === 'ready' || value === 'passed') {
    return 'stg-recovery-status--healthy';
  }
  if (value === 'critical' || value === 'failed' || value === 'not_ready' || value === 'degraded') {
    return 'stg-recovery-status--critical';
  }
  return 'stg-recovery-status--warning';
}

function readinessLabel(value: string): string {
  const map: Record<string, string> = {
    ready: 'Ready',
    partial: 'Partially ready',
    not_ready: 'Not ready',
  };
  return map[value] ?? value;
}

export function RecoveryCenter({
  canManageBackup,
  canViewRestore,
  canExecuteRestore,
  onOpenWizard,
  onOpenNetworkWizard,
  onOpenOfficeDeploymentWizard,
  onOpenRestore,
  onRunBackup,
}: RecoveryCenterProps): JSX.Element {
  const [center, setCenter] = useState<RecoveryCenterDashboard | null>(null);
  const [reports, setReports] = useState<RecoveryReports | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [dashboard, reportData] = await Promise.all([
        SettingsService.getRecoveryCenter(),
        SettingsService.getRecoveryReports(),
      ]);
      setCenter(dashboard);
      setReports(reportData);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !center) {
    return <p className="stg-muted">Loading recovery center…</p>;
  }

  return (
    <div className="stg-recovery">
      {center && (
        <>
          <div className={`stg-recovery-banner ${statusClass(center.system_health)}`}>
            <HeartPulse size={18} aria-hidden />
            <div>
              <strong>System health: {center.system_health}</strong>
              <p className="stg-muted">
                Recovery readiness is {readinessLabel(center.recovery_readiness).toLowerCase()}.
              </p>
            </div>
            {canExecuteRestore && (
              <button type="button" className="btn btn-primary btn-sm" onClick={onOpenWizard}>
                <Wand2 size={14} aria-hidden />
                Recovery wizard
              </button>
            )}
            {canExecuteRestore && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={onOpenNetworkWizard}>
                Network wizard
              </button>
            )}
            {canExecuteRestore && (
              <button type="button" className="btn btn-primary btn-sm" onClick={onOpenOfficeDeploymentWizard}>
                <Server size={14} aria-hidden />
                Office deployment
              </button>
            )}
          </div>

          <div className="stg-recovery-grid">
            <article className="stg-recovery-card">
              <Database size={16} aria-hidden />
              <span className="stg-recovery-card__label">Database status</span>
              <strong className={statusClass(center.database_status)}>{center.database_status}</strong>
            </article>
            <article className="stg-recovery-card">
              <ShieldCheck size={16} aria-hidden />
              <span className="stg-recovery-card__label">Backup status</span>
              <strong className={statusClass(center.backup_status)}>{center.backup_status}</strong>
            </article>
            <article className="stg-recovery-card">
              <HardDrive size={16} aria-hidden />
              <span className="stg-recovery-card__label">Storage</span>
              <strong className={statusClass(center.storage_status)}>{center.storage_status}</strong>
              <span className="stg-muted">{formatBytes(center.storage_free_bytes)} free</span>
            </article>
            <article className="stg-recovery-card">
              <Activity size={16} aria-hidden />
              <span className="stg-recovery-card__label">Recovery readiness</span>
              <strong className={statusClass(center.recovery_readiness)}>
                {readinessLabel(center.recovery_readiness)}
              </strong>
            </article>
          </div>

          <div className="stg-readonly-grid">
            <Readonly
              label="Last backup"
              value={center.last_backup_at ? formatDateTime(center.last_backup_at) : 'Never'}
            />
            <Readonly
              label="Last restore"
              value={center.last_restore_at ? formatDateTime(center.last_restore_at) : 'Never'}
            />
            <Readonly label="Backup folder" value={center.backup_folder} />
            <Readonly label="Failed backups" value={String(center.failed_backup_count)} />
          </div>

          {center.readiness_score && (
            <div className="stg-recovery-readiness-score">
              <h4 className="stg-subtitle">Recovery readiness score</h4>
              <div className="stg-recovery-metrics">
                <div>
                  <span className="stg-muted">Overall</span>
                  <strong>{center.readiness_score.overall_score}%</strong>
                </div>
                <div>
                  <span className="stg-muted">Database</span>
                  <strong>{center.readiness_score.database_health_score}%</strong>
                </div>
                <div>
                  <span className="stg-muted">Backup age</span>
                  <strong>{center.readiness_score.latest_backup_age_score}%</strong>
                </div>
                <div>
                  <span className="stg-muted">Verification</span>
                  <strong>{center.readiness_score.backup_verification_score}%</strong>
                </div>
                <div>
                  <span className="stg-muted">Storage</span>
                  <strong>{center.readiness_score.storage_health_score}%</strong>
                </div>
              </div>
            </div>
          )}

          {center.storage_monitoring && (
            <div className="stg-readonly-grid">
              <Readonly label="Estimated remaining backups" value={String(center.storage_monitoring.estimated_remaining_backups ?? '—')} />
              <Readonly label="Retention used" value={String(center.storage_monitoring.retention_used ?? '—')} />
            </div>
          )}

          {center.health_issues.length > 0 && (
            <div className="stg-recovery-issues">
              <h4 className="stg-subtitle">
                <AlertTriangle size={14} aria-hidden />
                Health checks
              </h4>
              <ul>
                {center.health_issues.map((issue) => (
                  <li key={issue.code} className={`stg-recovery-issue stg-recovery-issue--${issue.severity}`}>
                    <strong>{issue.title}</strong>
                    <span>{issue.message}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {reports && (
        <div className="stg-recovery-reports">
          <h4 className="stg-subtitle">Recovery reports</h4>
          <div className="stg-recovery-metrics">
            <div>
              <span className="stg-muted">Backup success rate</span>
              <strong>{reports.backup_success_rate}%</strong>
            </div>
            <div>
              <span className="stg-muted">Total backups</span>
              <strong>{reports.total_backups}</strong>
            </div>
            <div>
              <span className="stg-muted">Failed backups</span>
              <strong>{reports.failed_backups}</strong>
            </div>
          </div>

          {reports.failure_analysis.length > 0 && (
            <div className="stg-recovery-failures">
              <h5>Failure analysis</h5>
              <ul>
                {reports.failure_analysis.map((item) => (
                  <li key={item.reason}>
                    <span className="col-mono">{item.reason}</span>
                    <span>{item.count}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {reports.recovery_history.length > 0 && (
            <div className="stg-recovery-history">
              <h5>Recovery history</h5>
              <ul>
                {reports.recovery_history.map((item) => (
                  <li key={item.id} className="stg-backup-row">
                    <span className="col-mono">{item.filename}</span>
                    <span className="stg-muted">
                      {item.restore_scope} · {item.status} · {formatDateTime(item.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!reports.export_supported && (
            <p className="stg-muted">Report export (Excel/PDF) — future-ready.</p>
          )}
        </div>
      )}

      {(canManageBackup || canViewRestore) && (
        <div className="stg-actions">
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => void load()}>
            Refresh
          </button>
          {canManageBackup && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => void onRunBackup()}>
              Run backup
            </button>
          )}
          {canViewRestore && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={onOpenRestore}>
              Open restore center
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function Readonly({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="stg-readonly">
      <span className="stg-readonly__label">{label}</span>
      <span className="stg-readonly__value">{value}</span>
    </div>
  );
}
