import { useCallback, useState } from 'react';
import { AlertCircle, CalendarClock } from 'lucide-react';
import {
  SalesDetailDrawer,
  SalesFiltersPanel,
  SalesStatusBar,
  SalesTable,
  SalesToolbar,
} from '../../components/sales';
import { useSalesWorkspace } from '../../hooks/useSalesWorkspace';
import { canExportSales } from '../../lib/sales';
import { parseApiError } from '../../lib/apiError';
import { P } from '../../services/PermissionService';
import { TallyService } from '../../services/api/TallyService';
import { useAuthStore } from '../../store';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';

function defaultBackfillFrom(): string {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() - 3, 1);
  return start.toISOString().slice(0, 10);
}

export function SalesPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const workspace = useSalesWorkspace(session?.permissions ?? []);
  const canRunTallySync = session?.permissions?.includes(P.tally.runSync) ?? false;
  const [backfillOpen, setBackfillOpen] = useState(false);
  const [backfillFrom, setBackfillFrom] = useState<string>(defaultBackfillFrom());
  const [backfilling, setBackfilling] = useState(false);
  const [backfillNotice, setBackfillNotice] = useState<string | null>(null);
  const [backfillError, setBackfillError] = useState<string | null>(null);

  const runBackfill = useCallback(async () => {
    if (!backfillFrom) return;
    setBackfilling(true);
    setBackfillError(null);
    setBackfillNotice(null);
    try {
      const result = await TallyService.backfillSales(backfillFrom);
      const parts = [
        `Fetched ${result.fetched} sales invoice(s) from ${result.from_date} to ${result.to_date}.`,
        `${result.sales_created} unit(s) marked sold`,
        `${result.imported} new invoice(s) imported`,
        `${result.skipped} already synced`,
      ];
      if (result.missing_serials > 0) {
        parts.push(`${result.missing_serials} serial(s) not found in stock`);
      }
      if (result.failures > 0) parts.push(`${result.failures} failed — check Tally sync history`);
      setBackfillNotice(`${parts[0]} ${parts.slice(1).join(', ')}.`);
      setBackfillOpen(false);
      await workspace.refresh();
    } catch (err) {
      setBackfillError(parseApiError(err, 'Failed to sync older sales from Tally.'));
    } finally {
      setBackfilling(false);
    }
  }, [backfillFrom, workspace]);

  if (!session) {
    return (
      <div className="sales-page">
        <div className="sales-empty">
          <p className="sales-empty__title">Session unavailable</p>
          <p className="sales-empty__text">Sign in again to access sales.</p>
        </div>
      </div>
    );
  }

  const canExport = canExportSales(session.permissions);

  return (
    <div className="sales-page animate-fade-in">
      <header className="sales-page__header">
        <WorkspacePageBack />
        <div style={{ flex: 1 }}>
          <h1 className="sales-page__title">Sales</h1>
          <p className="sales-page__subtitle">Completed sales, invoices, and customer records.</p>
        </div>
        {canRunTallySync && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setBackfillOpen((open) => !open)}
          >
            <CalendarClock size={14} aria-hidden /> Sync older sales
          </button>
        )}
      </header>

      {backfillOpen && (
        <div className="card" style={{ display: 'grid', gap: 10 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 15 }}>Sync older sales invoices from Tally</h3>
            <p style={{ margin: '4px 0 0', color: 'var(--color-text-tertiary)', fontSize: 13 }}>
              Read-only fetch. Sales invoices from the date you pick (up to today) are checked
              against stock — any serial still in stock that was billed in Tally is marked sold.
              Invoices already synced are skipped, so nothing is ever sold twice. Tally is never
              modified.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <label style={{ display: 'grid', gap: 4, fontSize: 12 }}>
              <span style={{ color: 'var(--color-text-tertiary)' }}>From date</span>
              <input
                type="date"
                className="input"
                value={backfillFrom}
                max={new Date().toISOString().slice(0, 10)}
                onChange={(e) => setBackfillFrom(e.target.value)}
                disabled={backfilling}
              />
            </label>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => void runBackfill()}
              disabled={backfilling || !backfillFrom}
            >
              {backfilling ? 'Syncing…' : 'Sync from Tally'}
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setBackfillOpen(false)}
              disabled={backfilling}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {backfillNotice && (
        <div className="alert alert-success sales-page__alert">
          <span>{backfillNotice}</span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setBackfillNotice(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      {backfillError && (
        <div className="alert alert-danger sales-page__alert">
          <AlertCircle size={14} aria-hidden />
          <span>{backfillError}</span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setBackfillError(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      <SalesToolbar workspace={workspace} canExport={canExport} />

      <SalesFiltersPanel
        filters={workspace.filters}
        setFilters={workspace.setFilters}
        resetFilters={workspace.resetFilters}
        brands={workspace.brands}
        locations={workspace.locations}
        salespeople={workspace.salespeople}
      />

      {workspace.error && (
        <div className="alert alert-danger sales-page__alert">
          <AlertCircle size={14} aria-hidden />
          <span>{workspace.error}</span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void workspace.refresh()}
          >
            Retry
          </button>
        </div>
      )}

      {workspace.actionError && (
        <div className="alert alert-danger sales-page__alert">
          <AlertCircle size={14} aria-hidden />
          <span>{workspace.actionError}</span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={workspace.clearActionError}
          >
            Dismiss
          </button>
        </div>
      )}

      <div
        className={`sales-page__body ${workspace.selectedId ? 'sales-page__body--drawer-open' : ''}`}
      >
        <SalesTable workspace={workspace} onView={(item) => workspace.selectItem(item.id)} />
        <SalesDetailDrawer workspace={workspace} />
      </div>

      <SalesStatusBar workspace={workspace} />
    </div>
  );
}
