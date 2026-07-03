import { useCallback, useEffect, useMemo, useState } from 'react';
import { Download, Search } from 'lucide-react';
import { formatDateTime } from '../../lib/datetime';
import {
  tallyStatusBadgeClass,
  type TallyOperationalSummary,
  type TallySyncHistoryEntry,
} from '../../lib/tallyDisplay';
import { TallyService, type TallySyncHistoryFilters } from '../../services/api/TallyService';

interface TallySyncHistoryPanelProps {
  open: boolean;
  onClose: () => void;
}

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'success', label: 'Success' },
  { value: 'partial', label: 'Partial' },
  { value: 'failed', label: 'Failed' },
  { value: 'offline', label: 'Skipped (offline)' },
  { value: 'running', label: 'Running' },
];

export function TallySyncHistoryPanel({
  open,
  onClose,
}: TallySyncHistoryPanelProps): JSX.Element | null {
  const [entries, setEntries] = useState<TallySyncHistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [search, setSearch] = useState('');

  const filters = useMemo<TallySyncHistoryFilters>(
    () => ({
      status: status || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      search: search.trim() || undefined,
    }),
    [status, dateFrom, dateTo, search],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await TallyService.getSyncHistory(filters);
      setEntries(data);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to load sync history.');
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    if (open) {
      void load();
    }
  }, [open, load]);

  const exportCsv = async () => {
    await TallyService.exportSyncHistory(filters);
  };

  if (!open) return null;

  return (
    <div className="tally-history-overlay" role="presentation" onClick={onClose}>
      <div
        className="tally-history-panel"
        role="dialog"
        aria-labelledby="tally-history-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="tally-history-panel__header">
          <div>
            <h2 id="tally-history-title" className="tally-history-panel__title">
              Tally Sync History
            </h2>
            <p className="tally-history-panel__subtitle">
              Synchronization runs and invoice import activity
            </p>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            Close
          </button>
        </header>

        <div className="tally-history-panel__toolbar">
          <div className="tally-history-panel__filters">
            <select
              className="input input-sm"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value || 'all'} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <input
              className="input input-sm"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              aria-label="From date"
            />
            <input
              className="input input-sm"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              aria-label="To date"
            />
            <label className="tally-history-panel__search">
              <Search size={14} aria-hidden />
              <input
                className="input input-sm"
                type="search"
                placeholder="Search status or errors…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>
          </div>
          <div className="tally-history-panel__actions">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => void load()}
              disabled={loading}
            >
              Apply filters
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => void exportCsv()}
            >
              <Download size={14} aria-hidden /> Export CSV
            </button>
          </div>
        </div>

        {error && <p className="stg-form-error">{error}</p>}

        <div className="tally-history-panel__table-wrap">
          {loading ? (
            <div className="skeleton tally-history-panel__skeleton" />
          ) : entries.length === 0 ? (
            <p className="tally-history-panel__empty">
              No synchronization runs match your filters.
            </p>
          ) : (
            <table className="tally-history-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>Duration</th>
                  <th>Checked</th>
                  <th>Imported</th>
                  <th>Skipped</th>
                  <th>Errors</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={`${entry.started_at}-${entry.start_time}`}>
                    <td>{entry.sync_date}</td>
                    <td>{entry.start_time}</td>
                    <td>{entry.end_time ?? '—'}</td>
                    <td>{entry.duration_label}</td>
                    <td>{entry.invoices_checked}</td>
                    <td>{entry.invoices_imported}</td>
                    <td>{entry.invoices_skipped}</td>
                    <td>{entry.errors_count}</td>
                    <td>
                      <span className={tallyStatusBadgeClass(entry.status)}>
                        {entry.status_label}
                      </span>
                      {entry.error_summary && (
                        <span className="tally-history-table__error" title={entry.error_summary}>
                          {entry.error_summary}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export function TallyOperationalMetrics({
  operational,
}: {
  operational: TallyOperationalSummary;
}): JSX.Element {
  return (
    <div className="tally-ops-grid">
      <div className="tally-ops-card">
        <span className="tally-ops-card__label">Connection</span>
        <span
          className={`tally-ops-card__value ${operational.is_connected ? 'tally-ops-card__value--ok' : 'tally-ops-card__value--warn'}`}
        >
          {operational.connection_label}
        </span>
      </div>
      <div className="tally-ops-card">
        <span className="tally-ops-card__label">Auto sync</span>
        <span className="tally-ops-card__value">
          {operational.auto_sync_enabled ? 'Enabled' : 'Disabled'}
        </span>
      </div>
      <div className="tally-ops-card">
        <span className="tally-ops-card__label">Polling interval</span>
        <span className="tally-ops-card__value">{operational.polling_interval_label}</span>
      </div>
      <div className="tally-ops-card">
        <span className="tally-ops-card__label">Last successful sync</span>
        <span className="tally-ops-card__value">
          {operational.last_successful_sync_at
            ? formatDateTime(operational.last_successful_sync_at)
            : '—'}
        </span>
      </div>
      <div className="tally-ops-card">
        <span className="tally-ops-card__label">Last invoice imported</span>
        <span className="tally-ops-card__value">{operational.last_invoice_imported ?? '—'}</span>
      </div>
      <div className="tally-ops-card">
        <span className="tally-ops-card__label">Last invoice date</span>
        <span className="tally-ops-card__value">{operational.last_invoice_date ?? '—'}</span>
      </div>
      <div className="tally-ops-card">
        <span className="tally-ops-card__label">Next scheduled sync</span>
        <span className="tally-ops-card__value">
          {operational.next_scheduled_sync_at
            ? formatDateTime(operational.next_scheduled_sync_at)
            : '—'}
        </span>
      </div>
      <div className="tally-ops-card">
        <span className="tally-ops-card__label">Last sync duration</span>
        <span className="tally-ops-card__value">{operational.last_sync_duration_label}</span>
      </div>
      <div className="tally-ops-card">
        <span className="tally-ops-card__label">Imported today</span>
        <span className="tally-ops-card__value">{operational.imported_today}</span>
      </div>
      <div className="tally-ops-card">
        <span className="tally-ops-card__label">Imported this week</span>
        <span className="tally-ops-card__value">{operational.imported_this_week}</span>
      </div>
      <div className="tally-ops-card">
        <span className="tally-ops-card__label">Imported this month</span>
        <span className="tally-ops-card__value">{operational.imported_this_month}</span>
      </div>
      <div className="tally-ops-card">
        <span className="tally-ops-card__label">Total imported</span>
        <span className="tally-ops-card__value">{operational.total_imported}</span>
      </div>
      <div className="tally-ops-card tally-ops-card--wide">
        <span className="tally-ops-card__label">Scheduler status</span>
        <span className="tally-ops-card__value">{operational.scheduler_status_label}</span>
      </div>
      {operational.pending_retry && operational.retry_countdown_label && (
        <div className="tally-ops-card">
          <span className="tally-ops-card__label">Retry countdown</span>
          <span className="tally-ops-card__value tally-ops-card__value--warn">
            {operational.retry_countdown_label}
          </span>
        </div>
      )}
    </div>
  );
}
