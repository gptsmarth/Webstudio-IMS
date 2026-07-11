import { useCallback, useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { composeModelNotes } from '../../lib/modelNotes';
import { parseApiError } from '../../lib/apiError';
import { sanitizeCreateProductModelPayload } from '../../lib/productModelPayload';
import { resolvePublicAsset } from '../../utils/resolvePublicAsset';
import {
  accessoryToDisplaySpec,
  fetchAccessorySpecFromInternet,
  findAccessoryByIdentifier,
} from '../../lib/accessorySpecLookup';
import { lookupExistingModelInventory } from '../../lib/productSpecLookup';
import type { Location } from '../../services/api/LocationService';
import type { ProductModel } from '../../services/api/ProductModelService';
import type { InventoryStatus } from '../../services/api/InventoryService';
import { parsePriceInput } from '../../lib/inventoryPrice';
import { defaultUnitColorFromOptions } from '../../lib/inventoryDomain';
import {
  ACCESSORY_KINDS,
  accessoryKindLabel,
  type AccessoryIdentifierType,
  type AccessoryKind,
} from '../../lib/productCategory';
import { ProductSpecService } from '../../services/api/ProductSpecService';
import type { AddLaptopWizardRequest, SerialUnitEntry } from './AddLaptopWizard';

interface AddAccessoryWizardProps {
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

function identifierLabel(type: AccessoryIdentifierType): string {
  return type === 'part_number' ? 'Part number' : 'Model number';
}

export function AddAccessoryWizard({
  open,
  brandId,
  brandName,
  locations,
  productModels,
  loading,
  onClose,
  onConfirm,
}: AddAccessoryWizardProps): JSX.Element | null {
  const [step, setStep] = useState<WizardStep>('model');
  const [identifierType, setIdentifierType] = useState<AccessoryIdentifierType>('part_number');
  const [identifier, setIdentifier] = useState('');
  const [accessoryKind, setAccessoryKind] = useState<AccessoryKind | null>(null);
  const [modelName, setModelName] = useState('');
  const [resolvedModelNumber, setResolvedModelNumber] = useState('');
  const [resolvedPartNumber, setResolvedPartNumber] = useState('');
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
    {
      serial_number: '',
      current_location_id: locations[0]?.id ?? 0,
      purchase_price: '',
    },
  ]);
  const [status, setStatus] = useState<InventoryStatus>('available');
  const [colorOptions, setColorOptions] = useState('');
  const [description, setDescription] = useState('');
  const [specNotes, setSpecNotes] = useState('');
  const [specTab, setSpecTab] = useState<SpecTab>('configuration');
  const [productImageUrl, setProductImageUrl] = useState<string | null>(null);
  const [productImagePreview, setProductImagePreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const autoFetchKeyRef = useRef<string | null>(null);
  const forceRefreshOnNextSpecsFetch = useRef(false);
  const wasOpenRef = useRef(false);

  // Reset only when the dialog opens — not when `locations` is refreshed mid-wizard.
  useEffect(() => {
    if (!open) {
      wasOpenRef.current = false;
      return;
    }
    if (wasOpenRef.current) return;
    wasOpenRef.current = true;
    setStep('model');
    setIdentifierType('part_number');
    setIdentifier('');
    setAccessoryKind(null);
    setModelName('');
    setResolvedModelNumber('');
    setResolvedPartNumber('');
    setMode('new');
    setProductModelId('');
    setExistingLookup(null);
    setFetchMessage(null);
    setChecking(false);
    setFetching(false);
    setUnitCount(1);
    setUnits([
      {
        serial_number: '',
        current_location_id: locations[0]?.id ?? 0,
        purchase_price: '',
      },
    ]);
    setStatus('available');
    setColorOptions('');
    setDescription('');
    setSpecNotes('');
    setSpecTab('configuration');
    setProductImageUrl(null);
    setProductImagePreview(null);
    setError(null);
    autoFetchKeyRef.current = null;
    forceRefreshOnNextSpecsFetch.current = false;
  }, [open, locations]);

  useEffect(() => {
    if (!open) return;
    const defaultId = locations[0]?.id;
    if (!defaultId) return;
    setUnits((current) => {
      if (!current.some((unit) => !unit.current_location_id)) return current;
      return current.map((unit) =>
        unit.current_location_id ? unit : { ...unit, current_location_id: defaultId },
      );
    });
  }, [open, locations]);

  useEffect(() => {
    const count = Math.max(1, Math.min(50, unitCount));
    setUnits((current) => {
      const next = [...current];
      while (next.length < count) {
        next.push({
          serial_number: '',
          current_location_id: locations[0]?.id ?? 0,
          purchase_price: next[0]?.purchase_price ?? '',
        });
      }
      return next.slice(0, count);
    });
  }, [unitCount, locations]);

  const applyAccessorySpec = useCallback((spec: ReturnType<typeof accessoryToDisplaySpec>) => {
    setModelName(spec.model_name);
    setResolvedModelNumber(spec.model_number ?? '');
    setResolvedPartNumber(spec.part_number ?? '');
    setAccessoryKind(spec.accessory_kind ?? null);
    setColorOptions(spec.color_options ?? '');
    if (spec.description) {
      setDescription(spec.description);
    }
    setSpecNotes(spec.notes ?? '');
    setProductImageUrl(spec.product_image_url);
  }, []);

  const runAutoFetch = useCallback(
    async (forceRefresh = false): Promise<boolean> => {
      const trimmed = identifier.trim();
      if (!trimmed) return false;
      setFetching(true);
      setFetchMessage(null);
      setError(null);
      try {
        const internet = await fetchAccessorySpecFromInternet(trimmed, {
          identifierType,
          brandName,
          forceRefresh,
        });
        if (internet) {
          applyAccessorySpec(internet);
          const sourceNote = internet.notes?.includes('\n---\n')
            ? internet.notes.split('\n---\n').pop()?.trim()
            : null;
          if (!internet.accessory_kind) {
            setFetchMessage(
              forceRefresh
                ? sourceNote
                  ? `Configuration re-fetched. ${sourceNote} Select accessory type manually if needed.`
                  : 'Configuration re-fetched — select accessory type manually if auto-detect missed it.'
                : sourceNote
                  ? `Configuration partially fetched. ${sourceNote} Select accessory type manually if needed.`
                  : 'Configuration partially fetched — select accessory type manually if auto-detect missed it.',
            );
            return true;
          }
          setFetchMessage(
            forceRefresh
              ? sourceNote
                ? `Configuration re-fetched. ${sourceNote}`
                : 'Configuration re-fetched from internet — review and adjust if needed.'
              : sourceNote
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
          message.message ??
            'Auto-fetch failed — enter details manually or tap Auto fetch to retry.',
        );
        return false;
      } finally {
        setFetching(false);
      }
    },
    [applyAccessorySpec, brandName, identifier, identifierType],
  );

  useEffect(() => {
    if (!open || step !== 'specs' || mode !== 'new' || !identifier.trim()) {
      return;
    }
    const fetchKey = `${identifierType}:${identifier.trim().toLowerCase()}`;
    if (autoFetchKeyRef.current === fetchKey) {
      return;
    }
    autoFetchKeyRef.current = fetchKey;
    const forceRefresh = forceRefreshOnNextSpecsFetch.current;
    forceRefreshOnNextSpecsFetch.current = false;
    void runAutoFetch(forceRefresh);
  }, [open, step, mode, identifier, identifierType, runAutoFetch]);

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
    const trimmed = identifier.trim();
    if (!trimmed) return;

    setChecking(true);
    setError(null);
    setFetchMessage(null);

    try {
      const existing = findAccessoryByIdentifier(productModels, trimmed, brandId);
      if (existing) {
        const lookup = await lookupExistingModelInventory(existing);
        setExistingLookup(lookup);
        setMode('existing');
        setProductModelId(existing.id);
        applyAccessorySpec(accessoryToDisplaySpec(existing));
        setFetchMessage(
          lookup.availableSerials.length > 0
            ? `Accessory found — ${lookup.availableSerials.length} unit(s) already in stock. Add more serial numbers below.`
            : 'Accessory found — add serial numbers to restore stock for this model.',
        );
        setStep('units');
        return;
      }

      setMode('new');
      setProductModelId('');
      setExistingLookup(null);
      setModelName('');
      setResolvedModelNumber('');
      setResolvedPartNumber('');
      setAccessoryKind(null);
      setColorOptions('');
      setDescription('');
      setSpecNotes('');
      setProductImageUrl(null);
      autoFetchKeyRef.current = null;
      setStep('specs');
    } finally {
      setChecking(false);
    }
  };

  const submit = async () => {
    const validUnits = units
      .filter((unit) => unit.serial_number.trim() && unit.current_location_id)
      .map((unit) => ({
        serial_number: unit.serial_number.trim(),
        current_location_id: unit.current_location_id,
        color: defaultUnitColorFromOptions(colorOptions),
        purchase_price: unit.purchase_price.trim() ? parsePriceInput(unit.purchase_price) : null,
      }));

    if (validUnits.length === 0) {
      setError('Enter at least one serial number and location.');
      return;
    }
    if (locations.length === 0) {
      setError('No store locations are available. Add a location in Catalogue first.');
      return;
    }
    if (validUnits.some((unit) => !unit.current_location_id || unit.current_location_id <= 0)) {
      setError('Select a valid location for each serial number.');
      return;
    }
    if (!accessoryKind) {
      setError('Accessory type is required — use Auto fetch or pick a type manually.');
      return;
    }

    const entered = identifier.trim();
    const catalogPartNumber =
      identifierType === 'part_number'
        ? resolvedPartNumber.trim() || entered
        : resolvedPartNumber.trim() || null;
    const catalogModelNumber =
      resolvedModelNumber.trim() ||
      (identifierType === 'model_number' ? entered : catalogPartNumber || entered);

    const payload: AddLaptopWizardRequest = {
      brandId,
      mode,
      productModelId: mode === 'existing' ? productModelId : undefined,
      newProductModel:
        mode === 'new'
          ? sanitizeCreateProductModelPayload({
              brand_id: brandId,
              category: 'accessory',
              accessory_kind: accessoryKind,
              part_number: catalogPartNumber,
              model_number: catalogModelNumber,
              model_name: modelName.trim(),
              color_options: colorOptions.trim() || null,
              product_image_url: productImageUrl,
              notes: composeModelNotes(description, specNotes) || null,
            })
          : undefined,
      units: validUnits,
      status,
    };

    try {
      setError(null);
      await onConfirm(payload);
      onClose();
    } catch (err: unknown) {
      setError(parseApiError(err, 'Unable to add accessory inventory.'));
    }
  };

  if (!open) return null;

  const enteredIdentifier = identifier.trim();
  const identifierDisplay = identifierLabel(identifierType);

  return (
    <div className="inv-dialog-overlay" role="presentation">
      <div className="inv-dialog inv-dialog--wide animate-slide-in" role="dialog" aria-modal="true">
        <header className="inv-dialog__header">
          <div>
            <h2 className="inv-dialog__title">Add accessory — {brandName}</h2>
            <p className="inv-dialog__lead">
              Brand is fixed to {brandName}. Step {stepLabel(step, mode)}.
              {mode === 'existing' && step === 'units'
                ? ' Add serial numbers for this existing accessory.'
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
              <fieldset className="add-laptop-wizard__identifier-type">
                <legend className="form-label">Look up by</legend>
                <div className="add-laptop-wizard__identifier-options">
                  <label className="add-laptop-wizard__identifier-option">
                    <input
                      type="radio"
                      name="accessory-identifier-type"
                      checked={identifierType === 'part_number'}
                      onChange={() => setIdentifierType('part_number')}
                    />
                    <span>Part number</span>
                  </label>
                  <label className="add-laptop-wizard__identifier-option">
                    <input
                      type="radio"
                      name="accessory-identifier-type"
                      checked={identifierType === 'model_number'}
                      onChange={() => setIdentifierType('model_number')}
                    />
                    <span>Model number</span>
                  </label>
                </div>
              </fieldset>
              <label className="form-label">{identifierDisplay}</label>
              <input
                className="input col-mono"
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && identifier.trim() && !checking) {
                    void continueFromModel();
                  }
                }}
                placeholder={
                  identifierType === 'part_number' ? 'e.g. 90XB09VN-BPW000' : 'e.g. MD100'
                }
                autoFocus
              />
              <p className="add-laptop-wizard__hint">
                We check the database automatically, then fetch product details from the web using
                this {identifierType === 'part_number' ? 'part number' : 'model number'} for{' '}
                {brandName}. Existing accessories skip configuration — you only add serial numbers.
              </p>
              {fetchMessage && <p className="add-laptop-wizard__hint">{fetchMessage}</p>}
              <button
                type="button"
                className="btn btn-primary"
                disabled={!identifier.trim() || checking}
                onClick={() => void continueFromModel()}
              >
                {checking ? 'Checking database…' : 'Continue'}
              </button>
            </div>
          )}

          {step === 'specs' && (
            <div className="add-laptop-wizard__step">
              <p className="add-laptop-wizard__hint">
                New {identifierDisplay.toLowerCase()}{' '}
                <span className="col-mono">{enteredIdentifier}</span>
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
                        alt={modelName || enteredIdentifier}
                        className="inv-product-image__img"
                      />
                      <span className="inv-product-image__badge inv-product-image__badge--remote">
                        Auto fetch
                      </span>
                    </div>
                    <p className="inv-product-image__hint">
                      Preview from auto-fetch. Saved with the new accessory model.
                    </p>
                  </div>
                </div>
              ) : null}
              <label className="form-label">
                Product name
                <input
                  className="input"
                  value={modelName}
                  onChange={(event) => setModelName(event.target.value)}
                  placeholder="Official product name"
                />
              </label>
              <div className="add-laptop-wizard__actions-row">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={fetching || !enteredIdentifier}
                  onClick={() => void runAutoFetch(true)}
                >
                  {fetching ? 'Fetching…' : 'Auto fetch'}
                </button>
              </div>
              {fetchMessage && <p className="add-laptop-wizard__hint">{fetchMessage}</p>}
              <div
                className="add-laptop-wizard__tabs"
                role="tablist"
                aria-label="Accessory details"
              >
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
                    Accessory type
                    <select
                      className="input"
                      value={accessoryKind ?? ''}
                      onChange={(event) =>
                        setAccessoryKind((event.target.value as AccessoryKind) || null)
                      }
                    >
                      <option value="" disabled>
                        {fetching ? 'Fetching…' : 'Auto-detected from web lookup, or pick manually'}
                      </option>
                      {ACCESSORY_KINDS.map((kind) => (
                        <option key={kind.value} value={kind.value}>
                          {kind.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Model number
                    <input
                      className="input col-mono"
                      value={resolvedModelNumber}
                      onChange={(event) => setResolvedModelNumber(event.target.value)}
                      placeholder="Filled by auto-fetch when available"
                    />
                  </label>
                  <label>
                    Part number
                    <input
                      className="input col-mono"
                      value={resolvedPartNumber}
                      onChange={(event) => setResolvedPartNumber(event.target.value)}
                      placeholder={
                        identifierType === 'part_number'
                          ? enteredIdentifier
                          : 'Filled by auto-fetch when available'
                      }
                    />
                  </label>
                  <label className="add-laptop-wizard__field-full">
                    Colour / variant
                    <input
                      className="input"
                      value={colorOptions}
                      onChange={(event) => setColorOptions(event.target.value)}
                      placeholder="e.g. Black, White"
                    />
                  </label>
                  <label className="add-laptop-wizard__field-full">
                    Additional notes
                    <textarea
                      className="input add-laptop-wizard__textarea"
                      rows={3}
                      value={specNotes}
                      onChange={(event) => setSpecNotes(event.target.value)}
                      placeholder="Source notes or extra specs (auto-filled when available)"
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
                      onChange={(event) => setDescription(event.target.value)}
                      placeholder="Retail summary — features, compatibility, ideal customer. Auto-filled when available."
                    />
                  </label>
                </div>
              )}
              <div className="add-laptop-wizard__nav">
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => {
                    forceRefreshOnNextSpecsFetch.current = true;
                    autoFetchKeyRef.current = null;
                    setAccessoryKind(null);
                    setProductImagePreview(null);
                    setStep('model');
                  }}
                >
                  Back
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={!modelName.trim() || !accessoryKind}
                  onClick={() => setStep('units')}
                >
                  Next — serial numbers
                </button>
              </div>
            </div>
          )}

          {step === 'units' && (
            <div className="add-laptop-wizard__step">
              {mode === 'existing' && existingLookup?.model && (
                <div className="add-laptop-wizard__existing-summary">
                  <p className="add-laptop-wizard__hint">
                    {existingLookup.model.model_name}
                    {existingLookup.model.accessory_kind
                      ? ` · ${accessoryKindLabel(existingLookup.model.accessory_kind)}`
                      : ''}
                  </p>
                  {fetchMessage && <p className="add-laptop-wizard__hint">{fetchMessage}</p>}
                </div>
              )}
              <span className="inv-add-serials__hint">
                Colour is taken from the catalogue spec — no need to enter it per serial.
              </span>
              <label className="form-label">Number of units</label>
              <input
                type="number"
                className="input"
                min={1}
                max={50}
                value={unitCount}
                onChange={(event) => setUnitCount(Number(event.target.value))}
              />
              <label className="form-label">Initial status</label>
              <select
                className="input"
                value={status}
                onChange={(event) => setStatus(event.target.value as InventoryStatus)}
              >
                <option value="available">Available</option>
                <option value="received">Received</option>
              </select>
              <div className="add-laptop-wizard__units">
                <div className="add-laptop-wizard__unit-head" aria-hidden>
                  <span>Serial number</span>
                  <span>Location</span>
                  <span>Purchase price</span>
                </div>
                {units.map((unit, index) => (
                  <div
                    key={index}
                    className="add-laptop-wizard__unit-row add-laptop-wizard__unit-row--prices"
                  >
                    <input
                      className="input col-mono"
                      value={unit.serial_number}
                      onChange={(event) =>
                        setUnits((current) =>
                          current.map((row, rowIndex) =>
                            rowIndex === index
                              ? { ...row, serial_number: event.target.value }
                              : row,
                          ),
                        )
                      }
                      placeholder="Serial"
                    />
                    <select
                      className="input"
                      value={unit.current_location_id}
                      onChange={(event) =>
                        setUnits((current) =>
                          current.map((row, rowIndex) =>
                            rowIndex === index
                              ? { ...row, current_location_id: Number(event.target.value) }
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
                      className="input"
                      value={unit.purchase_price}
                      onChange={(event) =>
                        setUnits((current) =>
                          current.map((row, rowIndex) =>
                            rowIndex === index
                              ? { ...row, purchase_price: event.target.value }
                              : row,
                          ),
                        )
                      }
                      placeholder="Optional"
                    />
                  </div>
                ))}
              </div>
              <div className="add-laptop-wizard__nav">
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setStep(mode === 'existing' ? 'model' : 'specs')}
                >
                  Back
                </button>
                <button type="button" className="btn btn-primary" onClick={() => setStep('review')}>
                  Review
                </button>
              </div>
            </div>
          )}

          {step === 'review' && (
            <div className="add-laptop-wizard__step">
              {error && <div className="alert alert-danger">{error}</div>}
              <ul className="add-laptop-wizard__review-list">
                <li>
                  <span>Product</span>
                  <strong>{modelName}</strong>
                </li>
                <li>
                  <span>Type</span>
                  <strong>{accessoryKind ? accessoryKindLabel(accessoryKind) : '—'}</strong>
                </li>
                <li>
                  <span>Catalogue ID</span>
                  <strong className="col-mono">
                    {resolvedModelNumber || resolvedPartNumber || enteredIdentifier}
                    {resolvedPartNumber &&
                    resolvedModelNumber &&
                    resolvedPartNumber !== resolvedModelNumber
                      ? ` · PN ${resolvedPartNumber}`
                      : ''}
                  </strong>
                </li>
                <li>
                  <span>Units</span>
                  <strong>{units.filter((unit) => unit.serial_number.trim()).length}</strong>
                </li>
              </ul>
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
                  {loading ? 'Saving…' : 'Save accessory'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
