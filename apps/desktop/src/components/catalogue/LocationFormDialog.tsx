import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import type { CreateLocationRequest, Location, UpdateLocationRequest } from '../../services/api/LocationService';

interface LocationFormDialogProps {
  open: boolean;
  location: Location | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: (payload: CreateLocationRequest | UpdateLocationRequest) => Promise<void>;
}

export function LocationFormDialog({ open, location, loading, onClose, onConfirm }: LocationFormDialogProps): JSX.Element | null {
  const [name, setName] = useState('');
  const [locationType, setLocationType] = useState<'retail_floor' | 'warehouse' | 'other'>('retail_floor');
  const [sortOrder, setSortOrder] = useState('');
  const [branchId, setBranchId] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setName(location?.name ?? '');
    setLocationType(location?.location_type ?? 'retail_floor');
    setSortOrder(location?.sort_order != null ? String(location.sort_order) : '');
    setBranchId(location?.branch_id != null ? String(location.branch_id) : '');
    setIsActive(location?.is_active ?? true);
    setError(null);
  }, [open, location]);

  if (!open) return null;

  const submit = async () => {
    if (!name.trim()) {
      setError('Location name is required.');
      return;
    }
    setError(null);
    try {
      await onConfirm({
        name: name.trim(),
        location_type: locationType,
        sort_order: sortOrder ? Number(sortOrder) : null,
        branch_id: branchId ? Number(branchId) : null,
        is_active: isActive,
      });
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to save location.');
    }
  };

  return (
    <div className="cat-dialog-overlay" role="presentation" onClick={onClose}>
      <div className="cat-dialog animate-slide-in" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <header className="cat-dialog__header">
          <h2 className="cat-dialog__title">{location ? 'Edit location' : 'Add location'}</h2>
          <button type="button" className="app-toolbar-icon-btn" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </header>
        <div className="cat-dialog__body cat-dialog__grid">
          <label className="cat-field"><span>Name</span><input className="input" value={name} onChange={(e) => setName(e.target.value)} autoFocus /></label>
          <label className="cat-field">
            <span>Type</span>
            <select className="input" value={locationType} onChange={(e) => setLocationType(e.target.value as typeof locationType)}>
              <option value="retail_floor">Retail floor</option>
              <option value="warehouse">Warehouse</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label className="cat-field"><span>Sort order</span><input className="input" type="number" min={0} value={sortOrder} onChange={(e) => setSortOrder(e.target.value)} /></label>
          <label className="cat-field"><span>Branch ID</span><input className="input" type="number" min={1} value={branchId} onChange={(e) => setBranchId(e.target.value)} /></label>
          <label className="cat-field cat-field--checkbox">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            <span>Active</span>
          </label>
          {error && <p className="cat-dialog__error cat-field--full">{error}</p>}
        </div>
        <footer className="cat-dialog__footer">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={loading}>Cancel</button>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => void submit()} disabled={loading}>{loading ? 'Saving…' : 'Save'}</button>
        </footer>
      </div>
    </div>
  );
}
