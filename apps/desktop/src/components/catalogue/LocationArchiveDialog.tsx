import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import type { Location } from '../../services/api/LocationService';

interface LocationArchiveDialogProps {
  open: boolean;
  location: Location | null;
  movableCount: number;
  destinations: Location[];
  loading: boolean;
  onClose: () => void;
  onConfirm: (transferToLocationId: number) => Promise<void>;
}

export function LocationArchiveDialog({
  open,
  location,
  movableCount,
  destinations,
  loading,
  onClose,
  onConfirm,
}: LocationArchiveDialogProps): JSX.Element | null {
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
      setError(message.message ?? 'Unable to archive location.');
    }
  };

  return (
    <div className="cat-dialog-overlay" role="presentation" onClick={onClose}>
      <div className="cat-dialog animate-slide-in" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <header className="cat-dialog__header">
          <h2 className="cat-dialog__title">Transfer inventory before removing</h2>
          <button type="button" className="app-toolbar-icon-btn" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </header>
        <div className="cat-dialog__body">
          <p>
            <strong>{location.name}</strong> still has {movableCount} movable item{movableCount === 1 ? '' : 's'}.
            Choose where to move them before this location is archived.
          </p>
          <label className="cat-dialog__field">
            <span>Transfer to</span>
            <select className="input" value={transferToId} onChange={(e) => setTransferToId(e.target.value)} disabled={loading || destinations.length === 0}>
              {destinations.length === 0 && <option value="">No active locations available</option>}
              {destinations.map((dest) => (
                <option key={dest.id} value={dest.id}>{dest.name}</option>
              ))}
            </select>
          </label>
          {error && <div className="alert alert-danger">{error}</div>}
        </div>
        <footer className="cat-dialog__footer">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>Cancel</button>
          <button type="button" className="btn btn-primary" onClick={() => void submit()} disabled={loading || destinations.length === 0}>
            {loading ? 'Archiving…' : 'Transfer and remove'}
          </button>
        </footer>
      </div>
    </div>
  );
}
