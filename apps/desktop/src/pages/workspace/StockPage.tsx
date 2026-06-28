import { useCallback, useMemo, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import {
  HierarchyBreadcrumb,
  HierarchyToolbar,
  StockBrandGrid,
  StockModelCardGrid,
  StockModelDetail,
} from '../../components/stock';
import { useDebouncedHierarchySearch, useInventoryHierarchyData } from '../../hooks/useInventoryHierarchyData';
import { InventoryService } from '../../services/api/InventoryService';
import { useStockNavStore } from '../../store/useHierarchyNavStore';
import { useAuthStore } from '../../store';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';

export function StockPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const hierarchy = useInventoryHierarchyData();
  const nav = useStockNavStore();
  const debouncedSearch = useDebouncedHierarchySearch(nav.search);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const selectedModel = useMemo(
    () => hierarchy.models.find((model) => model.id === nav.modelId) ?? null,
    [hierarchy.models, nav.modelId],
  );

  const modelRows = useMemo(() => {
    if (!nav.brandId) return [];
    return hierarchy.filterStockModels(nav.brandId, debouncedSearch, nav.searchField);
  }, [debouncedSearch, hierarchy, nav.brandId, nav.searchField]);

  const modelUnits = useMemo(() => (
    nav.modelId ? hierarchy.unitsForModel(nav.modelId, true) : []
  ), [hierarchy, nav.modelId]);

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

  const handleUpdateSellingPrice = useCallback(async (itemId: string, sellingPrice: number | null) => {
    setActionLoading(true);
    setActionError(null);
    try {
      await InventoryService.updateSellingPrice(itemId, { selling_price: sellingPrice });
      await hierarchy.refresh();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setActionError(message.message ?? 'Could not update selling price.');
      throw err;
    } finally {
      setActionLoading(false);
    }
  }, [hierarchy]);

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
        {nav.level === 'brands' && session.role !== 'salesperson' && <WorkspacePageBack />}
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
        <HierarchyToolbar
          search={nav.search}
          onSearchChange={nav.setSearch}
          searchField={nav.searchField}
          onSearchFieldChange={nav.setSearchField}
        />
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
          onSelect={(modelId, label) => nav.openModel(modelId, label)}
        />
      )}

      {nav.level === 'serials' && selectedModel && (
        <div className="stock-page__serials-toolbar">
          <label className="stock-page__price-toggle">
            <input
              type="checkbox"
              checked={nav.showSellingPrice}
              onChange={(event) => nav.setShowSellingPrice(event.target.checked)}
            />
            <span>Show selling prices</span>
          </label>
        </div>
      )}

      {nav.level === 'serials' && selectedModel && (
        <StockModelDetail
          model={selectedModel}
          units={modelUnits}
          locations={hierarchy.locations}
          role={session.role}
          loading={hierarchy.loading}
          showSellingPrice={nav.showSellingPrice}
          onTransfer={handleTransfer}
          onUpdateSellingPrice={handleUpdateSellingPrice}
          actionLoading={actionLoading}
        />
      )}
    </div>
  );
}
