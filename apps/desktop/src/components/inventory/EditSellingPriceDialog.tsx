import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { formatInventoryPrice, parsePriceInput } from '../../lib/inventoryPrice';

interface EditSellingPriceDialogProps {
  open: boolean;
  serialNumber: string;
  currentPrice: number | null | undefined;
  loading: boolean;
  onClose: () => void;
  onConfirm: (sellingPrice: number | null) => Promise<void>;
}

export function EditSellingPriceDialog({
  open,
  serialNumber,
  currentPrice,
  loading,
  onClose,
  onConfirm,
}: EditSellingPriceDialogProps): JSX.Element | null {
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setValue(currentPrice != null ? String(currentPrice) : '');
    setError(null);
  }, [open, currentPrice]);

  if (!open) return null;

  const submit = async () => {
    const parsed = parsePriceInput(value);
    if (value.trim() && parsed === null) {
      setError('Enter a valid amount or leave blank to clear.');
      return;
    }
    setError(null);
    try {
      await onConfirm(parsed);
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Could not update selling price.');
    }
  };

  return (
    <div className="inv-dialog-overlay" role="presentation" onClick={onClose}>
      <div
        className="inv-dialog animate-slide-in"
        role="dialog"
        aria-modal="true"
        aria-labelledby="selling-price-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="inv-dialog__header">
          <h2 id="selling-price-dialog-title" className="inv-dialog__title">Edit selling price</h2>
          <button type="button" className="app-toolbar-icon-btn" onClick={onClose} aria-label="Close">
            <X size={16} aria-hidden />
          </button>
        </header>
        <div className="inv-dialog__body">
          <p className="inv-dialog__hint col-mono">{serialNumber}</p>
          <label className="inv-filters__field">
            <span className="inv-filters__label">Selling price (INR)</span>
            <input
              className="input"
              type="text"
              inputMode="decimal"
              value={value}
              onChange={(event) => setValue(event.target.value)}
              placeholder="e.g. 54999"
            />
          </label>
          {currentPrice != null && (
            <p className="inv-dialog__hint">Current: {formatInventoryPrice(currentPrice)}</p>
          )}
          {error && <p className="inv-dialog__error">{error}</p>}
        </div>
        <footer className="inv-dialog__footer">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => void submit()} disabled={loading}>
            {loading ? 'Saving…' : 'Save'}
          </button>
        </footer>
      </div>
    </div>
  );
}
