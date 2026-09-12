import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, X } from 'lucide-react';
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
import {
  ProductModelService,
  type AsusPriceRefreshStatus,
} from '../../services/api/ProductModelService';
import { ProductImageService } from '../../services/images/ProductImageService';
import { useStockNavStore } from '../../store/useHierarchyNavStore';
import { useAuthStore } from '../../store';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';
import { P, PermissionService } from '../../services/PermissionService';
import { canEditStockProductModel } from '../../lib/inventory';
import { matchesCategoryFilter } from '../../lib/inventoryHierarchy';
import { BrandLogoImage } from '../../components/branding/BrandLogoImage';

const ASUS_RUN_DISMISSED_KEY = 'webstudio_asus_price_run_dismissed_at';
const ASUS_RUN_POLL_INTERVAL_MS = 4000;

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

  // ASUS price refresh progress: server-tracked (see get_asus_bulk_run_status
  // on the backend) rather than component-local state, so it survives
  // navigating away and back, switching tabs, or even restarting the app —
  // any client polling the same endpoint sees the same real progress.
  const showAsusPriceBar = nav.level === 'models' && nav.brandName?.trim().toUpperCase() === 'ASUS';
  const [asusRunStatus, setAsusRunStatus] = useState<AsusPriceRefreshStatus | null>(null);
  const [asusRunStarting, setAsusRunStarting] = useState(false);
  const [asusRunError, setAsusRunError] = useState<string | null>(null);
  const [asusRunDismissedAt, setAsusRunDismissedAt] = useState<string | null>(() => {
    try {
      return localStorage.getItem(ASUS_RUN_DISMISSED_KEY);
    } catch {
      return null;
    }
  });
  const [pollNonce, setPollNonce] = useState(0);
  const refreshedForFinishedAtRef = useRef<string | null>(null);

  const fetchAsusRunStatus = useCallback(async () => {
    try {
      const status = await ProductModelService.getLivePriceRefreshStatus();
      setAsusRunStatus(status);
      return status;
    } catch {
      return null;
    }
  }, []);

  // useInventoryHierarchyData returns a fresh object every render, so a
  // ref (rather than a raw dependency) is what lets the polling effect
  // below call the latest hierarchy.refresh() without re-running itself
  // every time this component re-renders — including its OWN status
  // updates below, which would otherwise tear down and restart the
  // interval on every single poll tick, before it ever got a chance to
  // fire again on its own schedule ("frozen"/erratic instead of live).
  const hierarchyRef = useRef(hierarchy);
  useEffect(() => {
    hierarchyRef.current = hierarchy;
  });

  useEffect(() => {
    if (!showAsusPriceBar) return;
    let cancelled = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    const tick = async () => {
      const status = await fetchAsusRunStatus();
      if (cancelled || !status) return;
      if (status.in_progress > 0) {
        if (intervalId === null) {
          intervalId = setInterval(() => void tick(), ASUS_RUN_POLL_INTERVAL_MS);
        }
        return;
      }
      if (intervalId !== null) {
        clearInterval(intervalId);
        intervalId = null;
      }
      if (
        status.total > 0 &&
        status.finished_at &&
        refreshedForFinishedAtRef.current !== status.finished_at
      ) {
        refreshedForFinishedAtRef.current = status.finished_at;
        await hierarchyRef.current.refresh();
      }
    };

    void tick();
    return () => {
      cancelled = true;
      if (intervalId !== null) clearInterval(intervalId);
    };
  }, [showAsusPriceBar, pollNonce, fetchAsusRunStatus]);

  const handleUpdateAsusLivePrices = useCallback(async () => {
    setAsusRunStarting(true);
    setAsusRunError(null);
    try {
      await ProductModelService.refreshAllLivePrices();
      setPollNonce((n) => n + 1);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setAsusRunError(message.message ?? 'Could not start the ASUS price refresh.');
    } finally {
      setAsusRunStarting(false);
    }
  }, []);

  const handleDismissAsusRun = useCallback(() => {
    if (!asusRunStatus?.finished_at) return;
    setAsusRunDismissedAt(asusRunStatus.finished_at);
    try {
      localStorage.setItem(ASUS_RUN_DISMISSED_KEY, asusRunStatus.finished_at);
    } catch {
      // Best-effort persistence only — dismissing still works for this session.
    }
  }, [asusRunStatus]);

  const asusFailedIds = asusRunStatus?.failed_model_ids ?? [];

  const asusFailedLabels = useMemo(() => {
    if (asusFailedIds.length === 0) return [];
    const byId = new Map(hierarchy.models.map((m) => [m.id, m.model_number]));
    return asusFailedIds.map((id) => byId.get(id) ?? id);
  }, [asusFailedIds, hierarchy.models]);

  const asusRunFinished = Boolean(
    asusRunStatus &&
    asusRunStatus.total > 0 &&
    asusRunStatus.in_progress === 0 &&
    asusRunStatus.finished_at,
  );
  const asusRunUnseen = Boolean(
    asusRunFinished && asusRunStatus!.finished_at !== asusRunDismissedAt,
  );

  const asusRunMessage = useMemo(() => {
    if (!asusRunStatus || asusRunStatus.total === 0) return null;
    if (asusRunStatus.in_progress > 0) {
      return `Refreshing ASUS prices — ${asusRunStatus.completed} of ${asusRunStatus.total} done…`;
    }
    if (asusRunUnseen) {
      const okCount = asusRunStatus.total - asusFailedIds.length;
      return asusFailedIds.length > 0
        ? `Done — ${okCount} of ${asusRunStatus.total} updated, ${asusFailedIds.length} not found.`
        : `Done — refreshed ${asusRunStatus.total} ASUS model(s).`;
    }
    return null;
  }, [asusRunStatus, asusRunUnseen, asusFailedIds.length]);

  // The "Retry failed" action stays available even after the banner is
  // dismissed — dismissing just clears the summary text, not the ability to
  // go fix the ones that didn't resolve.
  const asusRunShowDismiss = asusRunUnseen;
  const asusRunShowRetry = asusRunFinished && asusFailedIds.length > 0;

  const asusRunActive = (asusRunStatus?.in_progress ?? 0) > 0;
  const [asusRetrying, setAsusRetrying] = useState(false);

  const handleRetryFailedAsusPrices = useCallback(async () => {
    setAsusRetrying(true);
    setAsusRunError(null);
    try {
      await ProductModelService.retryFailedLivePrices();
      setPollNonce((n) => n + 1);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setAsusRunError(message.message ?? 'Could not retry the failed ASUS prices.');
    } finally {
      setAsusRetrying(false);
    }
  }, []);

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
          {showAsusPriceBar && (
            <>
              <label className="stock-page__price-toggle">
                <input
                  type="checkbox"
                  checked={nav.showLivePrice}
                  onChange={(event) => nav.setShowLivePrice(event.target.checked)}
                />
                <span>Show ASUS price on cards</span>
              </label>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => void handleUpdateAsusLivePrices()}
                disabled={asusRunStarting || asusRunActive}
              >
                {asusRunStarting ? 'Starting…' : asusRunActive ? 'Refreshing…' : 'Update prices'}
              </button>
              {asusRunMessage && (
                <span className="stock-page__asus-price-notice">
                  {asusRunMessage}
                  {asusRunShowDismiss && (
                    <button
                      type="button"
                      className="stock-page__asus-price-notice-dismiss"
                      onClick={handleDismissAsusRun}
                      aria-label="Dismiss"
                    >
                      <X size={13} aria-hidden />
                    </button>
                  )}
                </span>
              )}
              {asusRunShowRetry && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => void handleRetryFailedAsusPrices()}
                  disabled={asusRetrying || asusRunActive}
                  title={
                    asusFailedLabels.length > 0
                      ? `Not found: ${asusFailedLabels.join(', ')}`
                      : undefined
                  }
                >
                  {asusRetrying ? 'Retrying…' : `Retry failed (${asusFailedIds.length})`}
                </button>
              )}
              {asusRunError && (
                <span className="stock-page__asus-price-notice stock-page__asus-price-notice--error">
                  {asusRunError}
                </span>
              )}
            </>
          )}
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
              showLivePrice={nav.showLivePrice}
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
              showSellingPrice={nav.showSellingPrice}
              showAsusPrice={nav.showLivePrice}
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
