import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  AlertCircle,
  ArrowLeft,
  Ban,
  CalendarClock,
  CheckCircle2,
  RefreshCw,
  X,
} from 'lucide-react';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';
import { PurchaseImportDialog } from '../../components/purchase/PurchaseImportDialog';
import { parseApiError } from '../../lib/apiError';
import { P } from '../../services/PermissionService';
import { useAuthStore } from '../../store';
import { TallyService } from '../../services/api/TallyService';
import {
  PurchaseService,
  type PurchaseModelGroup,
  type PurchaseQueueItem,
  type PurchaseVoucherDetail,
} from '../../services/api/PurchaseService';

type StatusFilter = '' | 'pending' | 'partially_imported' | 'imported' | 'ignored';

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  partially_imported: 'Partially imported',
  imported: 'Imported',
  ignored: 'Ignored',
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
        : status === 'ignored'
          ? 'badge badge-neutral'
          : 'badge';
  return <span className={cls}>{STATUS_LABELS[status] ?? status}</span>;
}

function defaultBackfillFrom(): string {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() - 3, 1);
  return start.toISOString().slice(0, 10);
}

/** Recent window for Purchase "Sync now" — Register-first backfill, not Day Book-only. */
function recentPurchaseSyncFrom(): string {
  const start = new Date();
  start.setDate(start.getDate() - 14);
  return start.toISOString().slice(0, 10);
}

export function PurchasePage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const canImport = session?.permissions?.includes(P.purchase.import) ?? false;
  const canView = session?.permissions?.includes(P.purchase.view) ?? false;
  const canSyncTally = session?.permissions?.includes(P.tally.runSync) ?? false;
  const [items, setItems] = useState<PurchaseQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const [detail, setDetail] = useState<PurchaseVoucherDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [importGroup, setImportGroup] = useState<PurchaseModelGroup | null>(null);
  const [ignoreTarget, setIgnoreTarget] = useState<{ id: number; label: string } | null>(null);
  const [ignoring, setIgnoring] = useState(false);
  const [closeTarget, setCloseTarget] = useState<{
    id: number;
    label: string;
    skipped: number;
    total: number;
  } | null>(null);
  const [closing, setClosing] = useState(false);
  const [backfillOpen, setBackfillOpen] = useState(false);
  const [backfillFrom, setBackfillFrom] = useState<string>(defaultBackfillFrom());
  const [backfillTo, setBackfillTo] = useState<string>('');
  const [backfilling, setBackfilling] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [refreshingVoucher, setRefreshingVoucher] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkConfirm, setBulkConfirm] = useState<'ignore' | 'import' | null>(null);
  const [bulkRunning, setBulkRunning] = useState(false);

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

  useEffect(() => {
    setSelectedIds(new Set());
  }, [statusFilter]);

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

  const confirmClose = useCallback(async () => {
    if (!closeTarget) return;
    setClosing(true);
    setError(null);
    try {
      await PurchaseService.markImported(closeTarget.id);
      setNotice(`Purchase ${closeTarget.label} was marked imported.`);
      setCloseTarget(null);
      setDetail(null);
      await loadQueue();
    } catch (err) {
      setError(parseApiError(err, 'Failed to mark the purchase voucher imported.'));
    } finally {
      setClosing(false);
    }
  }, [closeTarget, loadQueue]);

  const confirmBulkAction = useCallback(async () => {
    if (!bulkConfirm || selectedIds.size === 0) return;
    setBulkRunning(true);
    setError(null);
    const ids = Array.from(selectedIds);
    const action =
      bulkConfirm === 'ignore' ? PurchaseService.ignoreVoucher : PurchaseService.markImported;
    const results = await Promise.allSettled(ids.map((id) => action(id)));
    const succeeded = results.filter((r) => r.status === 'fulfilled').length;
    const failed = results.length - succeeded;
    const verb = bulkConfirm === 'ignore' ? 'ignored' : 'marked imported';
    setNotice(
      failed === 0
        ? `${succeeded} purchase(s) ${verb}.`
        : `${succeeded} purchase(s) ${verb}, ${failed} failed — they may already be imported or ignored.`,
    );
    setBulkConfirm(null);
    setSelectedIds(new Set());
    setBulkRunning(false);
    await loadQueue();
  }, [bulkConfirm, selectedIds, loadQueue]);

  const runBackfill = useCallback(async () => {
    if (!backfillFrom) return;
    setBackfilling(true);
    setError(null);
    setNotice(null);
    try {
      const result = await PurchaseService.backfill(backfillFrom, backfillTo || undefined);
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
  }, [backfillFrom, backfillTo, loadQueue]);

  const runSyncNow = useCallback(async () => {
    setSyncing(true);
    setError(null);
    setNotice(null);
    try {
      // Use the same Register-first path as "Fetch older" for a recent window.
      // Full Tally Sync Now often misses purchases when Day Book omits them and
      // Voucher Register fails silently.
      const from = recentPurchaseSyncFrom();
      const result = await PurchaseService.backfill(from);
      setNotice(
        `Fetched ${result.fetched} purchase invoice(s) since ${result.from_date} — ${result.new} new added to the queue.`,
      );
      await loadQueue();
      // Keep sales sync moving in the background when permitted.
      if (canSyncTally) {
        void TallyService.triggerSync().catch(() => undefined);
      }
    } catch (err) {
      setError(parseApiError(err, 'Failed to fetch the latest purchases from Tally.'));
    } finally {
      setSyncing(false);
    }
  }, [canSyncTally, loadQueue]);

  // Purchase's list and detail views are two full return branches of the same
  // component, not separately-mounted panes — the shared `.app-content` scroll
  // container's height shrinks to fit the (usually shorter) detail view, which
  // clamps its scrollTop, and nothing restores it when coming back to the list.
  // Save/restore that scroll position manually around the list<->detail toggle.
  const listScrollTopRef = useRef(0);
  const returningFromDetailRef = useRef(false);

  const openDetail = useCallback(async (voucherId: number) => {
    const mainEl = document.getElementById('main-content');
    if (mainEl) listScrollTopRef.current = mainEl.scrollTop;
    setDetailLoading(true);
    setError(null);
    try {
      const data = await PurchaseService.getVoucher(voucherId);
      setDetail(data);
      returningFromDetailRef.current = true;
    } catch (err) {
      setError(parseApiError(err, 'Failed to load voucher detail.'));
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useLayoutEffect(() => {
    if (detail !== null || !returningFromDetailRef.current) return;
    returningFromDetailRef.current = false;
    const mainEl = document.getElementById('main-content');
    if (!mainEl) return;
    const target = listScrollTopRef.current;
    let attempts = 0;
    const tryRestore = () => {
      mainEl.scrollTop = target;
      attempts += 1;
      if (Math.abs(mainEl.scrollTop - target) > 1 && attempts < 6) {
        requestAnimationFrame(tryRestore);
      }
    };
    tryRestore();
  }, [detail]);

  const refreshFromTally = useCallback(async () => {
    if (!detail) return;
    setRefreshingVoucher(true);
    setError(null);
    setNotice(null);
    try {
      await PurchaseService.refreshVoucher(detail.id);
      setNotice(`Purchase ${detail.voucher_number} was refreshed from Tally.`);
      await openDetail(detail.id);
      await loadQueue();
    } catch (err) {
      setError(parseApiError(err, 'Failed to refresh this purchase from Tally.'));
    } finally {
      setRefreshingVoucher(false);
    }
  }, [detail, loadQueue, openDetail]);

  const refreshDetail = useCallback(async () => {
    if (detail) await openDetail(detail.id);
    await loadQueue();
  }, [detail, openDetail, loadQueue]);

  const ignoreDialog = ignoreTarget
    ? createPortal(
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
                  Purchase <strong>{ignoreTarget.label}</strong> will be removed from the queue and
                  will <strong>not</strong> be fetched again on future Tally syncs. Any inventory
                  you already imported from it is kept. This does not change anything in Tally.
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
        </div>,
        document.body,
      )
    : null;

  const closeDialog = closeTarget
    ? createPortal(
        <div
          className="cat-dialog-overlay"
          role="presentation"
          onClick={() => !closing && setCloseTarget(null)}
        >
          <div
            className="cat-dialog animate-slide-in"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="cat-dialog__header">
              <h2 className="cat-dialog__title">Mark this purchase invoice as imported?</h2>
              <button
                type="button"
                className="app-toolbar-icon-btn"
                onClick={() => setCloseTarget(null)}
                aria-label="Close"
                disabled={closing}
              >
                <X size={16} />
              </button>
            </header>
            <div className="cat-dialog__body">
              <div className="alert alert-danger" style={{ marginBottom: 12 }}>
                <AlertCircle size={14} aria-hidden />
                <span>
                  Purchase <strong>{closeTarget.label}</strong> will move to Imported. This is
                  permanent —{' '}
                  <strong>
                    {closeTarget.skipped} of {closeTarget.total} line(s)
                  </strong>{' '}
                  you haven&apos;t added to inventory will be left out and can&apos;t be imported
                  from this invoice later.
                </span>
              </div>
            </div>
            <footer className="cat-dialog__footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setCloseTarget(null)}
                disabled={closing}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={() => void confirmClose()}
                disabled={closing}
              >
                {closing ? 'Marking…' : 'Mark as imported'}
              </button>
            </footer>
          </div>
        </div>,
        document.body,
      )
    : null;

  const bulkDialog = bulkConfirm
    ? createPortal(
        <div
          className="cat-dialog-overlay"
          role="presentation"
          onClick={() => !bulkRunning && setBulkConfirm(null)}
        >
          <div
            className="cat-dialog animate-slide-in"
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="cat-dialog__header">
              <h2 className="cat-dialog__title">
                {bulkConfirm === 'ignore'
                  ? `Ignore ${selectedIds.size} purchase invoice(s)?`
                  : `Mark ${selectedIds.size} purchase invoice(s) as imported?`}
              </h2>
              <button
                type="button"
                className="app-toolbar-icon-btn"
                onClick={() => setBulkConfirm(null)}
                aria-label="Close"
                disabled={bulkRunning}
              >
                <X size={16} />
              </button>
            </header>
            <div className="cat-dialog__body">
              <div className="alert alert-danger" style={{ marginBottom: 12 }}>
                <AlertCircle size={14} aria-hidden />
                <span>
                  {bulkConfirm === 'ignore' ? (
                    <>
                      These invoices will be removed from the queue and won&apos;t be fetched again
                      on future Tally syncs. Any inventory already imported from them is kept.
                    </>
                  ) : (
                    <>
                      These invoices will move to Imported, permanently. Any line(s) not yet added
                      to inventory will be left out and can&apos;t be imported later.
                    </>
                  )}
                </span>
              </div>
            </div>
            <footer className="cat-dialog__footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setBulkConfirm(null)}
                disabled={bulkRunning}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={() => void confirmBulkAction()}
                disabled={bulkRunning}
              >
                {bulkRunning
                  ? 'Working…'
                  : bulkConfirm === 'ignore'
                    ? 'Ignore and remove'
                    : 'Mark as imported'}
              </button>
            </footer>
          </div>
        </div>,
        document.body,
      )
    : null;

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
            {detail.status === 'ignored' && (
              <p style={{ margin: '4px 0 0', color: 'var(--color-text-tertiary)', fontSize: 12 }}>
                Ignored invoices stay hidden from the queue. To bring this one back, fetch older
                purchases from Tally for its date.
              </p>
            )}
          </div>
          {canImport && detail.status !== 'imported' && detail.status !== 'ignored' && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() =>
                setCloseTarget({
                  id: detail.id,
                  label: detail.voucher_number,
                  skipped: detail.groups.filter((g) => !g.imported).length,
                  total: detail.groups.length,
                })
              }
            >
              Mark as imported
            </button>
          )}
          {canImport && detail.status !== 'imported' && detail.status !== 'ignored' && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              style={{ color: 'var(--color-danger, #c0392b)' }}
              onClick={() => setIgnoreTarget({ id: detail.id, label: detail.voucher_number })}
            >
              <Ban size={14} aria-hidden /> Ignore invoice
            </button>
          )}
          {canView && detail.status !== 'imported' && detail.status !== 'ignored' && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => void refreshFromTally()}
              disabled={refreshingVoucher}
              title="Re-read this invoice from Tally to fix quantity or serials before import"
            >
              <RefreshCw
                size={14}
                aria-hidden
                className={refreshingVoucher ? 'stg-spin' : undefined}
              />{' '}
              {refreshingVoucher ? 'Refreshing…' : 'Refresh from Tally'}
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

        {notice && (
          <div className="alert alert-success">
            <span>{notice}</span>
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
                    {group.duplicate_count > 0 ? ` · ${group.duplicate_count} already added` : ''}
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
                          ? `Already added in IMS (${cell.existing_status ?? 'exists'}) — will be skipped on import`
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
        {closeDialog}
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
        {canView && (
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => void runSyncNow()}
            disabled={syncing}
            title="Pull recent purchase invoices from Tally (last 14 days)"
          >
            <RefreshCw size={14} aria-hidden className={syncing ? 'stg-spin' : undefined} />{' '}
            {syncing ? 'Syncing…' : 'Sync now'}
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
              Read-only. Pulls Purchase invoices from Tally in the date range you pick (to date
              defaults to today) into this queue. Nothing is imported automatically and Tally is
              never modified.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <label style={{ display: 'grid', gap: 4, fontSize: 12 }}>
              <span style={{ color: 'var(--color-text-tertiary)' }}>From date</span>
              <input
                type="date"
                className="input"
                value={backfillFrom}
                max={backfillTo || new Date().toISOString().slice(0, 10)}
                onChange={(e) => setBackfillFrom(e.target.value)}
                disabled={backfilling}
              />
            </label>
            <label style={{ display: 'grid', gap: 4, fontSize: 12 }}>
              <span style={{ color: 'var(--color-text-tertiary)' }}>To date (optional)</span>
              <input
                type="date"
                className="input"
                value={backfillTo}
                min={backfillFrom}
                max={new Date().toISOString().slice(0, 10)}
                onChange={(e) => setBackfillTo(e.target.value)}
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
        {(['', 'pending', 'partially_imported', 'imported', 'ignored'] as StatusFilter[]).map(
          (value) => (
            <button
              key={value || 'all'}
              type="button"
              className={
                statusFilter === value ? 'btn btn-secondary btn-sm' : 'btn btn-ghost btn-sm'
              }
              onClick={() => setStatusFilter(value)}
            >
              {value ? STATUS_LABELS[value] : 'All'}
            </button>
          ),
        )}
      </div>

      {error && (
        <div className="alert alert-danger">
          <AlertCircle size={14} aria-hidden />
          <span>{error}</span>
        </div>
      )}

      {canImport && selectedIds.size > 0 && (
        <div
          className="card"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 16px',
          }}
        >
          <span style={{ fontSize: 13 }}>{selectedIds.size} selected</span>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setBulkConfirm('import')}
          >
            Mark as imported
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            style={{ color: 'var(--color-danger, #c0392b)' }}
            onClick={() => setBulkConfirm('ignore')}
          >
            Ignore
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setSelectedIds(new Set())}
          >
            Clear selection
          </button>
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="table-root">
          <thead>
            <tr>
              {canImport && (
                <th style={{ width: 32 }}>
                  <input
                    type="checkbox"
                    aria-label="Select all actionable purchases"
                    checked={
                      items.some(
                        (item) => item.status === 'pending' || item.status === 'partially_imported',
                      ) &&
                      items
                        .filter(
                          (item) =>
                            item.status === 'pending' || item.status === 'partially_imported',
                        )
                        .every((item) => selectedIds.has(item.id))
                    }
                    onChange={(e) => {
                      const selectable = items.filter(
                        (item) => item.status === 'pending' || item.status === 'partially_imported',
                      );
                      setSelectedIds(
                        e.target.checked ? new Set(selectable.map((item) => item.id)) : new Set(),
                      );
                    }}
                  />
                </th>
              )}
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
                <td colSpan={canImport ? 11 : 10} style={{ textAlign: 'center', padding: 24 }}>
                  Loading purchase queue…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={canImport ? 11 : 10} style={{ textAlign: 'center', padding: 24 }}>
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
                  {canImport && (
                    <td onClick={(e) => e.stopPropagation()}>
                      {(item.status === 'pending' || item.status === 'partially_imported') && (
                        <input
                          type="checkbox"
                          aria-label={`Select purchase ${item.voucher_number}`}
                          checked={selectedIds.has(item.id)}
                          onChange={(e) => {
                            setSelectedIds((prev) => {
                              const next = new Set(prev);
                              if (e.target.checked) next.add(item.id);
                              else next.delete(item.id);
                              return next;
                            });
                          }}
                        />
                      )}
                    </td>
                  )}
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
                    {canImport && item.status !== 'imported' && item.status !== 'ignored' && (
                      <button
                        type="button"
                        className="app-toolbar-icon-btn"
                        aria-label={`Mark purchase ${item.voucher_number} as imported`}
                        title="Mark as imported"
                        onClick={(e) => {
                          e.stopPropagation();
                          setCloseTarget({
                            id: item.id,
                            label: item.voucher_number,
                            skipped: item.pending_group_count,
                            total: item.group_count,
                          });
                        }}
                      >
                        <CheckCircle2 size={14} aria-hidden />
                      </button>
                    )}
                    {canImport && item.status !== 'imported' && item.status !== 'ignored' && (
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
      {closeDialog}
      {bulkDialog}
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
