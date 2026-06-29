import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Archive,
  Download,
  Eye,
  FileSpreadsheet,
  FileText,
  RefreshCw,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import { formatDateTime } from '../../lib/datetime';
import { formatBytes } from '../../lib/settings';
import {
  SettingsService,
  type BackupAdminDashboard,
  type BackupDetailEntry,
  type BackupHistoryEntry,
  type BackupHistoryFilters,
  type BackupVerifyResult,
} from '../../services/api/SettingsService';
import { ModalPortal } from '../ModalPortal';

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

interface BackupAdminCenterProps {
  canWrite: boolean;
  onRestore: (filename: string) => void;
  onRefreshWorkspace: () => Promise<void>;
}

const EMPTY_FILTERS: BackupHistoryFilters = {};

export function BackupAdminCenter({
  canWrite,
  onRestore,
  onRefreshWorkspace,
}: BackupAdminCenterProps): JSX.Element {
  const [dashboard, setDashboard] = useState<BackupAdminDashboard | null>(null);
  const [history, setHistory] = useState<BackupHistoryEntry[]>([]);
  const [filters, setFilters] = useState<BackupHistoryFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [detail, setDetail] = useState<BackupDetailEntry | null>(null);
  const [verifyResult, setVerifyResult] = useState<BackupVerifyResult | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [dash, rows] = await Promise.all([
        SettingsService.getBackupAdminDashboard(),
        SettingsService.listBackupHistory({ page: 1, page_size: 50, ...filters }),
      ]);
      setDashboard(dash);
      setHistory(rows);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  const retentionLabel = useMemo(() => {
    if (!dashboard) return '—';
    const map: Record<string, string> = {
      last_7: 'Keep last 7',
      last_30: 'Keep last 30',
      last_90: 'Keep last 90',
      unlimited: 'Unlimited',
      custom: `Custom (${dashboard.retention_count})`,
    };
    return map[dashboard.retention_policy] ?? dashboard.retention_policy;
  }, [dashboard]);

  const runAction = async (filename: string, action: () => Promise<unknown>) => {
    setActionBusy(filename);
    setMessage(null);
    try {
      await action();
      await load();
      await onRefreshWorkspace();
    } catch {
      setMessage(`Action failed for ${filename}.`);
    } finally {
      setActionBusy(null);
    }
  };

  return (
    <div className="stg-backup-admin">
      {dashboard && (
        <div className="stg-backup-admin__dashboard">
          <div className={`stg-backup-health stg-backup-health--${dashboard.storage_health === 'healthy' ? 'healthy' : dashboard.storage_health === 'degraded' ? 'degraded' : 'warning'}`}>
            <ShieldCheck size={16} aria-hidden />
            <div>
              <strong>Storage health: {dashboard.storage_health}</strong>
              <p className="stg-muted">{dashboard.backup_folder}</p>
            </div>
          </div>
          <div className="stg-readonly-grid">
            <Readonly label="Disk free" value={formatBytes(dashboard.storage_free_bytes)} />
            <Readonly label="Disk used" value={formatBytes(dashboard.storage_used_bytes)} />
            <Readonly label="Backup folder used" value={formatBytes(dashboard.backup_folder_used_bytes)} />
            <Readonly label="Retention" value={retentionLabel} />
            <Readonly label="Oldest backup" value={dashboard.oldest_backup_at ? formatDateTime(dashboard.oldest_backup_at) : '—'} />
            <Readonly label="Newest backup" value={dashboard.newest_backup_at ? formatDateTime(dashboard.newest_backup_at) : '—'} />
            <Readonly label="Failed backups" value={String(dashboard.failed_backup_count)} />
            <Readonly label="Warnings" value={String(dashboard.warning_count)} />
          </div>
        </div>
      )}

      <div className="stg-backup-admin__toolbar">
        <div className="stg-backup-admin__filters">
          <select
            className="input input-sm"
            value={filters.backup_type ?? ''}
            onChange={(e) => setFilters({ ...filters, backup_type: e.target.value || undefined })}
          >
            <option value="">All types</option>
            <option value="full">Full</option>
            <option value="incremental">Incremental</option>
          </select>
          <select
            className="input input-sm"
            value={filters.status ?? ''}
            onChange={(e) => setFilters({ ...filters, status: e.target.value || undefined })}
          >
            <option value="">All statuses</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="archived">Archived</option>
          </select>
          <input
            className="input input-sm"
            placeholder="Filter by creator"
            value={filters.creator ?? ''}
            onChange={(e) => setFilters({ ...filters, creator: e.target.value || undefined })}
          />
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => void load()}>
            <RefreshCw size={14} aria-hidden />
            Apply
          </button>
        </div>
        <div className="stg-backup-admin__exports">
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void SettingsService.exportBackupHistory('xlsx', filters).then((blob) => downloadBlob(blob, 'backup-history.xlsx'))}
          >
            <FileSpreadsheet size={14} aria-hidden />
            Export Excel
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void SettingsService.exportBackupHistory('pdf', filters).then((blob) => downloadBlob(blob, 'backup-history.pdf'))}
          >
            <FileText size={14} aria-hidden />
            Export PDF
          </button>
        </div>
      </div>

      {message && <p className="stg-backup-error">{message}</p>}
      {loading && <p className="stg-muted">Loading backup history…</p>}

      <div className="stg-backup-admin__table-wrap">
        <table className="stg-backup-admin__table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Date</th>
              <th>Creator</th>
              <th>Duration</th>
              <th>Size</th>
              <th>Status</th>
              <th>Version</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 && !loading && (
              <tr>
                <td colSpan={9} className="stg-muted">No backups match the current filters.</td>
              </tr>
            )}
            {history.map((item) => (
              <tr key={item.filename} className={item.is_archived ? 'stg-backup-admin__row--archived' : ''}>
                <td className="col-mono">{item.filename}</td>
                <td>{item.backup_type ?? 'full'}</td>
                <td>{formatDateTime(item.created_at)}</td>
                <td>{item.creator_display_name ?? '—'}</td>
                <td>{item.duration_ms != null ? `${item.duration_ms} ms` : '—'}</td>
                <td>{formatBytes(item.size_bytes)}</td>
                <td>
                  <span className={`stg-backup-verify stg-backup-verify--${item.verification_status ?? 'unknown'}`}>
                    {item.status ?? item.verification_status}
                  </span>
                </td>
                <td>{item.app_version ?? '—'}</td>
                <td>
                  <div className="stg-backup-admin__actions">
                    <button
                      type="button"
                      className="btn btn-ghost btn-xs"
                      title="View details"
                      disabled={actionBusy === item.filename}
                      onClick={() => void SettingsService.getBackupDetails(item.filename).then(setDetail)}
                    >
                      <Eye size={12} aria-hidden />
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-xs"
                      title="Download"
                      disabled={actionBusy === item.filename}
                      onClick={() => void SettingsService.downloadBackup(item.filename).then((blob) => downloadBlob(blob, item.filename))}
                    >
                      <Download size={12} aria-hidden />
                    </button>
                    {canWrite && (
                      <>
                        <button
                          type="button"
                          className="btn btn-ghost btn-xs"
                          title="Verify"
                          disabled={actionBusy === item.filename}
                          onClick={() => void runAction(item.filename, async () => {
                            const result = await SettingsService.verifyBackup(item.filename);
                            setVerifyResult(result);
                          })}
                        >
                          <ShieldCheck size={12} aria-hidden />
                        </button>
                        <button
                          type="button"
                          className="btn btn-ghost btn-xs"
                          title="Restore"
                          disabled={actionBusy === item.filename}
                          onClick={() => onRestore(item.filename)}
                        >
                          <RefreshCw size={12} aria-hidden />
                        </button>
                        {!item.is_archived && (
                          <button
                            type="button"
                            className="btn btn-ghost btn-xs"
                            title="Archive"
                            disabled={actionBusy === item.filename}
                            onClick={() => void runAction(item.filename, () => SettingsService.archiveBackup(item.filename))}
                          >
                            <Archive size={12} aria-hidden />
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn btn-ghost btn-xs"
                          title="Delete"
                          disabled={actionBusy === item.filename}
                          onClick={() => {
                            if (window.confirm(`Delete backup ${item.filename}? This cannot be undone.`)) {
                              void runAction(item.filename, () => SettingsService.deleteBackup(item.filename));
                            }
                          }}
                        >
                          <Trash2 size={12} aria-hidden />
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {detail && (
        <ModalPortal>
          <div className="stg-restore-overlay" role="presentation" onClick={() => setDetail(null)}>
            <div className="stg-backup-detail animate-slide-in" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
              <h3>Backup details</h3>
              <div className="stg-readonly-grid">
                <Readonly label="Name" value={detail.filename} />
                <Readonly label="Checksum" value={detail.checksum_sha256 ?? '—'} />
                <Readonly label="Schema version" value={detail.schema_version ?? '—'} />
                <Readonly label="App version" value={detail.app_version ?? '—'} />
                <Readonly label="Storage path" value={detail.archive_path ?? '—'} />
              </div>
              {(detail.warnings?.length ?? 0) > 0 && (
                <p className="stg-backup-warning">Warnings: {detail.warnings?.join('; ')}</p>
              )}
              <button type="button" className="btn btn-primary btn-sm" onClick={() => setDetail(null)}>Close</button>
            </div>
          </div>
        </ModalPortal>
      )}

      {verifyResult && (
        <ModalPortal>
          <div className="stg-restore-overlay" role="presentation" onClick={() => setVerifyResult(null)}>
            <div className="stg-backup-detail animate-slide-in" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
              <h3>Verification result</h3>
              <p className={`stg-backup-verify stg-backup-verify--${verifyResult.verification_status}`}>
                {verifyResult.verification_status}
              </p>
              <Readonly label="Checksum valid" value={verifyResult.checksum_valid ? 'Yes' : 'No'} />
              <Readonly label="Integrity valid" value={verifyResult.integrity_valid ? 'Yes' : 'No'} />
              <button type="button" className="btn btn-primary btn-sm" onClick={() => setVerifyResult(null)}>Close</button>
            </div>
          </div>
        </ModalPortal>
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
