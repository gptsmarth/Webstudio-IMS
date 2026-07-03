import { useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { STORAGE_TYPES, STORAGE_UNITS } from '../../lib/catalogue';
import { parseSerialNumbers } from '../../lib/parseSerialNumbers';
import type { Brand } from '../../services/api/BrandService';
import type { Location } from '../../services/api/LocationService';
import type {
  CreateProductModelRequest,
  ProductModel,
} from '../../services/api/ProductModelService';
import type { InventoryStatus } from '../../services/api/InventoryService';
import { ProductModelSummaryPanel } from './ProductModelSummaryPanel';

export type ProductModelSelectionMode = 'existing' | 'new';

export interface AddInventoryBatchRequest {
  mode: ProductModelSelectionMode;
  productModelId?: string;
  newProductModel?: CreateProductModelRequest;
  serialNumbers: string[];
  color: string;
  current_location_id: number;
  status?: InventoryStatus;
}

interface AddInventoryDialogProps {
  open: boolean;
  brands: Brand[];
  locations: Location[];
  productModels: ProductModel[];
  loading: boolean;
  onClose: () => void;
  onBrandChange: (brandId: number | null) => void;
  onConfirm: (payload: AddInventoryBatchRequest) => Promise<void>;
}

const STATUS_OPTIONS: Array<{ value: InventoryStatus; label: string }> = [
  { value: 'received', label: 'Received' },
  { value: 'available', label: 'Available' },
];

export function AddInventoryDialog({
  open,
  brands,
  locations,
  productModels,
  loading,
  onClose,
  onBrandChange,
  onConfirm,
}: AddInventoryDialogProps): JSX.Element | null {
  const [brandId, setBrandId] = useState<number | null>(null);
  const [modelMode, setModelMode] = useState<ProductModelSelectionMode>('existing');
  const [productModelId, setProductModelId] = useState('');
  const [serialNumbersRaw, setSerialNumbersRaw] = useState('');
  const [color, setColor] = useState('');
  const [locationId, setLocationId] = useState<number | null>(null);
  const [status, setStatus] = useState<InventoryStatus>('available');
  const [modelNumber, setModelNumber] = useState('');
  const [modelName, setModelName] = useState('');
  const [cpu, setCpu] = useState('');
  const [gpu, setGpu] = useState('');
  const [ramGb, setRamGb] = useState('16');
  const [storageValue, setStorageValue] = useState('512');
  const [storageUnit, setStorageUnit] = useState<'GB' | 'TB'>('GB');
  const [storageType, setStorageType] = useState<'SSD' | 'HDD'>('SSD');
  const [display, setDisplay] = useState('');
  const [colorOptions, setColorOptions] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setBrandId(null);
    setModelMode('existing');
    setProductModelId('');
    setSerialNumbersRaw('');
    setColor('');
    setLocationId(locations[0]?.id ?? null);
    setStatus('available');
    setModelNumber('');
    setModelName('');
    setCpu('');
    setGpu('');
    setRamGb('16');
    setStorageValue('512');
    setStorageUnit('GB');
    setStorageType('SSD');
    setDisplay('');
    setColorOptions('');
    setError(null);
    onBrandChange(null);
  }, [open, locations, onBrandChange]);

  const serialNumbers = useMemo(() => parseSerialNumbers(serialNumbersRaw), [serialNumbersRaw]);
  const brandModels = productModels.filter((model) => model.brand_id === brandId);
  const selectedModel = productModels.find((model) => model.id === productModelId) ?? null;
  const colorSuggestions = useMemo(() => {
    const source = modelMode === 'existing' ? selectedModel?.color_options : colorOptions;
    if (!source?.trim()) return [];
    return source
      .split(',')
      .map((entry) => entry.trim())
      .filter(Boolean);
  }, [colorOptions, modelMode, selectedModel?.color_options]);

  useEffect(() => {
    if (!brandId) return;
    if (brandModels.length === 0) {
      setModelMode('new');
      setProductModelId('');
      return;
    }
    setModelMode('existing');
    setProductModelId((current) =>
      current && brandModels.some((model) => model.id === current) ? current : brandModels[0].id,
    );
  }, [brandId, brandModels]);

  if (!open) return null;

  const submit = async () => {
    if (!brandId || !locationId || !color.trim() || serialNumbers.length === 0) {
      setError('Brand, at least one serial number, color, and location are required.');
      return;
    }
    if (modelMode === 'existing' && !productModelId) {
      setError('Select an existing product model or switch to create a new one.');
      return;
    }
    if (modelMode === 'new' && (!modelNumber.trim() || !modelName.trim() || !cpu.trim())) {
      setError('Model number, model name, and CPU are required for a new product model.');
      return;
    }

    setError(null);
    try {
      await onConfirm({
        mode: modelMode,
        productModelId: modelMode === 'existing' ? productModelId : undefined,
        newProductModel:
          modelMode === 'new'
            ? {
                brand_id: brandId,
                model_number: modelNumber.trim(),
                model_name: modelName.trim(),
                cpu: cpu.trim(),
                gpu: gpu.trim() || null,
                ram_gb: Number(ramGb),
                storage_value: storageValue,
                storage_unit: storageUnit,
                storage_type: storageType,
                display: display.trim() || null,
                color_options: colorOptions.trim() || null,
              }
            : undefined,
        serialNumbers,
        color: color.trim(),
        current_location_id: locationId,
        status,
      });
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to add inventory.');
    }
  };

  const saveLabel =
    serialNumbers.length > 1
      ? `Add ${serialNumbers.length} units`
      : serialNumbers.length === 1
        ? 'Add unit'
        : 'Add inventory';

  return (
    <div className="inv-dialog-overlay" role="presentation" onClick={onClose}>
      <div
        className="inv-dialog inv-dialog--wide animate-slide-in"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-inventory-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="inv-dialog__header">
          <div>
            <h2 id="add-inventory-title" className="inv-dialog__title">
              Add inventory
            </h2>
            <p className="inv-dialog__lead">
              Link serial numbers to an existing product model, or create the catalogue entry once.
            </p>
          </div>
          <button
            type="button"
            className="app-toolbar-icon-btn"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={16} aria-hidden />
          </button>
        </header>

        <div className="inv-dialog__body inv-dialog__grid">
          <label className="inv-filters__field inv-dialog__field--full">
            <span className="inv-filters__label">Brand</span>
            <select
              className="input"
              value={brandId ?? ''}
              onChange={(e) => {
                const next = e.target.value ? Number(e.target.value) : null;
                setBrandId(next);
                setProductModelId('');
                onBrandChange(next);
              }}
            >
              <option value="">Select brand</option>
              {brands.map((brand) => (
                <option key={brand.id} value={brand.id}>
                  {brand.name}
                </option>
              ))}
            </select>
          </label>

          {brandId && (
            <div className="inv-dialog__field--full inv-add-model-mode">
              <span className="inv-filters__label">Product model</span>
              <div className="inv-add-model-mode__options">
                <label className="inv-add-model-mode__option">
                  <input
                    type="radio"
                    name="model-mode"
                    checked={modelMode === 'existing'}
                    onChange={() => setModelMode('existing')}
                    disabled={brandModels.length === 0}
                  />
                  Use existing model
                  {brandModels.length > 0 && (
                    <span className="inv-add-model-mode__badge">{brandModels.length} on file</span>
                  )}
                </label>
                <label className="inv-add-model-mode__option">
                  <input
                    type="radio"
                    name="model-mode"
                    checked={modelMode === 'new'}
                    onChange={() => setModelMode('new')}
                  />
                  Create new model
                </label>
              </div>
            </div>
          )}

          {brandId && modelMode === 'existing' && (
            <>
              <label className="inv-filters__field inv-dialog__field--full">
                <span className="inv-filters__label">Existing product model</span>
                <select
                  className="input"
                  value={productModelId}
                  onChange={(e) => setProductModelId(e.target.value)}
                >
                  <option value="">Select model</option>
                  {brandModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.model_number} — {model.model_name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="inv-dialog__field--full">
                <ProductModelSummaryPanel model={selectedModel} />
              </div>
            </>
          )}

          {brandId && modelMode === 'new' && (
            <>
              <label className="inv-filters__field">
                <span className="inv-filters__label">Model number</span>
                <input
                  className="input col-mono"
                  value={modelNumber}
                  onChange={(e) => setModelNumber(e.target.value)}
                />
              </label>
              <label className="inv-filters__field">
                <span className="inv-filters__label">Model name</span>
                <input
                  className="input"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                />
              </label>
              <label className="inv-filters__field">
                <span className="inv-filters__label">CPU</span>
                <input className="input" value={cpu} onChange={(e) => setCpu(e.target.value)} />
              </label>
              <label className="inv-filters__field">
                <span className="inv-filters__label">GPU</span>
                <input className="input" value={gpu} onChange={(e) => setGpu(e.target.value)} />
              </label>
              <label className="inv-filters__field">
                <span className="inv-filters__label">RAM (GB)</span>
                <input
                  className="input"
                  type="number"
                  min={1}
                  value={ramGb}
                  onChange={(e) => setRamGb(e.target.value)}
                />
              </label>
              <label className="inv-filters__field">
                <span className="inv-filters__label">Storage</span>
                <input
                  className="input"
                  value={storageValue}
                  onChange={(e) => setStorageValue(e.target.value)}
                />
              </label>
              <label className="inv-filters__field">
                <span className="inv-filters__label">Storage unit</span>
                <select
                  className="input"
                  value={storageUnit}
                  onChange={(e) => setStorageUnit(e.target.value as 'GB' | 'TB')}
                >
                  {STORAGE_UNITS.map((unit) => (
                    <option key={unit} value={unit}>
                      {unit}
                    </option>
                  ))}
                </select>
              </label>
              <label className="inv-filters__field">
                <span className="inv-filters__label">Storage type</span>
                <select
                  className="input"
                  value={storageType}
                  onChange={(e) => setStorageType(e.target.value as 'SSD' | 'HDD')}
                >
                  {STORAGE_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </label>
              <label className="inv-filters__field">
                <span className="inv-filters__label">Generation</span>
                <input
                  className="input"
                  value={display}
                  onChange={(e) => setDisplay(e.target.value)}
                />
              </label>
              <label className="inv-filters__field inv-dialog__field--full">
                <span className="inv-filters__label">Color variants (catalogue)</span>
                <input
                  className="input"
                  value={colorOptions}
                  onChange={(e) => setColorOptions(e.target.value)}
                  placeholder="e.g. Quiet Blue, Silver"
                />
              </label>
            </>
          )}

          <label className="inv-filters__field inv-dialog__field--full">
            <span className="inv-filters__label">Serial numbers</span>
            <textarea
              className="input inv-add-serials"
              value={serialNumbersRaw}
              onChange={(e) => setSerialNumbersRaw(e.target.value)}
              placeholder={'SN001\nSN002\nSN003'}
              rows={5}
            />
            <span className="inv-add-serials__hint">
              {serialNumbers.length > 0
                ? `${serialNumbers.length} unique serial number${serialNumbers.length === 1 ? '' : 's'} will be created.`
                : 'Enter one serial per line, or separate with commas.'}
            </span>
          </label>

          <label className="inv-filters__field">
            <span className="inv-filters__label">Unit color</span>
            {colorSuggestions.length > 0 ? (
              <input
                className="input"
                list="add-inv-color-options"
                value={color}
                onChange={(e) => setColor(e.target.value)}
              />
            ) : (
              <input className="input" value={color} onChange={(e) => setColor(e.target.value)} />
            )}
            {colorSuggestions.length > 0 && (
              <datalist id="add-inv-color-options">
                {colorSuggestions.map((option) => (
                  <option key={option} value={option} />
                ))}
              </datalist>
            )}
          </label>

          <label className="inv-filters__field">
            <span className="inv-filters__label">Location</span>
            <select
              className="input"
              value={locationId ?? ''}
              onChange={(e) => setLocationId(Number(e.target.value))}
            >
              {locations.map((location) => (
                <option key={location.id} value={location.id}>
                  {location.name}
                </option>
              ))}
            </select>
          </label>

          <label className="inv-filters__field">
            <span className="inv-filters__label">Initial status</span>
            <select
              className="input"
              value={status}
              onChange={(e) => setStatus(e.target.value as InventoryStatus)}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {error && <p className="inv-dialog__error inv-dialog__error--full">{error}</p>}
        </div>

        <footer className="inv-dialog__footer">
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
            disabled={loading || serialNumbers.length === 0}
          >
            {loading ? 'Saving…' : saveLabel}
          </button>
        </footer>
      </div>
    </div>
  );
}
