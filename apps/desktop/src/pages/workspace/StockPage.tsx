import { useCallback, useMemo, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import {
  HierarchyBreadcrumb,
  HierarchyToolbar,
  StockBrandGrid,
  StockModelCardGrid,
  StockModelDetail,
} from '../../components/stock';
import { EditSellingPriceDialog } from '../../components/inventory/EditSellingPriceDialog';
import { InventoryModelEditDialog } from '../../components/inventory/admin/InventoryModelEditDialog';
import { useDebouncedHierarchySearch, useInventoryHierarchyData } from '../../hooks/useInventoryHierarchyData';
import { InventoryService } from '../../services/api/InventoryService';
import { ProductModelService } from '../../services/api/ProductModelService';
import { useStockNavStore } from '../../store/useHierarchyNavStore';
import { useAuthStore } from '../../store';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';
import { P, PermissionService } from '../../services/PermissionService';
import { canEditProductModels, canEditSellingPrice } from '../../lib/inventory';
import { brandLogoSrc } from '../../lib/catalogue';

export function StockPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const hierarchy = useInventoryHierarchyData();
  const nav = useStockNavStore();
  const debouncedSearch = useDebouncedHierarchySearch(nav.search);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [priceModelId, setPriceModelId] = useState<string | null>(null);
  const [editModelId, setEditModelId] = useState<string | null>(null);

  const selectedModel = useMemo(
    () => hierarchy.models.find((model) => model.id === nav.modelId) ?? null,
    [hierarchy.models, nav.modelId],
  );

  const priceModel = useMemo(
    () => hierarchy.models.find((model) => model.id === priceModelId) ?? null,
    [hierarchy.models, priceModelId],
  );

  const editModel = useMemo(
    () => hierarchy.models.find((model) => model.id === editModelId) ?? null,
    [hierarchy.models, editModelId],
  );

  const modelRows = useMemo(() => {
    if (!nav.brandId) return [];
    return hierarchy.filterStockModels(nav.brandId, debouncedSearch, nav.searchField);
  }, [debouncedSearch, hierarchy, nav.brandId, nav.searchField]);

  const brandSummary = useMemo(
    () => hierarchy.brandSummaries.find((summary) => summary.brandId === nav.brandId) ?? null,
    [hierarchy.brandSummaries, nav.brandId],
  );

  const modelUnits = useMemo(() => (
    nav.modelId ? hierarchy.unitsForModel(nav.modelId, true) : []
  ), [hierarchy, nav.modelId]);

  const permissionService = PermissionService.from(session?.permissions);
  const canFullModelEdit = session ? canEditProductModels(session.permissions) : false;
  const canPriceEdit = session ? canEditSellingPrice(session.permissions) : false;
  const canEditFromStock = canFullModelEdit || canPriceEdit;
  const editModelLabel = canFullModelEdit ? 'Edit model & price' : 'Edit selling price';

  const handleTransfer = useCallback(async (itemId: string, locationId: number) => {
    setActionLoading(true);
    setActionError(null);
    try {
      await InventoryService.transferLocation(itemId, locationId);
      await hierarchy.refresh();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setActionError(message.message ?? 'Transfer failed.');
    } finally {
      setActionLoading(false);
    }
  }, [hierarchy]);

  const handleUpdateModelSellingPrice = useCallback(async (sellingPrice: number | null) => {
    if (!priceModelId) return;
    setActionLoading(true);
    setActionError(null);
    try {
      await ProductModelService.updateSellingPrice(priceModelId, { selling_price: sellingPrice });
      await hierarchy.refresh();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setActionError(message.message ?? 'Could not update selling price.');
      throw err;
    } finally {
      setActionLoading(false);
    }
  }, [hierarchy, priceModelId]);

  const handleUpdateModel = useCallback(async (
    patch: Parameters<typeof ProductModelService.updateModel>[1],
  ) => {
    if (!editModelId) return;
    setActionLoading(true);
    setActionError(null);
    try {
      await ProductModelService.updateModel(editModelId, patch);
      await hierarchy.refresh();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setActionError(message.message ?? 'Could not update model.');
      throw err;
    } finally {
      setActionLoading(false);
    }
  }, [editModelId, hierarchy]);

  if (!session) {
    return (
      <div className="stock-page">
        <p>Sign in to browse available stock.</p>
      </div>
    );
  }

  return (
    <div className="stock-page animate-fade-in">
      <header className="stock-page__header">
        {nav.level === 'brands' && permissionService.has(P.inventory.create) && <WorkspacePageBack />}
        <div>
          <h1 className="stock-page__title">Stock</h1>
          <p className="stock-page__subtitle">
            Browse available laptops by brand and model while assisting customers.
          </p>
        </div>
      </header>

      <HierarchyBreadcrumb
        minimal
        rootLabel="All brands"
        brandName={nav.brandName}
        modelLabel={nav.modelLabel}
        onRoot={() => nav.goToBrands()}
        onBrand={nav.level === 'serials' ? () => nav.goToModels() : undefined}
        onBack={
          nav.level === 'models'
            ? () => nav.goToBrands()
            : nav.level === 'serials'
              ? () => nav.goToModels()
              : undefined
        }
        backLabel={nav.level === 'serials' ? `Back to models` : 'Back to brands'}
      />

      {nav.level !== 'serials' && (
        <div className={nav.level === 'models' ? 'stock-page__toolbar-wrap' : undefined}>
          <HierarchyToolbar
            search={nav.search}
            onSearchChange={nav.setSearch}
            searchField={nav.searchField}
            onSearchFieldChange={nav.setSearchField}
          />
          {nav.level === 'models' && nav.brandName && (
            <div
              className="stock-page__brand-logo"
              data-brand={nav.brandName.trim().toLowerCase()}
            >
              <img
                src={brandLogoSrc(nav.brandName, brandSummary?.logoFilename ?? null)}
                alt=""
                className="stock-page__brand-logo-img"
              />
            </div>
          )}
        </div>
      )}

      {nav.level === 'models' && (
        <div className="stock-page__models-toolbar">
          <label className="stock-page__price-toggle">
            <input
              type="checkbox"
              checked={nav.showSellingPrice}
              onChange={(event) => nav.setShowSellingPrice(event.target.checked)}
            />
            <span>Show selling prices on cards</span>
          </label>
        </div>
      )}

      {hierarchy.error && (
        <div className="alert alert-danger stock-page__alert">
          <AlertCircle size={14} aria-hidden />
          <span>{hierarchy.error}</span>
        </div>
      )}

      {actionError && (
        <div className="alert alert-danger stock-page__alert">
          <AlertCircle size={14} aria-hidden />
          <span>{actionError}</span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setActionError(null)}>Dismiss</button>
        </div>
      )}

      {nav.level === 'brands' && (
        <StockBrandGrid
          summaries={hierarchy.brandSummaries}
          loading={hierarchy.loading}
          onSelect={(brandId, brandName) => nav.openBrand(brandId, brandName)}
        />
      )}

      {nav.level === 'models' && nav.brandId && (
        <StockModelCardGrid
          rows={modelRows}
          loading={hierarchy.loading}
          availableOnly
          showPrice={nav.showSellingPrice}
          onSelect={(modelId, label) => nav.openModel(modelId, label)}
        />
      )}

      {nav.level === 'serials' && selectedModel && (
        <StockModelDetail
          model={selectedModel}
          units={modelUnits}
          locations={hierarchy.locations}
          permissions={session.permissions}
          loading={hierarchy.loading}
          onTransfer={handleTransfer}
          actionLoading={actionLoading}
          onEditModel={canEditFromStock ? () => {
            if (canFullModelEdit) setEditModelId(selectedModel.id);
            else setPriceModelId(selectedModel.id);
          } : undefined}
          editModelLabel={editModelLabel}
        />
      )}

      <EditSellingPriceDialog
        open={priceModel !== null}
        label={priceModel ? `${priceModel.model_number} · ${priceModel.model_name}` : ''}
        currentPrice={priceModel?.selling_price}
        loading={actionLoading}
        onClose={() => setPriceModelId(null)}
        onConfirm={handleUpdateModelSellingPrice}
      />

      <InventoryModelEditDialog
        open={editModel !== null}
        model={editModel}
        loading={actionLoading}
        onClose={() => setEditModelId(null)}
        onConfirm={handleUpdateModel}
      />
    </div>
  );
}
