import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import type { Location } from '../../services/api/LocationService';

interface LocationDeleteDialogProps {
  open: boolean;
  location: Location | null;
  inventoryCount: number;
  movableCount: number;
  destinations: Location[];
  loading: boolean;
  onClose: () => void;
  onConfirm: (transferToLocationId: number) => Promise<void>;
}

export function LocationDeleteDialog({
  open,
  location,
  inventoryCount,
  movableCount,
  destinations,
  loading,
  onClose,
  onConfirm,
}: LocationDeleteDialogProps): JSX.Element | null {
  const [transferToId, setTransferToId] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setTransferToId(destinations[0] ? String(destinations[0].id) : '');
    setError(null);
  }, [open, destinations]);

  if (!open || !location) return null;

  const submit = async () => {
    const id = Number(transferToId);
    if (!id) {
      setError('Choose a destination location.');
      return;
    }
    setError(null);
    try {
      await onConfirm(id);
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to delete location.');
    }
  };

  return (
    <div className="cat-dialog-overlay" role="presentation" onClick={onClose}>
      <div className="cat-dialog animate-slide-in" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <header className="cat-dialog__header">
          <h2 className="cat-dialog__title">Delete location permanently</h2>
          <button type="button" className="app-toolbar-icon-btn" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </header>
        <div className="cat-dialog__body">
          <p>
            <strong>{location.name}</strong> has {inventoryCount} inventory item{inventoryCount === 1 ? '' : 's'}
            {movableCount !== inventoryCount ? ` (${movableCount} movable)` : ''}.
            All items will be transferred to the destination you choose, then this location will be permanently deleted.
            This action cannot be undone.
          </p>
          <label className="cat-dialog__field">
            <span>Transfer to</span>
            <select className="input" value={transferToId} onChange={(e) => setTransferToId(e.target.value)} disabled={loading || destinations.length === 0}>
              {destinations.length === 0 && <option value="">No other locations available</option>}
              {destinations.map((dest) => (
                <option key={dest.id} value={dest.id}>{dest.name}</option>
              ))}
            </select>
          </label>
          {error && <div className="alert alert-danger">{error}</div>}
        </div>
        <footer className="cat-dialog__footer">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>Cancel</button>
          <button type="button" className="btn btn-danger" onClick={() => void submit()} disabled={loading || destinations.length === 0}>
            {loading ? 'Deleting…' : 'Transfer and delete'}
          </button>
        </footer>
      </div>
    </div>
  );
}
