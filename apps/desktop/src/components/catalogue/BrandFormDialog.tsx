import { type ChangeEvent, useEffect, useRef, useState } from 'react';
import { Upload, X } from 'lucide-react';
import { BrandLogoImage } from '../branding/BrandLogoImage';
import { BrandLogoRegistry } from '../../registries/BrandLogoRegistry';
import type {
  Brand,
  CreateBrandRequest,
  UpdateBrandRequest,
} from '../../services/api/BrandService';

interface BrandFormDialogProps {
  open: boolean;
  brand: Brand | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: (
    payload: CreateBrandRequest | UpdateBrandRequest,
    logoFile?: File | null,
  ) => Promise<void>;
}

const LOGO_ACCEPT = 'image/png,image/jpeg,image/webp';
const MAX_LOGO_BYTES = 5 * 1024 * 1024;

const BUNDLED_LOGO_KEYS = BrandLogoRegistry.listBundledBrandKeys();

export function BrandFormDialog({
  open,
  brand,
  loading,
  onClose,
  onConfirm,
}: BrandFormDialogProps): JSX.Element | null {
  const [name, setName] = useState('');
  const [shortName, setShortName] = useState('');
  const [logoFilename, setLogoFilename] = useState('');
  const [logoManuallySet, setLogoManuallySet] = useState(false);
  const [displayOrder, setDisplayOrder] = useState('0');
  const [isActive, setIsActive] = useState(true);
  const [allowDuplicateSerials, setAllowDuplicateSerials] = useState(false);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) return;
    setName(brand?.name ?? '');
    setShortName(brand?.short_name ?? '');
    setLogoFilename(brand?.logo_filename ?? '');
    setLogoManuallySet(Boolean(brand?.logo_filename));
    setDisplayOrder(String(brand?.display_order ?? 0));
    setIsActive(brand?.is_active ?? true);
    setAllowDuplicateSerials(brand?.allow_duplicate_serials ?? false);
    setLogoFile(null);
    setLogoPreview(null);
    setError(null);
  }, [open, brand]);

  useEffect(() => {
    if (!open || logoManuallySet || !name.trim()) return;
    const suggested = BrandLogoRegistry.logoFilenameForBrand(name);
    if (suggested) {
      setLogoFilename(suggested);
    }
  }, [open, name, logoManuallySet]);

  if (!open) return null;

  const submit = async () => {
    if (!name.trim()) {
      setError('Brand name is required.');
      return;
    }
    setError(null);
    // When a custom logo file is chosen, the backend sets logo_filename from
    // the uploaded asset after save. Keep any existing uploaded path so it is
    // not clobbered by a name-derived bundled guess.
    const resolvedLogo = logoFile
      ? logoFilename.trim() || null
      : logoFilename.trim() || BrandLogoRegistry.logoFilenameForBrand(name.trim()) || null;
    try {
      await onConfirm(
        {
          name: name.trim(),
          short_name: shortName.trim() || null,
          logo_filename: resolvedLogo,
          display_order: Number(displayOrder) || 0,
          is_active: isActive,
          allow_duplicate_serials: allowDuplicateSerials,
        },
        logoFile,
      );
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to save brand.');
    }
  };

  const selectLogo = (filename: string) => {
    setLogoManuallySet(true);
    setLogoFilename(filename);
    setLogoFile(null);
    setLogoPreview(null);
  };

  const onLogoFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    event.target.value = '';
    if (!file) return;
    if (!LOGO_ACCEPT.split(',').includes(file.type)) {
      setError('Logo must be a PNG, JPG, or WebP image.');
      return;
    }
    if (file.size > MAX_LOGO_BYTES) {
      setError('Logo must be 5 MB or smaller.');
      return;
    }
    setError(null);
    setLogoFile(file);
    setLogoManuallySet(true);
    const reader = new FileReader();
    reader.onload = () => setLogoPreview(String(reader.result));
    reader.readAsDataURL(file);
  };

  return (
    <div className="cat-dialog-overlay" role="presentation" onClick={onClose}>
      <div
        className="cat-dialog cat-dialog--wide animate-slide-in"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="cat-dialog__header">
          <h2 className="cat-dialog__title">{brand ? 'Edit brand' : 'Add brand'}</h2>
          <button
            type="button"
            className="app-toolbar-icon-btn"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </header>
        <div className="cat-dialog__body cat-dialog__grid">
          <label className="cat-field">
            <span>Name</span>
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </label>
          <label className="cat-field">
            <span>Short name</span>
            <input
              className="input"
              value={shortName}
              onChange={(e) => setShortName(e.target.value)}
            />
          </label>
          <div className="cat-field cat-field--full">
            <span>Logo</span>
            <p className="cat-logo-picker__hint">
              Upload a custom logo (PNG, JPG, or WebP), pick a bundled logo below, or leave Default
              to match by brand name.
            </p>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                marginBottom: 8,
              }}
            >
              {logoPreview ? (
                <img
                  src={logoPreview}
                  alt="Selected logo preview"
                  style={{
                    height: 44,
                    width: 44,
                    objectFit: 'contain',
                    borderRadius: 6,
                    background: 'var(--surface-2, #f3f4f6)',
                  }}
                />
              ) : (
                <BrandLogoImage
                  brand={name || 'default'}
                  logoFilename={logoFilename || null}
                  className="cat-logo-picker__img"
                  alt="Current logo"
                />
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept={LOGO_ACCEPT}
                style={{ display: 'none' }}
                onChange={onLogoFileChange}
              />
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={12} aria-hidden /> Upload custom logo
              </button>
              {logoFile && (
                <span className="cat-logo-picker__label" style={{ maxWidth: 180 }}>
                  {logoFile.name}
                </span>
              )}
            </div>
            <div className="cat-logo-picker" role="listbox" aria-label="Brand logo">
              <button
                type="button"
                role="option"
                aria-selected={!logoFilename}
                className={`cat-logo-picker__item${!logoFilename ? ' cat-logo-picker__item--selected' : ''}`}
                onClick={() => selectLogo('')}
              >
                <BrandLogoImage brand="default" className="cat-logo-picker__img" alt="Default" />
                <span className="cat-logo-picker__label">Default</span>
              </button>
              {BUNDLED_LOGO_KEYS.map((key) => {
                const filename = `${key}.svg`;
                const selected = logoFilename === filename;
                return (
                  <button
                    key={key}
                    type="button"
                    role="option"
                    aria-selected={selected}
                    className={`cat-logo-picker__item${selected ? ' cat-logo-picker__item--selected' : ''}`}
                    onClick={() => selectLogo(filename)}
                  >
                    <BrandLogoImage
                      brand={key}
                      logoFilename={filename}
                      className="cat-logo-picker__img"
                      alt={key}
                    />
                    <span className="cat-logo-picker__label">{key}</span>
                  </button>
                );
              })}
            </div>
          </div>
          <label className="cat-field">
            <span>Display order</span>
            <input
              className="input"
              type="number"
              min={0}
              value={displayOrder}
              onChange={(e) => setDisplayOrder(e.target.value)}
            />
          </label>
          <label className="cat-field cat-field--checkbox">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
            />
            <span>Active</span>
          </label>
          <div className="cat-field cat-field--full">
            <label className="cat-field--checkbox">
              <input
                type="checkbox"
                checked={allowDuplicateSerials}
                onChange={(e) => setAllowDuplicateSerials(e.target.checked)}
              />
              <span>EAN-as-serial (allow duplicate serial numbers)</span>
            </label>
            <p className="cat-logo-picker__hint">
              For accessory brands where every unit of a model shares the same EAN. Enter the EAN
              once with a quantity when adding stock. Leave off for laptops and serial-tracked
              products (the default).
            </p>
          </div>
          {error && <p className="cat-dialog__error cat-dialog__error--full">{error}</p>}
        </div>
        <footer className="cat-dialog__footer">
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={onClose}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => void submit()}
            disabled={loading}
          >
            {loading ? 'Saving…' : 'Save'}
          </button>
        </footer>
      </div>
    </div>
  );
}
