import { RefreshCw } from 'lucide-react';
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
  fullPage = false,
}: TallyReadinessPanelProps): JSX.Element {
  if (loading) {
    return <div className="skeleton tally-panel__skeleton" />;
  }

  return (
    <div className={`tally-panel ${fullPage ? 'tally-panel--full' : ''}`}>
      <div className="tally-panel__grid">
        <div className="tally-panel__metric">
          <span className="tally-panel__label">Connection</span>
          <span className="tally-panel__value">{tally.connection_status}</span>
        </div>
        <div className="tally-panel__metric">
          <span className="tally-panel__label">Health</span>
          <span className="tally-panel__value">{tally.connection_health}</span>
        </div>
        <div className="tally-panel__metric">
          <span className="tally-panel__label">Last sync</span>
          <span className="tally-panel__value">{tally.last_sync ?? '—'}</span>
        </div>
        <div className="tally-panel__metric">
          <span className="tally-panel__label">Next scheduled sync</span>
          <span className="tally-panel__value">{tally.next_scheduled_sync ?? '—'}</span>
        </div>
        <div className="tally-panel__metric">
          <span className="tally-panel__label">Connected companies</span>
          <span className="tally-panel__value">{tally.connected_companies}</span>
        </div>
        <div className="tally-panel__metric">
          <span className="tally-panel__label">Processed invoices</span>
          <span className="tally-panel__value">{tally.invoices_processed}</span>
        </div>
        <div className="tally-panel__metric">
          <span className="tally-panel__label">Pending issues</span>
          <span className="tally-panel__value">{tally.pending_issues}</span>
        </div>
        <div className="tally-panel__metric">
          <span className="tally-panel__label">Inventory entries</span>
          <span className="tally-panel__value">{tally.inventory_entries_processed}</span>
        </div>
        <div className="tally-panel__metric">
          <span className="tally-panel__label">Sync failures</span>
          <span className="tally-panel__value">{tally.sync_failures}</span>
        </div>
        <div className="tally-panel__metric">
          <span className="tally-panel__label">Voucher types</span>
          <span className="tally-panel__value">
            {tally.voucher_types.length ? tally.voucher_types.join(' · ') : 'Sales · NEW SALE'}
          </span>
        </div>
      </div>

      {fullPage && (
        <dl className="tally-panel__details">
          <div><dt>Skipped invoices</dt><dd>{tally.skipped_invoices || '—'}</dd></div>
          <div><dt>Duplicate invoices</dt><dd>{tally.duplicate_invoices || '—'}</dd></div>
          <div><dt>Model mismatches</dt><dd>{tally.model_mismatches || '—'}</dd></div>
          <div><dt>Missing serials</dt><dd>{tally.missing_serials || '—'}</dd></div>
        </dl>
      )}

      {!tally.available && (
        <p className="tally-panel__hint">
          Enable Tally integration and set the host, port, and company name in the configuration panel above or under System Settings → Tally.
        </p>
      )}

      {tally.last_error && <p className="tally-panel__error">{tally.last_error}</p>}

      {onSync && (
        <button type="button" className="btn btn-secondary btn-sm tally-panel__sync" onClick={onSync} disabled={syncing}>
          <RefreshCw size={14} aria-hidden className={syncing ? 'sales-spin' : undefined} />
          {syncing ? 'Syncing…' : 'Trigger sync'}
        </button>
      )}
    </div>
  );
}
