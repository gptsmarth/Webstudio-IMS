import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, ArrowLeft, RefreshCw } from 'lucide-react';
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

export function PurchasePage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const canImport = session?.permissions?.includes(P.purchase.import) ?? false;
  const [items, setItems] = useState<PurchaseQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const [detail, setDetail] = useState<PurchaseVoucherDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [importGroup, setImportGroup] = useState<PurchaseModelGroup | null>(null);

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

  // ---- Voucher detail view ----
  if (detail) {
    return (
      <div className="animate-fade-in" style={{ padding: 24, display: 'grid', gap: 16 }}>
        <header style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setDetail(null)}>
            <ArrowLeft size={14} aria-hidden /> Back to queue
          </button>
          <div>
            <h1 style={{ margin: 0 }}>Purchase {detail.voucher_number}</h1>
            <p style={{ margin: 0, color: 'var(--color-text-tertiary)', fontSize: 13 }}>
              Supplier {detail.supplier_name ?? '—'} · Invoice {detail.invoice_number ?? '—'} ·{' '}
              {detail.voucher_date ?? '—'} · <StatusBadge status={detail.status} />
            </p>
          </div>
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
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void loadQueue()}>
          <RefreshCw size={14} aria-hidden /> Refresh
        </button>
      </header>

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
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: 24 }}>
                  Loading purchase queue…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: 24 }}>
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
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {detailLoading && <p style={{ color: 'var(--color-text-tertiary)' }}>Opening voucher…</p>}
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
