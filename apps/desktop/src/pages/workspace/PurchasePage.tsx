import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, ArrowLeft, Ban, CalendarClock, RefreshCw, X } from 'lucide-react';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';
import { PurchaseImportDialog } from '../../components/purchase/PurchaseImportDialog';
import { parseApiError } from '../../lib/apiError';
import { P } from '../../services/PermissionService';
import { useAuthStore } from '../../store';
import {
  PurchaseService,
  type PurchaseModelGroup,
  type PurchaseQueueItem,
  type PurchaseVoucherDetail,
} from '../../services/api/PurchaseService';

type StatusFilter = '' | 'pending' | 'partially_imported' | 'imported';

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  partially_imported: 'Partially imported',
  imported: 'Imported',
};

function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  const num = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(num)) return String(value);
  return num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function StatusBadge({ status }: { status: string }): JSX.Element {
  const cls =
    status === 'imported'
      ? 'badge badge-success'
      : status === 'partially_imported'
        ? 'badge badge-warning'
        : 'badge';
  return <span className={cls}>{STATUS_LABELS[status] ?? status}</span>;
}

function defaultBackfillFrom(): string {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() - 3, 1);
  return start.toISOString().slice(0, 10);
}

export function PurchasePage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const canImport = session?.permissions?.includes(P.purchase.import) ?? false;
  const canView = session?.permissions?.includes(P.purchase.view) ?? false;
  const [items, setItems] = useState<PurchaseQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const [detail, setDetail] = useState<PurchaseVoucherDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [importGroup, setImportGroup] = useState<PurchaseModelGroup | null>(null);
  const [ignoreTarget, setIgnoreTarget] = useState<{ id: number; label: string } | null>(null);
  const [ignoring, setIgnoring] = useState(false);
  const [backfillOpen, setBackfillOpen] = useState(false);
  const [backfillFrom, setBackfillFrom] = useState<string>(defaultBackfillFrom());
  const [backfilling, setBackfilling] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await PurchaseService.listQueue(statusFilter || undefined);
      setItems(data);
    } catch (err) {
      setError(parseApiError(err, 'Failed to load the purchase queue.'));
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);

  const confirmIgnore = useCallback(async () => {
    if (!ignoreTarget) return;
    setIgnoring(true);
    setError(null);
    try {
      await PurchaseService.ignoreVoucher(ignoreTarget.id);
      setNotice(`Purchase ${ignoreTarget.label} was removed from the queue.`);
      setIgnoreTarget(null);
      setDetail(null);
      await loadQueue();
    } catch (err) {
      setError(parseApiError(err, 'Failed to ignore the purchase voucher.'));
    } finally {
      setIgnoring(false);
    }
  }, [ignoreTarget, loadQueue]);

  const runBackfill = useCallback(async () => {
    if (!backfillFrom) return;
    setBackfilling(true);
    setError(null);
    setNotice(null);
    try {
      const result = await PurchaseService.backfill(backfillFrom);
      setNotice(
        `Fetched ${result.fetched} purchase invoice(s) since ${result.from_date} — ${result.new} new added to the queue.`,
      );
      setBackfillOpen(false);
      await loadQueue();
    } catch (err) {
      setError(parseApiError(err, 'Failed to fetch older purchases from Tally.'));
    } finally {
      setBackfilling(false);
    }
  }, [backfillFrom, loadQueue]);

  const openDetail = useCallback(async (voucherId: number) => {
    setDetailLoading(true);
    setError(null);
    try {
      const data = await PurchaseService.getVoucher(voucherId);
      setDetail(data);
    } catch (err) {
      setError(parseApiError(err, 'Failed to load voucher detail.'));
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const refreshDetail = useCallback(async () => {
    if (detail) await openDetail(detail.id);
    await loadQueue();
  }, [detail, openDetail, loadQueue]);

  const ignoreDialog = ignoreTarget ? (
    <div
      className="cat-dialog-overlay"
      role="presentation"
      onClick={() => !ignoring && setIgnoreTarget(null)}
    >
      <div
        className="cat-dialog animate-slide-in"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="cat-dialog__header">
          <h2 className="cat-dialog__title">Ignore this purchase invoice?</h2>
          <button
            type="button"
            className="app-toolbar-icon-btn"
            onClick={() => setIgnoreTarget(null)}
            aria-label="Close"
            disabled={ignoring}
          >
            <X size={16} />
          </button>
        </header>
        <div className="cat-dialog__body">
          <div className="alert alert-danger" style={{ marginBottom: 12 }}>
            <AlertCircle size={14} aria-hidden />
            <span>
              Purchase <strong>{ignoreTarget.label}</strong> will be removed from the queue and will{' '}
              <strong>not</strong> be fetched again on future Tally syncs. Any inventory you already
              imported from it is kept. This does not change anything in Tally.
            </span>
          </div>
          <p style={{ margin: 0, color: 'var(--color-text-tertiary)', fontSize: 13 }}>
            You can bring it back later by fetching older purchases for its date.
          </p>
        </div>
        <footer className="cat-dialog__footer">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setIgnoreTarget(null)}
            disabled={ignoring}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => void confirmIgnore()}
            disabled={ignoring}
          >
            {ignoring ? 'Removing…' : 'Ignore and remove'}
          </button>
        </footer>
      </div>
    </div>
  ) : null;

  // ---- Voucher detail view ----
  if (detail) {
    return (
      <div className="animate-fade-in" style={{ padding: 24, display: 'grid', gap: 16 }}>
        <header style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setDetail(null)}>
            <ArrowLeft size={14} aria-hidden /> Back to queue
          </button>
          <div style={{ flex: 1 }}>
            <h1 style={{ margin: 0 }}>Purchase {detail.voucher_number}</h1>
            <p style={{ margin: 0, color: 'var(--color-text-tertiary)', fontSize: 13 }}>
              Supplier {detail.supplier_name ?? '—'} · Invoice {detail.invoice_number ?? '—'} ·{' '}
              {detail.voucher_date ?? '—'} · <StatusBadge status={detail.status} />
            </p>
          </div>
          {canImport && detail.status !== 'imported' && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              style={{ color: 'var(--color-danger, #c0392b)' }}
              onClick={() => setIgnoreTarget({ id: detail.id, label: detail.voucher_number })}
            >
              <Ban size={14} aria-hidden /> Ignore invoice
            </button>
          )}
        </header>

        <div className="card">
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
              gap: 12,
            }}
          >
            <Metric label="Reference no." value={detail.reference_number ?? '—'} />
            <Metric label="Voucher GUID" value={detail.voucher_guid} mono />
            <Metric label="CGST" value={money(detail.taxes.cgst_amount)} />
            <Metric label="SGST" value={money(detail.taxes.sgst_amount)} />
            <Metric label="IGST" value={money(detail.taxes.igst_amount)} />
            <Metric label="Cess" value={money(detail.taxes.cess_amount)} />
            <Metric label="Invoice total" value={money(detail.grand_total)} />
          </div>
        </div>

        {error && (
          <div className="alert alert-danger">
            <AlertCircle size={14} aria-hidden />
            <span>{error}</span>
          </div>
        )}

        <div style={{ display: 'grid', gap: 12 }}>
          {detail.groups.map((group) => (
            <div key={group.group_key} className="card">
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  gap: 12,
                }}
              >
                <div>
                  <h3 style={{ margin: 0 }}>{group.stock_item_name}</h3>
                  <p style={{ margin: '4px 0', color: 'var(--color-text-tertiary)', fontSize: 13 }}>
                    Quantity {group.quantity} · {group.serials.length} serial(s)
                    {group.duplicate_count > 0 ? ` · ${group.duplicate_count} duplicate(s)` : ''}
                  </p>
                </div>
                {group.imported ? (
                  <span className="badge badge-success">Imported</span>
                ) : canImport ? (
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => setImportGroup(group)}
                  >
                    Import
                  </button>
                ) : (
                  <span className="badge" title="Requires the “Import to inventory” permission">
                    View only
                  </span>
                )}
              </div>
              {group.serials.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                  {group.serials.map((cell) => (
                    <span
                      key={cell.serial_number}
                      className={cell.is_duplicate ? 'badge badge-warning' : 'badge'}
                      title={
                        cell.is_duplicate
                          ? `Already in IMS (${cell.existing_status ?? 'exists'})`
                          : undefined
                      }
                      style={{ fontFamily: 'var(--font-mono)' }}
                    >
                      {cell.serial_number}
                    </span>
                  ))}
                </div>
              )}
              {group.serials.length === 0 && (
                <p style={{ color: 'var(--color-text-tertiary)', fontSize: 13, marginTop: 8 }}>
                  No serials on the invoice line — add them during import.
                </p>
              )}
            </div>
          ))}
        </div>

        {importGroup && (
          <PurchaseImportDialog
            open
            voucher={detail}
            group={importGroup}
            onClose={() => setImportGroup(null)}
            onImported={() => {
              setImportGroup(null);
              void refreshDetail();
            }}
          />
        )}
        {ignoreDialog}
      </div>
    );
  }

  // ---- Queue list view ----
  return (
    <div className="animate-fade-in" style={{ padding: 24, display: 'grid', gap: 16 }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <WorkspacePageBack />
        <div style={{ flex: 1 }}>
          <h1 style={{ margin: 0 }}>Purchase</h1>
          <p style={{ margin: 0, color: 'var(--color-text-tertiary)', fontSize: 13 }}>
            Tally purchase vouchers awaiting review. Import stock into inventory after approval —
            nothing is added automatically.
          </p>
        </div>
        {canView && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setBackfillOpen((open) => !open)}
          >
            <CalendarClock size={14} aria-hidden /> Fetch older purchases
          </button>
        )}
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void loadQueue()}>
          <RefreshCw size={14} aria-hidden /> Refresh
        </button>
      </header>

      {backfillOpen && (
        <div className="card" style={{ display: 'grid', gap: 10 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 15 }}>Fetch older purchase invoices</h3>
            <p style={{ margin: '4px 0 0', color: 'var(--color-text-tertiary)', fontSize: 13 }}>
              Read-only. Pulls Purchase invoices from Tally starting at the date you pick (up to
              today) into this queue. Nothing is imported automatically and Tally is never modified.
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
              {backfilling ? 'Fetching…' : 'Fetch from Tally'}
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

      {notice && (
        <div className="alert alert-success">
          <span>{notice}</span>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        {(['', 'pending', 'partially_imported', 'imported'] as StatusFilter[]).map((value) => (
          <button
            key={value || 'all'}
            type="button"
            className={statusFilter === value ? 'btn btn-secondary btn-sm' : 'btn btn-ghost btn-sm'}
            onClick={() => setStatusFilter(value)}
          >
            {value ? STATUS_LABELS[value] : 'All'}
          </button>
        ))}
      </div>

      {error && (
        <div className="alert alert-danger">
          <AlertCircle size={14} aria-hidden />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="table-root">
          <thead>
            <tr>
              <th>Supplier</th>
              <th>Date</th>
              <th>Voucher no.</th>
              <th>Invoice no.</th>
              <th>Reference</th>
              <th className="col-amount">Total</th>
              <th className="col-amount">Tax (C/S/I)</th>
              <th>Groups</th>
              <th>Status</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={10} style={{ textAlign: 'center', padding: 24 }}>
                  Loading purchase queue…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={10} style={{ textAlign: 'center', padding: 24 }}>
                  No purchase vouchers in the queue yet. They appear automatically after a Tally
                  sync.
                </td>
              </tr>
            )}
            {!loading &&
              items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => void openDetail(item.id)}
                  style={{ cursor: 'pointer' }}
                >
                  <td>{item.supplier_name ?? '—'}</td>
                  <td>{item.voucher_date ?? '—'}</td>
                  <td className="col-mono">{item.voucher_number}</td>
                  <td className="col-mono">{item.invoice_number ?? '—'}</td>
                  <td className="col-mono">{item.reference_number ?? '—'}</td>
                  <td className="col-amount">{money(item.grand_total)}</td>
                  <td className="col-amount">
                    {money(item.taxes.cgst_amount)} / {money(item.taxes.sgst_amount)} /{' '}
                    {money(item.taxes.igst_amount)}
                  </td>
                  <td>
                    {item.imported_group_count}/{item.group_count}
                  </td>
                  <td>
                    <StatusBadge status={item.status} />
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {canImport && item.status !== 'imported' && (
                      <button
                        type="button"
                        className="app-toolbar-icon-btn"
                        aria-label={`Ignore purchase ${item.voucher_number}`}
                        title="Ignore this purchase invoice"
                        onClick={(e) => {
                          e.stopPropagation();
                          setIgnoreTarget({ id: item.id, label: item.voucher_number });
                        }}
                      >
                        <Ban size={14} aria-hidden />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {detailLoading && <p style={{ color: 'var(--color-text-tertiary)' }}>Opening voucher…</p>}
      {ignoreDialog}
    </div>
  );
}

function Metric({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}): JSX.Element {
  return (
    <div>
      <p style={{ margin: 0, fontSize: 11, color: 'var(--color-text-tertiary)' }}>{label}</p>
      <p
        style={{
          margin: 0,
          fontSize: 13,
          fontWeight: 500,
          fontFamily: mono ? 'var(--font-mono)' : undefined,
          wordBreak: mono ? 'break-all' : undefined,
        }}
      >
        {value}
      </p>
    </div>
  );
}
