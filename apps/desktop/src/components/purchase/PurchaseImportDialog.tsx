import { useEffect, useMemo, useState } from 'react';
import { Plus, Trash2, X } from 'lucide-react';
import { parseApiError } from '../../lib/apiError';
import { stripBrandPrefix } from '../../lib/catalogue';
import { defaultUnitColorFromOptions } from '../../lib/inventoryDomain';
import { parsePriceInput } from '../../lib/inventoryPrice';
import { BrandService, type Brand } from '../../services/api/BrandService';
import { LocationService, type Location } from '../../services/api/LocationService';
import { ProductModelService, type ProductModel } from '../../services/api/ProductModelService';
import type { InventoryStatus } from '../../services/api/InventoryService';
import {
  PurchaseService,
  type MatchAccessoryResponse,
  type MatchModelResponse,
  type PurchaseModelGroup,
  type PurchaseVoucherDetail,
} from '../../services/api/PurchaseService';
import { AddLaptopWizard, type AddLaptopWizardRequest } from '../inventory/AddLaptopWizard';
import { AddAccessoryWizard } from '../inventory/AddAccessoryWizard';
import { ConfirmPurchaseImportDialog } from './ConfirmPurchaseImportDialog';

type ItemType = '' | 'laptop' | 'accessory';

interface Props {
  open: boolean;
  voucher: PurchaseVoucherDetail;
  group: PurchaseModelGroup;
  onClose: () => void;
  onImported: () => void;
}

const NEW_MODEL = '__new__';

export function PurchaseImportDialog({
  open,
  voucher,
  group,
  onClose,
  onImported,
}: Props): JSX.Element | null {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [brandModels, setBrandModels] = useState<ProductModel[]>([]);
  const [brandId, setBrandId] = useState<number>(0);
  const [itemType, setItemType] = useState<ItemType>('');
  const [match, setMatch] = useState<MatchModelResponse | null>(null);
  const [accMatch, setAccMatch] = useState<MatchAccessoryResponse | null>(null);
  const [matching, setMatching] = useState(false);
  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [serials, setSerials] = useState<string[]>([]);
  const [locationId, setLocationId] = useState<number>(0);
  const [purchasePrice, setPurchasePrice] = useState<string>('');
  const [status, setStatus] = useState<InventoryStatus>('available');
  const [error, setError] = useState<string | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Serials the backend already found in IMS (checked against the whole
  // database when the voucher detail is loaded). These are "already added":
  // they are skipped at import time instead of blocking the remaining units.
  const knownDuplicates = useMemo(() => {
    const set = new Set<string>();
    for (const cell of group.serials) {
      if (cell.is_duplicate) set.add(cell.serial_number.trim().toUpperCase());
    }
    return set;
  }, [group.serials]);

  // Default per-unit purchase price from Tally = line total ÷ quantity. Always editable.
  const defaultUnitPrice = useMemo(() => {
    const total = group.line_total == null ? NaN : Number(group.line_total);
    const qty = group.quantity > 0 ? group.quantity : group.serials.length;
    if (!Number.isFinite(total) || total <= 0 || qty <= 0) return '';
    const unit = total / qty;
    if (!Number.isFinite(unit) || unit <= 0) return '';
    return (Math.round(unit * 100) / 100).toString();
  }, [group.line_total, group.quantity, group.serials.length]);

  useEffect(() => {
    if (!open) return;
    setBrandId(0);
    setItemType('');
    setMatch(null);
    setAccMatch(null);
    setSelectedModelId('');
    setBrandModels([]);
    const fromTally = group.serials.map((cell) => cell.serial_number);
    const qty = group.quantity > 0 ? group.quantity : fromTally.length;
    while (fromTally.length < qty) fromTally.push('');
    setSerials(fromTally);
    setPurchasePrice(defaultUnitPrice);
    setStatus('available');
    setError(null);
    setShowWizard(false);
    setShowConfirm(false);
    void (async () => {
      try {
        const [brandList, locationList] = await Promise.all([
          BrandService.listBrands(),
          LocationService.listLocations(),
        ]);
        setBrands(brandList.filter((b) => b.is_active));
        setLocations(locationList);
        setLocationId(locationList[0]?.id ?? 0);
      } catch (err) {
        setError(parseApiError(err, 'Failed to load brands and locations.'));
      }
    })();
  }, [open, group.serials, group.quantity, defaultUnitPrice]);

  const selectedModel = brandModels.find((m) => m.id === selectedModelId) ?? null;

  const handleBrandChange = async (nextBrandId: number) => {
    setBrandId(nextBrandId);
    setItemType('');
    setMatch(null);
    setAccMatch(null);
    setSelectedModelId('');
    setBrandModels([]);
    setShowWizard(false);
    setError(null);
    if (!nextBrandId) return;
    try {
      const models = await ProductModelService.listModels(nextBrandId);
      setBrandModels(models);
    } catch (err) {
      setError(parseApiError(err, 'Failed to load brand catalogue.'));
    }
  };

  const chooseItemType = async (next: ItemType) => {
    setItemType(next);
    setMatch(null);
    setAccMatch(null);
    setSelectedModelId('');
    setShowWizard(false);
    setError(null);
    if (!next || !brandId) return;
    setMatching(true);
    try {
      if (next === 'laptop') {
        const result = await PurchaseService.matchModel(brandId, group.stock_item_name);
        setMatch(result);
        if (result.auto_selected_model_id) setSelectedModelId(result.auto_selected_model_id);
      } else {
        const result = await PurchaseService.matchAccessory(brandId, group.stock_item_name);
        setAccMatch(result);
        if (result.auto_selected_model_id) setSelectedModelId(result.auto_selected_model_id);
      }
    } catch (err) {
      setError(parseApiError(err, 'Failed to search the catalogue within brand.'));
    } finally {
      setMatching(false);
    }
  };

  const alreadyAddedCount = serials.filter((serial) =>
    knownDuplicates.has(serial.trim().toUpperCase()),
  ).length;
  const emptyCount = serials.filter((serial) => !serial.trim()).length;
  const uniqueCount = new Set(serials.map((s) => s.trim().toUpperCase()).filter(Boolean)).size;
  const hasInternalDuplicates = uniqueCount !== serials.filter((s) => s.trim()).length;
  // Units that are NOT already in IMS — the ones this import will create.
  const newUnitCount = serials.filter(
    (serial) => serial.trim() && !knownDuplicates.has(serial.trim().toUpperCase()),
  ).length;
  const canImportExisting =
    !!selectedModel &&
    serials.length > 0 &&
    emptyCount === 0 &&
    newUnitCount > 0 &&
    !hasInternalDuplicates;

  const resolvedColor = defaultUnitColorFromOptions(selectedModel?.color_options);
  const locationName = locations.find((l) => l.id === locationId)?.name ?? '—';
  const selectedBrand = brands.find((b) => b.id === brandId);
  const brandName = selectedBrand?.name ?? '';
  // Brand-free seed for the Add Model / Add Accessory wizards so "ASUS" is not
  // carried into the model number/name or the internet spec lookup.
  const strippedStockName = stripBrandPrefix(
    group.stock_item_name,
    brandName,
    selectedBrand?.short_name,
  );

  const runExistingImport = async () => {
    if (!selectedModel) return;
    setSubmitting(true);
    setError(null);
    try {
      await PurchaseService.importGroup({
        voucher_id: voucher.id,
        group_key: group.group_key,
        brand_id: brandId,
        mode: 'existing',
        product_model_id: selectedModel.id,
        serial_numbers: serials.map((s) => s.trim()).filter(Boolean),
        color: resolvedColor,
        current_location_id: locationId,
        status,
        purchase_price: purchasePrice.trim() ? parsePriceInput(purchasePrice) : null,
        // Backend re-checks the whole database and skips serials that already
        // exist ("already added") so the remaining new units still import.
        skip_existing_serials: true,
      });
      setShowConfirm(false);
      onImported();
    } catch (err) {
      setError(parseApiError(err, 'Import failed. Nothing was changed.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleWizardConfirm = async (payload: AddLaptopWizardRequest) => {
    const wizardSerials = payload.units.map((u) => u.serial_number.trim()).filter(Boolean);
    const first = payload.units[0];
    await PurchaseService.importGroup({
      voucher_id: voucher.id,
      group_key: group.group_key,
      brand_id: brandId,
      mode: 'new',
      new_product_model: payload.newProductModel,
      serial_numbers: wizardSerials,
      color: first?.color ?? 'Not specified',
      current_location_id: first?.current_location_id ?? locationId,
      status: payload.status ?? 'available',
      purchase_price: first?.purchase_price ?? null,
      skip_existing_serials: true,
    });
    onImported();
  };

  if (!open) return null;

  // New-model path (accessory): hand off to the existing Add Accessory wizard.
  if (showWizard && brandId && itemType === 'accessory') {
    return (
      <AddAccessoryWizard
        open
        brandId={brandId}
        brandName={brandName}
        allowDuplicateSerials={
          brands.find((b) => b.id === brandId)?.allow_duplicate_serials ?? false
        }
        locations={locations}
        productModels={brandModels}
        loading={submitting}
        onClose={() => setShowWizard(false)}
        onConfirm={handleWizardConfirm}
        initialIdentifier={accMatch?.normalized_query ?? strippedStockName}
        initialIdentifierType="model_number"
        initialModelName={strippedStockName}
        initialSerials={group.serials.map((cell) => cell.serial_number)}
        initialPurchasePrice={defaultUnitPrice}
        titleOverride={`Add accessory — ${brandName} (Purchase ${voucher.voucher_number})`}
        submitLabelOverride="Import to inventory"
      />
    );
  }

  // New-model path (laptop): hand off to the existing Add Model wizard (fully reused).
  if (showWizard && brandId) {
    return (
      <AddLaptopWizard
        open
        brandId={brandId}
        brandName={brandName}
        locations={locations}
        productModels={brandModels}
        loading={submitting}
        onClose={() => setShowWizard(false)}
        onConfirm={handleWizardConfirm}
        initialModelNumber={match?.normalized_model_number ?? strippedStockName}
        initialModelName={strippedStockName}
        initialSerials={group.serials.map((cell) => cell.serial_number)}
        initialPurchasePrice={defaultUnitPrice}
        titleOverride={`Add model — ${brandName} (Purchase ${voucher.voucher_number})`}
        submitLabelOverride="Import to inventory"
      />
    );
  }

  return (
    <div className="inv-dialog-overlay" role="presentation">
      <div className="inv-dialog inv-dialog--wide animate-slide-in" role="dialog" aria-modal="true">
        <header className="inv-dialog__header">
          <div>
            <h2 className="inv-dialog__title">Import — {group.stock_item_name}</h2>
            <p className="inv-dialog__lead">
              Supplier {voucher.supplier_name ?? '—'} · Purchase {voucher.voucher_number} · Qty{' '}
              {group.quantity}
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

        <div className="inv-dialog__body" style={{ display: 'grid', gap: 16 }}>
          {/* Step 1 — Brand */}
          <div>
            <label className="form-label">Brand</label>
            <select
              className="input"
              value={brandId}
              onChange={(e) => void handleBrandChange(Number(e.target.value))}
            >
              <option value={0}>Select a brand…</option>
              {brands.map((brand) => (
                <option key={brand.id} value={brand.id}>
                  {brand.name}
                </option>
              ))}
            </select>
            <p className="add-laptop-wizard__hint">
              The selected brand determines which catalogue is searched.
            </p>
          </div>

          {/* Step 2 — Item type (Laptop vs Accessory) */}
          {brandId > 0 && (
            <div>
              <label className="form-label">Item type</label>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  type="button"
                  className={
                    itemType === 'laptop' ? 'btn btn-secondary btn-sm' : 'btn btn-ghost btn-sm'
                  }
                  onClick={() => void chooseItemType('laptop')}
                >
                  Laptop
                </button>
                <button
                  type="button"
                  className={
                    itemType === 'accessory' ? 'btn btn-secondary btn-sm' : 'btn btn-ghost btn-sm'
                  }
                  onClick={() => void chooseItemType('accessory')}
                >
                  Accessory
                </button>
              </div>
              <p className="add-laptop-wizard__hint">
                Choose whether this purchase line is a laptop (serial/model match) or an accessory
                (searched by part number &amp; model name).
              </p>
            </div>
          )}

          {/* Step 3 — Model / accessory match within brand */}
          {brandId > 0 && itemType && (
            <div>
              <label className="form-label">
                {itemType === 'accessory' ? 'Accessory' : 'Model'}
              </label>
              {matching ? (
                <p className="add-laptop-wizard__hint">
                  Searching {itemType === 'accessory' ? 'accessories' : 'models'} within {brandName}
                  …
                </p>
              ) : itemType === 'laptop' ? (
                <>
                  <select
                    className="input"
                    value={selectedModelId}
                    onChange={(e) => {
                      const value = e.target.value;
                      setSelectedModelId(value);
                      if (value === NEW_MODEL) {
                        setShowWizard(true);
                      }
                    }}
                  >
                    <option value="">Select model…</option>
                    {match?.matches.map((m) => (
                      <option key={m.id} value={m.id} disabled={!m.is_active}>
                        {m.model_number} — {m.model_name}
                        {m.match_kind === 'partial' ? ' (possible match)' : ''}
                        {m.is_active ? '' : ' (archived)'}
                      </option>
                    ))}
                    <option value={NEW_MODEL}>+ Create new model (Add Model wizard)</option>
                  </select>
                  {match && (
                    <p className="add-laptop-wizard__hint">
                      Normalized: <span className="col-mono">{match.normalized_model_number}</span>.{' '}
                      {match.auto_selected_model_id
                        ? 'Existing model found — new serial numbers will be appended. You can change the selection.'
                        : match.matches.length === 0
                          ? 'No existing model matched — create a new model.'
                          : match.matches.some((m) => m.match_kind === 'partial')
                            ? 'Possible match(es) found — select one to append serials, or create a new model if it is a different model.'
                            : 'Select the matching model or create a new one.'}
                    </p>
                  )}
                </>
              ) : (
                <>
                  <select
                    className="input"
                    value={selectedModelId}
                    onChange={(e) => {
                      const value = e.target.value;
                      setSelectedModelId(value);
                      if (value === NEW_MODEL) {
                        setShowWizard(true);
                      }
                    }}
                  >
                    <option value="">Select accessory…</option>
                    {accMatch?.matches.map((m) => (
                      <option key={m.id} value={m.id} disabled={!m.is_active}>
                        {m.model_number} — {m.model_name}
                        {m.part_number ? ` · PN ${m.part_number}` : ''} ({Math.round(m.score * 100)}
                        % match){m.is_active ? '' : ' (archived)'}
                      </option>
                    ))}
                    <option value={NEW_MODEL}>+ Create new accessory (Add Accessory wizard)</option>
                  </select>
                  {accMatch && (
                    <p className="add-laptop-wizard__hint">
                      Searched: <span className="col-mono">{accMatch.normalized_query}</span>.{' '}
                      {accMatch.auto_selected_model_id
                        ? 'Matching accessory found — new serial numbers will be appended. You can change the selection.'
                        : accMatch.matches.length === 0
                          ? 'No matching accessory found — create a new accessory.'
                          : 'Select the closest accessory or create a new one.'}
                    </p>
                  )}
                </>
              )}
            </div>
          )}

          {/* Step 3 — Serials + location + price (existing model append) */}
          {selectedModel && (
            <>
              <div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <label className="form-label">
                    Serial numbers ({serials.filter((s) => s.trim()).length} / Qty {group.quantity})
                  </label>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => setSerials((cur) => [...cur, ''])}
                  >
                    <Plus size={12} aria-hidden /> Add serial
                  </button>
                </div>
                <div style={{ display: 'grid', gap: 6 }}>
                  {serials.map((serial, index) => {
                    const isAlreadyAdded = knownDuplicates.has(serial.trim().toUpperCase());
                    return (
                      <div key={index} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <input
                          className="input col-mono"
                          style={isAlreadyAdded ? { opacity: 0.6 } : undefined}
                          value={serial}
                          placeholder={`Serial ${index + 1}`}
                          onChange={(e) =>
                            setSerials((cur) =>
                              cur.map((s, i) => (i === index ? e.target.value : s)),
                            )
                          }
                        />
                        {isAlreadyAdded && (
                          <span
                            className="badge badge-warning"
                            title="This serial already exists in IMS — it will be skipped, not re-imported."
                          >
                            Already added
                          </span>
                        )}
                        <button
                          type="button"
                          className="app-toolbar-icon-btn"
                          aria-label="Remove serial"
                          onClick={() => setSerials((cur) => cur.filter((_, i) => i !== index))}
                        >
                          <Trash2 size={14} aria-hidden />
                        </button>
                      </div>
                    );
                  })}
                </div>
                {alreadyAddedCount > 0 && (
                  <p className="add-laptop-wizard__hint">
                    {alreadyAddedCount} serial(s) already exist in IMS — they will be skipped and
                    only the {newUnitCount} new unit(s) will be imported.
                  </p>
                )}
                {alreadyAddedCount > 0 && newUnitCount === 0 && (
                  <p className="inv-dialog__error">
                    Every serial in this group is already in IMS — nothing left to import.
                  </p>
                )}
                {hasInternalDuplicates && (
                  <p className="inv-dialog__error">The serial list contains repeated values.</p>
                )}
              </div>

              <div className="inv-dialog__grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label className="form-label">Location (applied to all)</label>
                  <select
                    className="input"
                    value={locationId}
                    onChange={(e) => setLocationId(Number(e.target.value))}
                  >
                    {locations.map((location) => (
                      <option key={location.id} value={location.id}>
                        {location.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="form-label">Purchase price (applied to all)</label>
                  <input
                    className="input inv-price-input"
                    inputMode="decimal"
                    placeholder="Optional"
                    value={purchasePrice}
                    onChange={(e) => setPurchasePrice(e.target.value)}
                  />
                </div>
                <div>
                  <label className="form-label">Initial status</label>
                  <select
                    className="input"
                    value={status}
                    onChange={(e) => setStatus(e.target.value as InventoryStatus)}
                  >
                    <option value="received">Received</option>
                    <option value="available">Available</option>
                  </select>
                </div>
                <div>
                  <label className="form-label">Colour</label>
                  <input className="input" value={resolvedColor} readOnly />
                </div>
              </div>
            </>
          )}

          {error && <p className="inv-dialog__error">{error}</p>}
        </div>

        <footer className="inv-dialog__footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          {selectedModel && (
            <button
              type="button"
              className="btn btn-primary"
              disabled={!canImportExisting}
              onClick={() => setShowConfirm(true)}
            >
              Review &amp; import
            </button>
          )}
        </footer>
      </div>

      <ConfirmPurchaseImportDialog
        open={showConfirm}
        loading={submitting}
        error={error}
        onCancel={() => setShowConfirm(false)}
        onConfirm={() => void runExistingImport()}
        summary={{
          supplier: voucher.supplier_name ?? '',
          brand: brandName,
          model: selectedModel ? `${selectedModel.model_number} — ${selectedModel.model_name}` : '',
          existingModel: true,
          quantity: newUnitCount,
          serialCount: newUnitCount,
          alreadyAddedCount,
          destination: 'Inventory (Tally Purchase)',
          location: locationName,
          purchasePrice: purchasePrice.trim() ? purchasePrice.trim() : '—',
        }}
      />
    </div>
  );
}
