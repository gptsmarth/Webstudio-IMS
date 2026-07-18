import { X } from 'lucide-react';

export interface PurchaseImportSummary {
  supplier: string;
  brand: string;
  model: string;
  existingModel: boolean;
  quantity: number;
  serialCount: number;
  /** Serials already present in IMS — skipped at import, never re-created. */
  alreadyAddedCount: number;
  destination: string;
  location: string;
  purchasePrice: string;
}

interface Props {
  open: boolean;
  loading: boolean;
  summary: PurchaseImportSummary;
  error?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

function Row({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="inv-dialog__grid" style={{ gridTemplateColumns: '160px 1fr', gap: 8 }}>
      <span style={{ color: 'var(--color-text-tertiary)', fontSize: 12 }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 500 }}>{value}</span>
    </div>
  );
}

export function ConfirmPurchaseImportDialog({
  open,
  loading,
  summary,
  error,
  onCancel,
  onConfirm,
}: Props): JSX.Element | null {
  if (!open) return null;
  return (
    <div className="inv-dialog-overlay" role="presentation" onClick={onCancel}>
      <div
        className="inv-dialog animate-slide-in"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-purchase-import-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="inv-dialog__header">
          <div>
            <h2 id="confirm-purchase-import-title" className="inv-dialog__title">
              Confirm import
            </h2>
            <p className="inv-dialog__lead">
              Review before inventory is created. This runs in a single transaction.
            </p>
          </div>
          <button
            type="button"
            className="app-toolbar-icon-btn"
            onClick={onCancel}
            aria-label="Close"
          >
            <X size={16} aria-hidden />
          </button>
        </header>
        <div className="inv-dialog__body" style={{ display: 'grid', gap: 6 }}>
          <Row label="Supplier" value={summary.supplier || '—'} />
          <Row label="Brand" value={summary.brand} />
          <Row label="Model" value={summary.model} />
          <Row label="Existing model" value={summary.existingModel ? 'YES' : 'NO'} />
          <Row label="New units to import" value={String(summary.quantity)} />
          <Row label="Serial count" value={String(summary.serialCount)} />
          <Row
            label="Already added"
            value={summary.alreadyAddedCount > 0 ? `${summary.alreadyAddedCount} (skipped)` : '0'}
          />
          <Row label="Inventory destination" value={summary.destination} />
          <Row label="Location" value={summary.location} />
          <Row label="Purchase price" value={summary.purchasePrice} />
          {error && <p className="inv-dialog__error">{error}</p>}
        </div>
        <footer className="inv-dialog__footer">
          <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={loading}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onConfirm}
            disabled={loading || summary.serialCount === 0}
          >
            {loading ? 'Importing…' : 'Confirm import'}
          </button>
        </footer>
      </div>
    </div>
  );
}
