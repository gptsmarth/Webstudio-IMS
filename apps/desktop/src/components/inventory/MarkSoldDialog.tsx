import { useState } from 'react';
import { X } from 'lucide-react';
import type { MarkSoldRequest } from '../../services/api/InventoryService';

interface MarkSoldDialogProps {
  open: boolean;
  serialNumber: string;
  loading: boolean;
  onClose: () => void;
  onConfirm: (payload: MarkSoldRequest) => Promise<void>;
}

const PAYMENT_MODES = ['Cash', 'Card', 'UPI', 'Bank Transfer', 'Finance'];

export function MarkSoldDialog({
  open,
  serialNumber,
  loading,
  onClose,
  onConfirm,
}: MarkSoldDialogProps): JSX.Element | null {
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [paymentMode, setPaymentMode] = useState(PAYMENT_MODES[0]);
  const [saleDate, setSaleDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [saleAmount, setSaleAmount] = useState('');
  const [remarks, setRemarks] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const submit = async () => {
    if (!invoiceNumber.trim() || !customerName.trim()) {
      setError('Invoice number and customer name are required.');
      return;
    }
    setError(null);
    try {
      await onConfirm({
        invoice_number: invoiceNumber.trim(),
        customer_name: customerName.trim(),
        payment_mode: paymentMode,
        sale_date: saleDate,
        sale_amount: saleAmount.trim() ? Number(saleAmount) : null,
        remarks: remarks.trim() || null,
      });
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to mark item as sold.');
    }
  };

  return (
    <div className="inv-dialog-overlay" role="presentation" onClick={onClose}>
      <div
        className="inv-dialog animate-slide-in"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mark-sold-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="inv-dialog__header">
          <div>
            <h2 id="mark-sold-dialog-title" className="inv-dialog__title">
              Mark as sold
            </h2>
            <p className="inv-dialog__subtitle col-mono">{serialNumber}</p>
          </div>
          <button type="button" className="app-toolbar-icon-btn" onClick={onClose} aria-label="Close">
            <X size={16} aria-hidden />
          </button>
        </header>

        <div className="inv-dialog__body inv-dialog__form-grid">
          <label className="inv-filters__field">
            <span className="inv-filters__label">Invoice number</span>
            <input className="input" value={invoiceNumber} onChange={(event) => setInvoiceNumber(event.target.value)} />
          </label>
          <label className="inv-filters__field">
            <span className="inv-filters__label">Customer name</span>
            <input className="input" value={customerName} onChange={(event) => setCustomerName(event.target.value)} />
          </label>
          <label className="inv-filters__field">
            <span className="inv-filters__label">Payment mode</span>
            <select className="input" value={paymentMode} onChange={(event) => setPaymentMode(event.target.value)}>
              {PAYMENT_MODES.map((mode) => (
                <option key={mode} value={mode}>
                  {mode}
                </option>
              ))}
            </select>
          </label>
          <label className="inv-filters__field">
            <span className="inv-filters__label">Sale date</span>
            <input type="date" className="input" value={saleDate} onChange={(event) => setSaleDate(event.target.value)} />
          </label>
          <label className="inv-filters__field">
            <span className="inv-filters__label">Sale amount (₹)</span>
            <input
              type="number"
              min="0"
              step="1"
              className="input"
              value={saleAmount}
              onChange={(event) => setSaleAmount(event.target.value)}
              placeholder="Optional"
            />
          </label>
          <label className="inv-filters__field inv-dialog__field-full">
            <span className="inv-filters__label">Remarks</span>
            <textarea className="input inv-dialog__textarea" rows={3} value={remarks} onChange={(event) => setRemarks(event.target.value)} />
          </label>
          {error && <p className="inv-dialog__error inv-dialog__field-full">{error}</p>}
        </div>

        <footer className="inv-dialog__footer">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => void submit()} disabled={loading}>
            {loading ? 'Saving…' : 'Confirm sale'}
          </button>
        </footer>
      </div>
    </div>
  );
}
