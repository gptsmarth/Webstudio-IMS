import { useCallback, useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { STORAGE_TYPES, STORAGE_UNITS } from '../../lib/catalogue';
import { composeModelNotes } from '../../lib/modelNotes';
import { resolvePublicAsset } from '../../utils/resolvePublicAsset';
import {
  fetchProductSpecFromInternet,
  findModelByNumber,
  lookupExistingModelInventory,
  modelToFetchedSpec,
  type FetchedProductSpec,
} from '../../lib/productSpecLookup';
import type { Location } from '../../services/api/LocationService';
import type {
  CreateProductModelRequest,
  ProductModel,
} from '../../services/api/ProductModelService';
import type { InventoryStatus } from '../../services/api/InventoryService';
import { formatInventoryPrice, parsePriceInput } from '../../lib/inventoryPrice';
import { ProductModelSummaryPanel } from './ProductModelSummaryPanel';
import { ProductSpecService } from '../../services/api/ProductSpecService';

export interface SerialUnitEntry {
  serial_number: string;
  current_location_id: number;
  color: string;
  purchase_price: string;
}

export interface AddLaptopWizardUnit {
  serial_number: string;
  current_location_id: number;
  color: string;
  purchase_price: number | null;
}

export interface AddLaptopWizardRequest {
  brandId: number;
  mode: 'existing' | 'new';
  productModelId?: string;
  newProductModel?: CreateProductModelRequest;
  units: AddLaptopWizardUnit[];
  status?: InventoryStatus;
}

interface AddLaptopWizardProps {
  open: boolean;
  brandId: number;
  brandName: string;
  locations: Location[];
  productModels: ProductModel[];
  loading: boolean;
  onClose: () => void;
  onConfirm: (payload: AddLaptopWizardRequest) => Promise<void>;
}

type WizardStep = 'model' | 'specs' | 'units' | 'review';
type SpecTab = 'configuration' | 'description';

function stepLabel(step: WizardStep, mode: 'existing' | 'new'): string {
  if (mode === 'existing') {
    return step === 'model' ? '1 of 2' : '2 of 2';
  }
  if (step === 'model') return '1 of 4';
  if (step === 'specs') return '2 of 4';
  if (step === 'units') return '3 of 4';
  return '4 of 4';
}

export function AddLaptopWizard({
  open,
  brandId,
  brandName,
  locations,
  productModels,
  loading,
  onClose,
  onConfirm,
}: AddLaptopWizardProps): JSX.Element | null {
  const [step, setStep] = useState<WizardStep>('model');
  const [modelNumber, setModelNumber] = useState('');
  const [modelName, setModelName] = useState('');
  const [mode, setMode] = useState<'existing' | 'new'>('new');
  const [productModelId, setProductModelId] = useState('');
  const [existingLookup, setExistingLookup] = useState<Awaited<
    ReturnType<typeof lookupExistingModelInventory>
  > | null>(null);
  const [checking, setChecking] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [fetchMessage, setFetchMessage] = useState<string | null>(null);
  const [unitCount, setUnitCount] = useState(1);
  const [units, setUnits] = useState<SerialUnitEntry[]>([
    { serial_number: '', current_location_id: locations[0]?.id ?? 0, color: '', purchase_price: '' },
  ]);
  const [status, setStatus] = useState<InventoryStatus>('available');
  const [cpu, setCpu] = useState('');
  const [gpu, setGpu] = useState('');
  const [ramGb, setRamGb] = useState('16');
  const [storageValue, setStorageValue] = useState('512');
  const [storageUnit, setStorageUnit] = useState<'GB' | 'TB'>('GB');
  const [storageType, setStorageType] = useState<'SSD' | 'HDD'>('SSD');
  const [display, setDisplay] = useState('');
  const [colorOptions, setColorOptions] = useState('');
  const [description, setDescription] = useState('');
  const [specNotes, setSpecNotes] = useState('');
  const [specTab, setSpecTab] = useState<SpecTab>('configuration');
  const [productImageUrl, setProductImageUrl] = useState<string | null>(null);
  const [productImagePreview, setProductImagePreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const autoFetchTriggered = useRef(false);

  const brandModels = productModels.filter((model) => model.brand_id === brandId);
  const selectedModel =
    brandModels.find((model) => model.id === productModelId) ?? existingLookup?.model ?? null;

  useEffect(() => {
    if (!open) return;
    setStep('model');
    setModelNumber('');
    setModelName('');
    setMode('new');
    setProductModelId('');
    setExistingLookup(null);
    setFetchMessage(null);
    setChecking(false);
    setFetching(false);
    setUnitCount(1);
    setUnits([{ serial_number: '', current_location_id: locations[0]?.id ?? 0, color: '', purchase_price: '' }]);
    setStatus('available');
    setCpu('');
    setGpu('');
    setRamGb('16');
    setStorageValue('512');
    setStorageUnit('GB');
    setStorageType('SSD');
    setDisplay('');
    setColorOptions('');
    setDescription('');
    setSpecNotes('');
    setSpecTab('configuration');
    setProductImageUrl(null);
    setProductImagePreview(null);
    setError(null);
    autoFetchTriggered.current = false;
  }, [open, locations]);

  useEffect(() => {
    const count = Math.max(1, Math.min(50, unitCount));
    setUnits((current) => {
      const next = [...current];
      while (next.length < count) {
        next.push({
          serial_number: '',
          current_location_id: locations[0]?.id ?? 0,
          color: next[0]?.color ?? '',
          purchase_price: next[0]?.purchase_price ?? '',
        });
      }
      return next.slice(0, count);
    });
  }, [unitCount, locations]);

  const applyModel = useCallback((model: ProductModel) => {
    setMode('existing');
    setProductModelId(model.id);
    setModelNumber(model.model_number);
    setModelName(model.model_name);
    const spec = modelToFetchedSpec(model);
    setCpu(spec.cpu);
    setGpu(spec.gpu ?? '');
    setRamGb(String(spec.ram_gb));
    setStorageValue(spec.storage_value);
    setStorageUnit(spec.storage_unit);
    setStorageType(spec.storage_type);
    setDisplay(spec.display ?? '');
    setColorOptions(spec.color_options ?? '');
    setDescription(spec.description ?? '');
    setSpecNotes(spec.notes ?? '');
    setProductImageUrl(spec.product_image_url);
  }, []);

  const applyInternetSpec = useCallback(
    (internet: FetchedProductSpec) => {
      if (!internet) return;
      setModelName(internet.model_name || modelName);
      setCpu(internet.cpu);
      setGpu(internet.gpu ?? '');
      setRamGb(String(internet.ram_gb));
      setStorageValue(internet.storage_value);
      setStorageUnit(internet.storage_unit);
      setStorageType(internet.storage_type);
      setDisplay(internet.display ?? '');
      setColorOptions(internet.color_options ?? '');
      if (internet.description) {
        setDescription(internet.description);
      }
      setSpecNotes(internet.notes ?? '');
      setProductImageUrl(internet.product_image_url);
    },
    [modelName],
  );

  const runGeminiFetch = useCallback(async (): Promise<boolean> => {
    if (!modelNumber.trim()) return false;
    setFetching(true);
    setFetchMessage(null);
    setError(null);
    try {
      const internet = await fetchProductSpecFromInternet(modelNumber, {
        modelName: modelName.trim() || undefined,
        brandName,
      });
      if (internet) {
        applyInternetSpec(internet);
        const sourceNote = internet.notes?.includes('\n---\n')
          ? internet.notes.split('\n---\n').pop()?.trim()
          : null;
        setFetchMessage(
          sourceNote
            ? `Configuration auto-fetched. ${sourceNote}`
            : 'Configuration auto-fetched — review and adjust if needed.',
        );
        return true;
      }
      setFetchMessage(
        'Auto-fetch found no match — enter details manually or tap Auto fetch to retry.',
      );
      return false;
    } catch (err: unknown) {
      const message = err as { message?: string };
      setFetchMessage(
        message.message ?? 'Auto-fetch failed — enter details manually or tap Auto fetch to retry.',
      );
      return false;
    } finally {
      setFetching(false);
    }
  }, [applyInternetSpec, brandName, modelName, modelNumber]);

  useEffect(() => {
    if (!open || step !== 'specs' || mode !== 'new' || !modelNumber.trim()) {
      return;
    }
    if (autoFetchTriggered.current) {
      return;
    }
    autoFetchTriggered.current = true;
    void runGeminiFetch();
  }, [open, step, mode, modelNumber, runGeminiFetch]);

  useEffect(() => {
    if (!productImageUrl) {
      setProductImagePreview(null);
      return;
    }
    if (productImageUrl.startsWith('/assets/')) {
      setProductImagePreview(resolvePublicAsset(productImageUrl));
      return;
    }
    if (!productImageUrl.startsWith('https://')) {
      setProductImagePreview(null);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;

    void ProductSpecService.fetchImageBlob(productImageUrl)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setProductImagePreview(objectUrl);
      })
      .catch(() => {
        if (!cancelled) {
          setProductImagePreview(productImageUrl);
        }
      });

    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [productImageUrl]);

  const continueFromModel = async () => {
    const trimmed = modelNumber.trim();
    if (!trimmed) return;

    setChecking(true);
    setError(null);
    setFetchMessage(null);

    try {
      const existing = findModelByNumber(productModels, trimmed, brandId);
      if (existing) {
        const lookup = await lookupExistingModelInventory(existing);
        setExistingLookup(lookup);
        applyModel(existing);
        setFetchMessage(
          lookup.availableSerials.length > 0
            ? `Model found — ${lookup.availableSerials.length} unit(s) already in stock. Add more serial numbers below.`
            : 'Model found — add serial numbers to restore stock for this model.',
        );
        setStep('units');
        return;
      }

      setMode('new');
      setProductModelId('');
      setExistingLookup(null);
      autoFetchTriggered.current = false;
      setStep('specs');
    } finally {
      setChecking(false);
    }
  };

  const submit = async () => {
    const validUnits: Array<SerialUnitEntry & { parsedPurchasePrice: number | null }> = [];
    for (const unit of units) {
      if (!unit.serial_number.trim() || !unit.color.trim() || !unit.current_location_id) {
        continue;
      }
      let parsedPurchase: number | null = null;
      if (unit.purchase_price.trim()) {
        parsedPurchase = parsePriceInput(unit.purchase_price);
        if (parsedPurchase === null) {
          setError(`Invalid purchase price for serial ${unit.serial_number.trim()}.`);
          return;
        }
      }
      validUnits.push({ ...unit, parsedPurchasePrice: parsedPurchase });
    }
    if (validUnits.length === 0) {
      setError('Enter at least one serial number, color, and location.');
      return;
    }

    if (mode === 'existing' && !productModelId) {
      setError('Select or resolve a product model.');
      return;
    }

    if (mode === 'new') {
      if (!modelNumber.trim() || !modelName.trim() || !cpu.trim()) {
        setError('Model number, name, and CPU are required.');
        return;
      }
    }

    const payload: AddLaptopWizardRequest = {
      brandId,
      mode,
      productModelId: mode === 'existing' ? productModelId : undefined,
      units: validUnits.map((unit) => ({
        serial_number: unit.serial_number.trim(),
        color: unit.color.trim(),
        current_location_id: unit.current_location_id,
        purchase_price: unit.parsedPurchasePrice,
      })),
      status,
      newProductModel:
        mode === 'new'
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
              product_image_url: productImageUrl,
              notes: composeModelNotes(description, specNotes),
            }
          : undefined,
    };

    try {
      await onConfirm(payload);
      onClose();
    } catch {
      // parent sets error
    }
  };

  if (!open) return null;

  return (
    <div className="inv-dialog-overlay" role="presentation" onClick={onClose}>
      <div
        className="inv-dialog inv-dialog--wide animate-slide-in"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="inv-dialog__header">
          <div>
            <h2 className="inv-dialog__title">Add laptop — {brandName}</h2>
            <p className="inv-dialog__lead">
              Brand is fixed to {brandName}. Step {stepLabel(step, mode)}.
              {mode === 'existing' && step === 'units'
                ? ' Add serial numbers for this existing model.'
                : null}
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

        <div className="inv-dialog__body add-laptop-wizard">
          {step === 'model' && (
            <div className="add-laptop-wizard__step">
              <label className="form-label">Model number</label>
              <input
                className="input"
                value={modelNumber}
                onChange={(e) => setModelNumber(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && modelNumber.trim() && !checking) {
                    void continueFromModel();
                  }
                }}
                placeholder="e.g. X151VA-AB5321WS"
                autoFocus
              />
              <p className="add-laptop-wizard__hint">
                We check the database automatically. Existing models skip configuration — you only
                add serial numbers.
              </p>
              {fetchMessage && <p className="add-laptop-wizard__hint">{fetchMessage}</p>}
              <button
                type="button"
                className="btn btn-primary"
                disabled={!modelNumber.trim() || checking}
                onClick={() => void continueFromModel()}
              >
                {checking ? 'Checking database…' : 'Continue'}
              </button>
            </div>
          )}

          {step === 'specs' && (
            <div className="add-laptop-wizard__step">
              <p className="add-laptop-wizard__hint">
                New model <span className="col-mono">{modelNumber}</span>
                {fetching
                  ? ' — auto-fetching configuration…'
                  : ' — confirm or edit configuration below.'}
              </p>
              {productImagePreview || productImageUrl ? (
                <div className="add-laptop-wizard__image">
                  <div className="inv-product-image">
                    <div className="inv-product-image__frame">
                      <img
                        src={productImagePreview || productImageUrl || ''}
                        alt={modelName || modelNumber}
                        className="inv-product-image__img"
                      />
                      <span className="inv-product-image__badge inv-product-image__badge--remote">
                        Auto fetch
                      </span>
                    </div>
                    <p className="inv-product-image__hint">
                      Preview from auto-fetch. Saved with the new product model.
                    </p>
                  </div>
                </div>
              ) : null}
              <label className="form-label">
                Model name
                <input
                  className="input"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  placeholder="e.g. Vivobook 15"
                />
              </label>
              <div className="add-laptop-wizard__actions-row">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={fetching || !modelNumber.trim()}
                  onClick={() => void runGeminiFetch()}
                >
                  {fetching ? 'Fetching…' : 'Auto fetch'}
                </button>
              </div>
              {fetchMessage && <p className="add-laptop-wizard__hint">{fetchMessage}</p>}
              <div className="add-laptop-wizard__tabs" role="tablist" aria-label="Model details">
                <button
                  type="button"
                  role="tab"
                  aria-selected={specTab === 'configuration'}
                  className={`add-laptop-wizard__tab${specTab === 'configuration' ? ' add-laptop-wizard__tab--active' : ''}`}
                  onClick={() => setSpecTab('configuration')}
                >
                  Configuration
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={specTab === 'description'}
                  className={`add-laptop-wizard__tab${specTab === 'description' ? ' add-laptop-wizard__tab--active' : ''}`}
                  onClick={() => setSpecTab('description')}
                >
                  Description
                </button>
              </div>
              {specTab === 'configuration' ? (
                <div className="add-laptop-wizard__form-grid" role="tabpanel">
                  <label>
                    CPU
                    <input className="input" value={cpu} onChange={(e) => setCpu(e.target.value)} />
                  </label>
                  <label>
                    GPU
                    <input className="input" value={gpu} onChange={(e) => setGpu(e.target.value)} />
                  </label>
                  <label>
                    RAM (GB)
                    <input
                      className="input"
                      value={ramGb}
                      onChange={(e) => setRamGb(e.target.value)}
                    />
                  </label>
                  <label>
                    Storage
                    <input
                      className="input"
                      value={storageValue}
                      onChange={(e) => setStorageValue(e.target.value)}
                    />
                  </label>
                  <label>
                    Storage unit
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
                  <label>
                    Storage type
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
                  <label className="add-laptop-wizard__field-full">
                    Display
                    <input
                      className="input"
                      value={display}
                      onChange={(e) => setDisplay(e.target.value)}
                    />
                  </label>
                  <label className="add-laptop-wizard__field-full">
                    Color options
                    <input
                      className="input"
                      value={colorOptions}
                      onChange={(e) => setColorOptions(e.target.value)}
                      placeholder="e.g. Quiet Blue, Cool Silver"
                    />
                  </label>
                  <label className="add-laptop-wizard__field-full">
                    Additional specs
                    <textarea
                      className="input add-laptop-wizard__textarea"
                      rows={4}
                      value={specNotes}
                      onChange={(e) => setSpecNotes(e.target.value)}
                      placeholder="OS, battery, weight, connectivity, warranty… (auto-filled when available)"
                    />
                  </label>
                </div>
              ) : (
                <div className="add-laptop-wizard__description-panel" role="tabpanel">
                  <label className="form-label">
                    Product description
                    <textarea
                      className="input add-laptop-wizard__textarea"
                      rows={8}
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Retail summary for staff — positioning, key features, ideal customer. Auto-filled when available."
                    />
                  </label>
                </div>
              )}
              <div className="add-laptop-wizard__nav">
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => {
                    autoFetchTriggered.current = false;
                    setStep('model');
                  }}
                >
                  Back
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={!modelName.trim() || !cpu.trim()}
                  onClick={() => setStep('units')}
                >
                  Next — serial numbers
                </button>
              </div>
            </div>
          )}

          {step === 'units' && (
            <div className="add-laptop-wizard__step">
              {mode === 'existing' && selectedModel && (
                <div className="add-laptop-wizard__existing-summary">
                  <ProductModelSummaryPanel model={selectedModel} />
                  {fetchMessage && <p className="add-laptop-wizard__hint">{fetchMessage}</p>}
                </div>
              )}
              <label className="form-label">Number of units</label>
              <input
                type="number"
                className="input"
                min={1}
                max={50}
                value={unitCount}
                onChange={(e) => setUnitCount(Number(e.target.value))}
              />
              <label className="form-label">Initial status</label>
              <select
                className="input"
                value={status}
                onChange={(e) => setStatus(e.target.value as InventoryStatus)}
              >
                <option value="received">Received</option>
                <option value="available">Available</option>
              </select>
              <div className="add-laptop-wizard__units">
                <div className="add-laptop-wizard__unit-head" aria-hidden>
                  <span>Serial</span>
                  <span>Color</span>
                  <span>Location</span>
                  <span>Purchase price</span>
                </div>
                {units.map((unit, index) => (
                  <div key={index} className="add-laptop-wizard__unit-row add-laptop-wizard__unit-row--prices">
                    <input
                      className="input col-mono"
                      placeholder={`Serial ${index + 1}`}
                      value={unit.serial_number}
                      onChange={(e) =>
                        setUnits((current) =>
                          current.map((row, i) =>
                            i === index ? { ...row, serial_number: e.target.value } : row,
                          ),
                        )
                      }
                    />
                    <input
                      className="input"
                      placeholder="Color"
                      value={unit.color}
                      onChange={(e) =>
                        setUnits((current) =>
                          current.map((row, i) =>
                            i === index ? { ...row, color: e.target.value } : row,
                          ),
                        )
                      }
                    />
                    <select
                      className="input"
                      value={unit.current_location_id}
                      onChange={(e) =>
                        setUnits((current) =>
                          current.map((row, i) =>
                            i === index
                              ? { ...row, current_location_id: Number(e.target.value) }
                              : row,
                          ),
                        )
                      }
                    >
                      {locations.map((location) => (
                        <option key={location.id} value={location.id}>
                          {location.name}
                        </option>
                      ))}
                    </select>
                    <input
                      className="input inv-price-input"
                      placeholder="Purchase price"
                      inputMode="decimal"
                      value={unit.purchase_price}
                      onChange={(e) =>
                        setUnits((current) =>
                          current.map((row, i) =>
                            i === index ? { ...row, purchase_price: e.target.value } : row,
                          ),
                        )
                      }
                    />
                  </div>
                ))}
              </div>
              {error && <p className="inv-dialog__error">{error}</p>}
              <div className="add-laptop-wizard__nav">
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setStep(mode === 'existing' ? 'model' : 'specs')}
                >
                  Back
                </button>
                {mode === 'existing' ? (
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={loading}
                    onClick={() => void submit()}
                  >
                    {loading ? 'Adding…' : 'Add to inventory'}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setStep('review')}
                  >
                    Review
                  </button>
                )}
              </div>
            </div>
          )}

          {step === 'review' && mode === 'new' && (
            <div className="add-laptop-wizard__step">
              <p>
                <strong>{modelNumber}</strong> — {modelName}
              </p>
              <p>{units.filter((u) => u.serial_number.trim()).length} unit(s) · New model</p>
              <ul className="add-laptop-wizard__review-list">
                {units
                  .filter((u) => u.serial_number.trim())
                  .map((unit, index) => (
                    <li key={index}>
                      <span className="col-mono">{unit.serial_number}</span>
                      <span>{unit.color}</span>
                      <span>{locations.find((l) => l.id === unit.current_location_id)?.name}</span>
                      <span>
                        {unit.purchase_price.trim()
                          ? formatInventoryPrice(parsePriceInput(unit.purchase_price))
                          : '—'}
                      </span>
                    </li>
                  ))}
              </ul>
              {error && <p className="inv-dialog__error">{error}</p>}
              <div className="add-laptop-wizard__nav">
                <button type="button" className="btn btn-ghost" onClick={() => setStep('units')}>
                  Back
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={loading}
                  onClick={() => void submit()}
                >
                  {loading ? 'Adding…' : 'Add to inventory'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
