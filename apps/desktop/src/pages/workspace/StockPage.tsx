import { useCallback, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import {
  HierarchyBreadcrumb,
  HierarchyLayer,
  HierarchyToolbar,
  StockBrandGrid,
  StockModelCardGrid,
  StockModelDetail,
} from '../../components/stock';
import { useHierarchyScrollRef } from '../../hooks/useHierarchyScrollRef';
import { EditSellingPriceDialog } from '../../components/inventory/EditSellingPriceDialog';
import { InventoryModelEditDialog } from '../../components/inventory/admin/InventoryModelEditDialog';
import {
  useDebouncedHierarchySearch,
  useInventoryHierarchyData,
} from '../../hooks/useInventoryHierarchyData';
import { InventoryService } from '../../services/api/InventoryService';
import { ProductModelService } from '../../services/api/ProductModelService';
import { ProductImageService } from '../../services/images/ProductImageService';
import { useStockNavStore } from '../../store/useHierarchyNavStore';
import { useAuthStore } from '../../store';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';
import { P, PermissionService } from '../../services/PermissionService';
import { canEditStockProductModel } from '../../lib/inventory';
import { matchesCategoryFilter } from '../../lib/inventoryHierarchy';
import { BrandLogoImage } from '../../components/branding/BrandLogoImage';

export function StockPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const hierarchy = useInventoryHierarchyData(session?.permissions ?? []);
  const nav = useStockNavStore();
  const getScrollTop = useStockNavStore((state) => state.getScrollTop);
  const setScrollTop = useStockNavStore((state) => state.setScrollTop);
  const { ref: brandsScrollRef, saveScrollNow: saveBrandsScroll } = useHierarchyScrollRef(
    'brands',
    nav.level === 'brands',
    getScrollTop,
    setScrollTop,
    { ready: !hierarchy.loading },
  );
  const { ref: modelsScrollRef, saveScrollNow: saveModelsScroll } = useHierarchyScrollRef(
    `models-${nav.brandId ?? 0}`,
    nav.level === 'models',
    getScrollTop,
    setScrollTop,
    { ready: !hierarchy.loading },
  );
  // The hierarchy panes above are meant to scroll internally (see useHierarchyScrollRef),
  // but if the shared `#main-content` app-shell container ever ends up being the one that
  // actually overflows for a given window size, its own scrollTop still gets clamped when
  // switching levels and nothing restores it — same root cause as the Purchase list/detail
  // toggle. Save/restore it alongside the existing per-pane scroll handling as a safety net.
  const mainScrollByKeyRef = useRef<Record<string, number>>({});
  const mainScrollKey =
    nav.level === 'brands'
      ? 'brands'
      : nav.level === 'models'
        ? `models-${nav.brandId ?? 0}`
        : null;

  const saveMainScroll = useCallback(() => {
    if (!mainScrollKey) return;
    const mainEl = document.getElementById('main-content');
    if (mainEl) mainScrollByKeyRef.current[mainScrollKey] = mainEl.scrollTop;
  }, [mainScrollKey]);

  useLayoutEffect(() => {
    if (!mainScrollKey) return;
    const target = mainScrollByKeyRef.current[mainScrollKey];
    if (target == null) return;
    const mainEl = document.getElementById('main-content');
    if (!mainEl) return;
    let attempts = 0;
    const tryRestore = () => {
      mainEl.scrollTop = target;
      attempts += 1;
      if (Math.abs(mainEl.scrollTop - target) > 1 && attempts < 8) {
        requestAnimationFrame(tryRestore);
      }
    };
    tryRestore();
  }, [mainScrollKey]);

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
    const rows = hierarchy.filterStockModels(nav.brandId, debouncedSearch, nav.searchField);
    return rows.filter((row) => matchesCategoryFilter(row.model, nav.productCategoryFilter));
  }, [debouncedSearch, hierarchy, nav.brandId, nav.searchField, nav.productCategoryFilter]);

  const brandSummary = useMemo(
    () => hierarchy.brandSummaries.find((summary) => summary.brandId === nav.brandId) ?? null,
    [hierarchy.brandSummaries, nav.brandId],
  );

  const modelUnits = useMemo(
    () => (nav.modelId ? hierarchy.unitsForModel(nav.modelId, true) : []),
    [hierarchy, nav.modelId],
  );

  const permissionService = PermissionService.from(session?.permissions);
  const canEditFromStock = session ? canEditStockProductModel(session.permissions) : false;

  const handleTransfer = useCallback(
    async (itemId: string, locationId: number) => {
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
    },
    [hierarchy],
  );

  const handleDeleteSerial = useCallback(
    async (itemId: string) => {
      setActionLoading(true);
      setActionError(null);
      try {
        await InventoryService.deleteItem(itemId);
        await hierarchy.refresh();
      } catch (err: unknown) {
        const message = err as { message?: string };
        setActionError(message.message ?? 'Could not delete serial.');
      } finally {
        setActionLoading(false);
      }
    },
    [hierarchy],
  );

  const handleUpdateModelSellingPrice = useCallback(
    async (sellingPrice: number | null) => {
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
    },
    [hierarchy, priceModelId],
  );

  const handleUpdateModel = useCallback(
    async (patch: Parameters<typeof ProductModelService.updateModel>[1]) => {
      if (!editModelId) return;
      setActionLoading(true);
      setActionError(null);
      try {
        await ProductModelService.updateModel(editModelId, patch);
        if (patch.product_image_url !== undefined) {
          ProductImageService.clearCachedForModel(editModelId);
        }
        await hierarchy.refresh();
      } catch (err: unknown) {
        const message = err as { message?: string };
        setActionError(message.message ?? 'Could not update model.');
        throw err;
      } finally {
        setActionLoading(false);
      }
    },
    [editModelId, hierarchy],
  );

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
        {nav.level === 'brands' && permissionService.has(P.inventory.create) && (
          <WorkspacePageBack />
        )}
        <div>
          <h1 className="stock-page__title">Stock</h1>
          <p className="stock-page__subtitle">
            Browse available laptops and accessories by brand and model while assisting customers.
          </p>
        </div>
      </header>

      <HierarchyBreadcrumb
        minimal
        rootLabel="All brands"
        brandName={nav.brandName}
        modelLabel={nav.modelLabel}
        onRoot={() => {
          saveBrandsScroll();
          saveModelsScroll();
          saveMainScroll();
          nav.goToBrands();
        }}
        onBrand={
          nav.level === 'serials'
            ? () => {
                saveModelsScroll();
                saveMainScroll();
                nav.goToModels();
              }
            : undefined
        }
        onBack={
          nav.level === 'models'
            ? () => {
                saveBrandsScroll();
                saveMainScroll();
                nav.goToBrands();
              }
            : nav.level === 'serials'
              ? () => {
                  saveModelsScroll();
                  saveMainScroll();
                  nav.goToModels();
                }
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
            productCategoryFilter={nav.productCategoryFilter}
            onProductCategoryFilterChange={nav.setProductCategoryFilter}
          />
          {nav.level === 'models' && nav.brandName && (
            <div className="stock-page__brand-logo" data-brand={nav.brandName.trim().toLowerCase()}>
              <BrandLogoImage
                brand={nav.brandName}
                logoFilename={brandSummary?.logoFilename ?? null}
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
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setActionError(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="stock-page__stack">
        {(nav.level === 'brands' || nav.brandId != null) && (
          <HierarchyLayer active={nav.level === 'brands'}>
            <StockBrandGrid
              ref={brandsScrollRef}
              summaries={hierarchy.brandSummaries}
              loading={hierarchy.loading}
              onSelect={(brandId, brandName) => {
                saveBrandsScroll();
                saveMainScroll();
                nav.openBrand(brandId, brandName);
              }}
            />
          </HierarchyLayer>
        )}

        {nav.brandId != null && (
          <HierarchyLayer active={nav.level === 'models'}>
            <StockModelCardGrid
              ref={modelsScrollRef}
              rows={modelRows}
              loading={hierarchy.loading}
              showPrice={nav.showSellingPrice}
              onSelect={(modelId, label) => {
                saveModelsScroll();
                saveMainScroll();
                nav.openModel(modelId, label);
              }}
            />
          </HierarchyLayer>
        )}

        {nav.level === 'serials' && selectedModel && (
          <HierarchyLayer active>
            <StockModelDetail
              model={selectedModel}
              units={modelUnits}
              locations={hierarchy.locations}
              permissions={session.permissions}
              loading={hierarchy.loading}
              onTransfer={handleTransfer}
              onDeleteSerial={handleDeleteSerial}
              actionLoading={actionLoading}
              onEditModel={canEditFromStock ? () => setEditModelId(selectedModel.id) : undefined}
              editModelLabel="Edit model & price"
            />
          </HierarchyLayer>
        )}
      </div>

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
