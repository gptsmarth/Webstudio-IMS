import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import type { SaleListItem } from '../../services/api/SalesService';

interface SaleCancelDialogProps {
  open: boolean;
  sale: SaleListItem | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: (reason: string | null) => Promise<void>;
}

export function SaleCancelDialog({
  open,
  sale,
  loading,
  onClose,
  onConfirm,
}: SaleCancelDialogProps): JSX.Element | null {
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setReason('');
    setError(null);
  }, [open, sale?.id]);

  if (!open || !sale) return null;

  const submit = async () => {
    setError(null);
    try {
      await onConfirm(reason.trim() || null);
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to delete invoice.');
    }
  };

  return (
    <div className="cat-dialog-overlay" role="presentation" onClick={onClose}>
      <div
        className="cat-dialog animate-slide-in"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sale-cancel-dialog-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="cat-dialog__header">
          <h2 id="sale-cancel-dialog-title" className="cat-dialog__title">
            Delete invoice
          </h2>
          <button
            type="button"
            className="app-toolbar-icon-btn"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </header>
        <div className="cat-dialog__body">
          <p>
            This will delete invoice <strong>{sale.invoice_number}</strong> and return serial{' '}
            <strong className="col-mono">{sale.serial_number}</strong> ({sale.model_number}) to
            available stock. This action cannot be undone.
          </p>
          <label className="cat-dialog__field">
            <span>Reason (optional)</span>
            <textarea
              className="input"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={loading}
              placeholder="Customer return, wrong invoice, etc."
            />
          </label>
          {error && <div className="alert alert-danger">{error}</div>}
        </div>
        <footer className="cat-dialog__footer">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button type="button" className="btn btn-danger" onClick={() => void submit()} disabled={loading}>
            {loading ? 'Deleting…' : 'Delete invoice'}
          </button>
        </footer>
      </div>
    </div>
  );
}
