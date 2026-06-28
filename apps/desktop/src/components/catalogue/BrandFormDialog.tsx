import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { ASSET_MANIFEST } from '../../registries/AssetManifest';
import type { Brand, CreateBrandRequest, UpdateBrandRequest } from '../../services/api/BrandService';

interface BrandFormDialogProps {
  open: boolean;
  brand: Brand | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: (payload: CreateBrandRequest | UpdateBrandRequest) => Promise<void>;
}

const LOGO_OPTIONS = Object.keys(ASSET_MANIFEST.brandLogos).filter((key) => key !== 'default');

export function BrandFormDialog({ open, brand, loading, onClose, onConfirm }: BrandFormDialogProps): JSX.Element | null {
  const [name, setName] = useState('');
  const [shortName, setShortName] = useState('');
  const [logoFilename, setLogoFilename] = useState('');
  const [displayOrder, setDisplayOrder] = useState('0');
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setName(brand?.name ?? '');
    setShortName(brand?.short_name ?? '');
    setLogoFilename(brand?.logo_filename ?? '');
    setDisplayOrder(String(brand?.display_order ?? 0));
    setIsActive(brand?.is_active ?? true);
    setError(null);
  }, [open, brand]);

  if (!open) return null;

  const submit = async () => {
    if (!name.trim()) {
      setError('Brand name is required.');
      return;
    }
    setError(null);
    try {
      await onConfirm({
        name: name.trim(),
        short_name: shortName.trim() || null,
        logo_filename: logoFilename || null,
        display_order: Number(displayOrder) || 0,
        is_active: isActive,
      });
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to save brand.');
    }
  };

  return (
    <div className="cat-dialog-overlay" role="presentation" onClick={onClose}>
      <div className="cat-dialog animate-slide-in" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <header className="cat-dialog__header">
          <h2 className="cat-dialog__title">{brand ? 'Edit brand' : 'Add brand'}</h2>
          <button type="button" className="app-toolbar-icon-btn" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </header>
        <div className="cat-dialog__body cat-dialog__grid">
          <label className="cat-field"><span>Name</span><input className="input" value={name} onChange={(e) => setName(e.target.value)} autoFocus /></label>
          <label className="cat-field"><span>Short name</span><input className="input" value={shortName} onChange={(e) => setShortName(e.target.value)} /></label>
          <label className="cat-field">
            <span>Logo</span>
            <select className="input" value={logoFilename} onChange={(e) => setLogoFilename(e.target.value)}>
              <option value="">Default</option>
              {LOGO_OPTIONS.map((key) => <option key={key} value={`${key}.svg`}>{key}</option>)}
            </select>
          </label>
          <label className="cat-field"><span>Display order</span><input className="input" type="number" min={0} value={displayOrder} onChange={(e) => setDisplayOrder(e.target.value)} /></label>
          <label className="cat-field cat-field--checkbox">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            <span>Active</span>
          </label>
          {error && <p className="cat-dialog__error cat-dialog__error--full">{error}</p>}
        </div>
        <footer className="cat-dialog__footer">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={loading}>Cancel</button>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => void submit()} disabled={loading}>{loading ? 'Saving…' : 'Save'}</button>
        </footer>
      </div>
    </div>
  );
}
