import { useEffect, useState } from 'react';
import { Globe, X } from 'lucide-react';
import { confirmCatalogueRemoval } from '../../../lib/catalogue';
import type { ProductModel } from '../../../services/api/ProductModelService';
import type { StorageType, StorageUnit } from '../../../services/api/InventoryService';
import { formatInventoryPrice, parsePriceInput } from '../../../lib/inventoryPrice';
import { fetchProductSpecFromInternet } from '../../../lib/productSpecLookup';
import { composeModelNotes } from '../../../lib/modelNotes';

interface InventoryModelEditDialogProps {
  open: boolean;
  model: ProductModel | null;
  loading: boolean;
  canArchive?: boolean;
  onClose: () => void;
  onConfirm: (patch: {
    model_number: string;
    model_name: string;
    cpu: string;
    gpu: string | null;
    ram_gb: number;
    storage_value: number;
    storage_unit: StorageUnit;
    storage_type: StorageType;
    display: string | null;
    color_options: string | null;
    product_image_url?: string | null;
    notes: string | null;
    purchase_price: number | null;
    selling_price: number | null;
  }) => Promise<void>;
  onArchive?: () => Promise<void>;
}

export function InventoryModelEditDialog({
  open,
  model,
  loading,
  canArchive = false,
  onClose,
  onConfirm,
  onArchive,
}: InventoryModelEditDialogProps): JSX.Element | null {
  const [modelNumber, setModelNumber] = useState('');
  const [modelName, setModelName] = useState('');
  const [cpu, setCpu] = useState('');
  const [gpu, setGpu] = useState('');
  const [ramGb, setRamGb] = useState('');
  const [storageValue, setStorageValue] = useState('');
  const [storageUnit, setStorageUnit] = useState<StorageUnit>('GB');
  const [storageType, setStorageType] = useState<StorageType>('SSD');
  const [display, setDisplay] = useState('');
  const [colorOptions, setColorOptions] = useState('');
  const [productImageUrl, setProductImageUrl] = useState('');
  const [notes, setNotes] = useState('');
  const [purchasePrice, setPurchasePrice] = useState('');
  const [sellingPrice, setSellingPrice] = useState('');
  const [refetching, setRefetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !model) return;
    setModelNumber(model.model_number);
    setModelName(model.model_name);
    setCpu(model.cpu);
    setGpu(model.gpu ?? '');
    setRamGb(String(model.ram_gb));
    setStorageValue(String(model.storage_value));
    setStorageUnit(model.storage_unit);
    setStorageType(model.storage_type);
    setDisplay(model.display ?? '');
    setColorOptions(model.color_options ?? '');
    setProductImageUrl(model.product_image_url ?? '');
    setNotes(model.notes ?? '');
    setPurchasePrice(model.purchase_price != null ? String(model.purchase_price) : '');
    setSellingPrice(model.selling_price != null ? String(model.selling_price) : '');
    setError(null);
  }, [open, model]);

  if (!open || !model) return null;

  const submit = async () => {
    const ram = Number(ramGb);
    const storage = Number(storageValue);
    if (!modelNumber.trim() || !modelName.trim() || !cpu.trim()) {
      setError('Model number, name, and processor are required.');
      return;
    }
    if (!Number.isFinite(ram) || ram <= 0) {
      setError('Enter a valid RAM size.');
      return;
    }
    if (!Number.isFinite(storage) || storage <= 0) {
      setError('Enter a valid storage size.');
      return;
    }

    const parsedPurchase = purchasePrice.trim() ? parsePriceInput(purchasePrice) : null;
    const parsedSelling = sellingPrice.trim() ? parsePriceInput(sellingPrice) : null;
    if (purchasePrice.trim() && parsedPurchase === null) {
      setError('Enter a valid purchase price or leave blank.');
      return;
    }
    if (sellingPrice.trim() && parsedSelling === null) {
      setError('Enter a valid selling price or leave blank.');
      return;
    }

    setError(null);
    try {
      await onConfirm({
        model_number: modelNumber.trim(),
        model_name: modelName.trim(),
        cpu: cpu.trim(),
        gpu: gpu.trim() || null,
        ram_gb: ram,
        storage_value: storage,
        storage_unit: storageUnit,
        storage_type: storageType,
        display: display.trim() || null,
        color_options: colorOptions.trim() || null,
        product_image_url: productImageUrl.trim() || null,
        notes: notes.trim() || null,
        purchase_price: parsedPurchase,
        selling_price: parsedSelling,
      });
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Could not update model.');
    }
  };

  const handleRefetch = async () => {
    if (!modelNumber.trim()) return;
    setRefetching(true);
    setError(null);
    try {
      const spec = await fetchProductSpecFromInternet(modelNumber, {
        modelName: modelName || model.model_name,
        brandName: model.brand_name || undefined,
      });
      if (!spec) {
        setError('Could not find online specifications or image for this model.');
        return;
      }
      if (spec.cpu) setCpu(spec.cpu);
      if (spec.gpu) setGpu(spec.gpu);
      if (spec.ram_gb) setRamGb(String(spec.ram_gb));
      if (spec.storage_value) setStorageValue(String(spec.storage_value));
      if (spec.storage_unit) setStorageUnit(spec.storage_unit);
      if (spec.storage_type) setStorageType(spec.storage_type);
      if (spec.display) setDisplay(spec.display);
      if (spec.color_options) setColorOptions(spec.color_options);
      if (spec.product_image_url) setProductImageUrl(spec.product_image_url);

      const combinedNotes = composeModelNotes(spec.description || '', spec.notes || '');
      if (combinedNotes) setNotes(combinedNotes);
    } catch (err: unknown) {
      const msg = err as { message?: string };
      setError(msg.message ?? 'Refetch failed.');
    } finally {
      setRefetching(false);
    }
  };

  const archive = async () => {
    if (!onArchive || !confirmCatalogueRemoval(`${model.brand_name ?? ''} ${model.model_name}`.trim(), 'model')) {
      return;
    }
    setError(null);
    try {
      await onArchive();
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Could not archive model.');
    }
  };

  return (
    <div className="inv-dialog-overlay" role="presentation" onClick={onClose}>
      <div
        className="inv-dialog inv-dialog--wide animate-slide-in"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-model-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="inv-dialog__header">
          <h2 id="edit-model-dialog-title" className="inv-dialog__title">Edit model</h2>
          <button type="button" className="app-toolbar-icon-btn" onClick={onClose} aria-label="Close">
            <X size={16} aria-hidden />
          </button>
        </header>
        <div className="inv-dialog__body inv-model-edit">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <p className="inv-dialog__hint" style={{ margin: 0 }}>
              {model.brand_name ? `${model.brand_name} · ` : ''}
              <span className="col-mono">{model.model_number}</span>
            </p>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => void handleRefetch()}
              disabled={loading || refetching}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Globe size={14} aria-hidden />
              {refetching ? 'Refetching specs & image…' : 'Refetch from internet'}
            </button>
          </div>

          <div className="inv-model-edit__grid">
            <label className="inv-filters__field">
              <span className="inv-filters__label">Model number</span>
              <input className="input" value={modelNumber} onChange={(e) => setModelNumber(e.target.value)} />
            </label>
            <label className="inv-filters__field">
              <span className="inv-filters__label">Model name</span>
              <input className="input" value={modelName} onChange={(e) => setModelName(e.target.value)} />
            </label>
            <label className="inv-filters__field inv-model-edit__span-2">
              <span className="inv-filters__label">Processor</span>
              <input className="input" value={cpu} onChange={(e) => setCpu(e.target.value)} />
            </label>
            <label className="inv-filters__field inv-model-edit__span-2">
              <span className="inv-filters__label">Graphics</span>
              <input className="input" value={gpu} onChange={(e) => setGpu(e.target.value)} placeholder="Optional" />
            </label>
            <label className="inv-filters__field">
              <span className="inv-filters__label">RAM (GB)</span>
              <input className="input" type="number" min={1} value={ramGb} onChange={(e) => setRamGb(e.target.value)} />
            </label>
            <label className="inv-filters__field">
              <span className="inv-filters__label">Storage</span>
              <input className="input" type="number" min={0} step="0.01" value={storageValue} onChange={(e) => setStorageValue(e.target.value)} />
            </label>
            <label className="inv-filters__field">
              <span className="inv-filters__label">Storage unit</span>
              <select className="input" value={storageUnit} onChange={(e) => setStorageUnit(e.target.value as StorageUnit)}>
                <option value="GB">GB</option>
                <option value="TB">TB</option>
              </select>
            </label>
            <label className="inv-filters__field">
              <span className="inv-filters__label">Storage type</span>
              <select className="input" value={storageType} onChange={(e) => setStorageType(e.target.value as StorageType)}>
                <option value="SSD">SSD</option>
                <option value="HDD">HDD</option>
              </select>
            </label>
            <label className="inv-filters__field inv-model-edit__span-2">
              <span className="inv-filters__label">Display</span>
              <input className="input" value={display} onChange={(e) => setDisplay(e.target.value)} placeholder="Optional" />
            </label>
            <label className="inv-filters__field inv-model-edit__span-2">
              <span className="inv-filters__label">Color options</span>
              <input className="input" value={colorOptions} onChange={(e) => setColorOptions(e.target.value)} placeholder="Optional" />
            </label>
            <label className="inv-filters__field inv-model-edit__span-2">
              <span className="inv-filters__label">Image URL</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  className="input"
                  style={{ flex: 1 }}
                  value={productImageUrl}
                  onChange={(e) => setProductImageUrl(e.target.value)}
                  placeholder="https://..."
                />
                {productImageUrl && (
                  <a
                    href={productImageUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-ghost btn-sm"
                    style={{ alignSelf: 'center', whiteSpace: 'nowrap' }}
                  >
                    Preview
                  </a>
                )}
              </div>
            </label>
            <label className="inv-filters__field">
              <span className="inv-filters__label">Purchase price (INR)</span>
              <input className="input" inputMode="decimal" value={purchasePrice} onChange={(e) => setPurchasePrice(e.target.value)} placeholder="Model-wide" />
              {model.purchase_price != null && (
                <span className="inv-dialog__hint">Current: {formatInventoryPrice(model.purchase_price)}</span>
              )}
            </label>
            <label className="inv-filters__field">
              <span className="inv-filters__label">Selling price (INR)</span>
              <input className="input" inputMode="decimal" value={sellingPrice} onChange={(e) => setSellingPrice(e.target.value)} placeholder="Model-wide" />
              {model.selling_price != null && (
                <span className="inv-dialog__hint">Current: {formatInventoryPrice(model.selling_price)}</span>
              )}
            </label>
            <label className="inv-filters__field inv-model-edit__span-2">
              <span className="inv-filters__label">Notes</span>
              <textarea className="input" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional" />
            </label>
          </div>

          {error && <p className="inv-dialog__error">{error}</p>}
        </div>
        <footer className="inv-dialog__footer">
          {canArchive && onArchive && model.status === 'active' && (
            <button type="button" className="btn btn-danger btn-sm inv-dialog__footer-leading" onClick={() => void archive()} disabled={loading}>
              Remove model
            </button>
          )}
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => void submit()} disabled={loading}>
            {loading ? 'Saving…' : 'Save changes'}
          </button>
        </footer>
      </div>
    </div>
  );
}
