import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import type { Location } from '../../services/api/LocationService';

interface TransferLocationDialogProps {
  open: boolean;
  locations: Location[];
  currentLocationId: number;
  loading: boolean;
  onClose: () => void;
  onConfirm: (locationId: number) => Promise<void>;
}

export function TransferLocationDialog({
  open,
  locations,
  currentLocationId,
  loading,
  onClose,
  onConfirm,
}: TransferLocationDialogProps): JSX.Element | null {
  const options = locations.filter((location) => location.id !== currentLocationId);
  const [locationId, setLocationId] = useState<number>(options[0]?.id ?? currentLocationId);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const destinations = locations.filter((location) => location.id !== currentLocationId);
    setLocationId(destinations[0]?.id ?? currentLocationId);
    setError(null);
  }, [open, currentLocationId, locations]);

  if (!open) return null;

  const submit = async () => {
    setError(null);
    try {
      await onConfirm(locationId);
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Transfer failed.');
    }
  };

  return (
    <div className="inv-dialog-overlay" role="presentation" onClick={onClose}>
      <div
        className="inv-dialog animate-slide-in"
        role="dialog"
        aria-modal="true"
        aria-labelledby="transfer-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="inv-dialog__header">
          <h2 id="transfer-dialog-title" className="inv-dialog__title">
            Transfer location
          </h2>
          <button type="button" className="app-toolbar-icon-btn" onClick={onClose} aria-label="Close">
            <X size={16} aria-hidden />
          </button>
        </header>

        <div className="inv-dialog__body">
          <label className="inv-filters__field">
            <span className="inv-filters__label">Destination location</span>
            <select
              className="input"
              value={locationId}
              onChange={(event) => setLocationId(Number(event.target.value))}
            >
              {options.map((location) => (
                <option key={location.id} value={location.id}>
                  {location.name}
                </option>
              ))}
            </select>
          </label>
          {error && <p className="inv-dialog__error">{error}</p>}
        </div>

        <footer className="inv-dialog__footer">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => void submit()} disabled={loading}>
            {loading ? 'Transferring…' : 'Transfer'}
          </button>
        </footer>
      </div>
    </div>
  );
}
