import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import {
  AdminBrandSummary,
  AdminModelTable,
  AdminSerialTable,
  InvModelSerialHero,
} from '../../components/inventory/admin';
import { InventoryModelEditDialog } from '../../components/inventory/admin/InventoryModelEditDialog';
import { AddLaptopWizard } from '../../components/inventory/AddLaptopWizard';
import { AddAccessoryWizard } from '../../components/inventory/AddAccessoryWizard';
import { InventoryDetailDrawer } from '../../components/inventory/InventoryDetailDrawer';
import { MarkSoldDialog } from '../../components/inventory/MarkSoldDialog';
import { HierarchyBreadcrumb, HierarchyToolbar, StockBrandGrid } from '../../components/stock';
import {
  useDebouncedHierarchySearch,
  useInventoryHierarchyData,
} from '../../hooks/useInventoryHierarchyData';
import { useInventoryWorkspace } from '../../hooks/useInventoryWorkspace';
import { canArchiveProductModels, canWriteInventory } from '../../lib/inventory';
import { matchesCategoryFilter } from '../../lib/inventoryHierarchy';
import { InventoryService } from '../../services/api/InventoryService';
import { ProductModelService } from '../../services/api/ProductModelService';
import { ProductImageService } from '../../services/images/ProductImageService';
import { useInventoryNavStore } from '../../store/useHierarchyNavStore';
import { useAuthStore, useNavigationStore } from '../../store';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';

export function InventoryPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const setRoute = useNavigationStore((state) => state.setRoute);
  const hierarchy = useInventoryHierarchyData(session?.permissions ?? []);
  const workspace = useInventoryWorkspace(session?.permissions ?? []);
  const nav = useInventoryNavStore();
  const debouncedSearch = useDebouncedHierarchySearch(nav.search);
  const [addOpen, setAddOpen] = useState(false);
  const [addAccessoryOpen, setAddAccessoryOpen] = useState(false);
  const [markSoldOpen, setMarkSoldOpen] = useState(false);
  const [markSoldItemId, setMarkSoldItemId] = useState<string | null>(null);
  const [editModelId, setEditModelId] = useState<string | null>(null);
  const [modelActionLoading, setModelActionLoading] = useState(false);

  const canWrite = session ? canWriteInventory(session.permissions) : false;
  const canArchiveModel = session ? canArchiveProductModels(session.permissions) : false;

  useEffect(() => {
    if (session && !canWrite) {
      setRoute('stock');
    }
  }, [canWrite, session, setRoute]);

  useEffect(
    () => () => {
      useInventoryNavStore.getState().reset();
    },
    [],
  );

  const brandSummary = useMemo(
    () => hierarchy.brandSummaries.find((row) => row.brandId === nav.brandId) ?? null,
    [hierarchy.brandSummaries, nav.brandId],
  );

  const filteredModels = useMemo(() => {
    if (!nav.brandId) return [];
    let rows = hierarchy.filterInventoryModels(nav.brandId, debouncedSearch, nav.searchField);
    if (!nav.showZeroStock) {
      rows = rows.filter((row) => row.availableUnits > 0);
    }
    rows = rows.filter((row) => matchesCategoryFilter(row.model, nav.productCategoryFilter));
    return rows;
  }, [
    debouncedSearch,
    hierarchy,
    nav.brandId,
    nav.searchField,
    nav.showZeroStock,
    nav.productCategoryFilter,
  ]);

  const serialUnits = useMemo(
    () => (nav.modelId ? hierarchy.unitsForModel(nav.modelId, false) : []),
    [hierarchy, nav.modelId],
  );

  const selectedModel = useMemo(
    () => hierarchy.models.find((model) => model.id === nav.modelId) ?? null,
    [hierarchy.models, nav.modelId],
  );

  const editModel = useMemo(
    () =>
      editModelId ? (hierarchy.models.find((model) => model.id === editModelId) ?? null) : null,
    [editModelId, hierarchy.models],
  );

  const markSoldItem = useMemo(
    () => serialUnits.find((item) => item.id === markSoldItemId) ?? workspace.selectedItem,
    [markSoldItemId, serialUnits, workspace.selectedItem],
  );

  const handleTransfer = useCallback(
    async (itemId: string, locationId: number) => {
      await InventoryService.transferLocation(itemId, locationId);
      if (workspace.selectedId === itemId) {
        await workspace.refreshSelected();
      }
      await hierarchy.refresh();
      await workspace.refresh();
    },
    [hierarchy, workspace],
  );

  const handleMarkSold = useCallback(
    (itemId: string) => {
      workspace.selectItem(itemId);
      setMarkSoldItemId(itemId);
      setMarkSoldOpen(true);
    },
    [workspace],
  );

  const handleUpdateModel = useCallback(
    async (patch: Parameters<typeof ProductModelService.updateModel>[1]) => {
      if (!editModel) return;
      setModelActionLoading(true);
      try {
        await ProductModelService.updateModel(editModel.id, patch);
        if (patch.product_image_url !== undefined) {
          ProductImageService.clearCachedForModel(editModel.id);
        }
        await hierarchy.refresh();
        await workspace.refresh();
        if (workspace.selectedItem?.product_model_id === editModel.id) {
          await workspace.refreshSelected();
        }
      } finally {
        setModelActionLoading(false);
      }
    },
    [editModel, hierarchy, workspace],
  );

  const handleDeleteModel = useCallback(async () => {
    if (!editModel) return;
    setModelActionLoading(true);
    try {
      await ProductModelService.deleteModel(editModel.id);
      setEditModelId(null);
      if (nav.modelId === editModel.id) {
        nav.goToModels();
      }
      await hierarchy.refresh();
      await workspace.refresh();
    } finally {
      setModelActionLoading(false);
    }
  }, [editModel, hierarchy, nav, workspace]);

  const handleAddComplete = useCallback(
    async (payload: Parameters<typeof workspace.addLaptopWizard>[0]) => {
      await workspace.addLaptopWizard(payload);
      await hierarchy.refresh();
    },
    [hierarchy, workspace],
  );

  if (!session) {
    return (
      <div className="inv-page">
        <p>Sign in to manage inventory.</p>
      </div>
    );
  }

  if (!canWrite) {
    return (
      <div className="inv-page">
        <p>Redirecting to Stock…</p>
      </div>
    );
  }

  return (
    <div className="inv-page inv-page--hierarchy animate-fade-in">
      <header className="inv-page__header">
        {nav.level === 'brands' && <WorkspacePageBack />}
        <div>
          <h1 className="inv-page__title">Inventory</h1>
          <p className="inv-page__subtitle">Manage stock by brand, model, and serial number.</p>
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
        backLabel={nav.level === 'serials' ? 'Back to models' : 'Back to brands'}
      />

      {nav.level === 'models' && (
        <AdminBrandSummary summary={brandSummary} brandName={nav.brandName} />
      )}

      {nav.level !== 'serials' && (
        <HierarchyToolbar
          search={nav.search}
          onSearchChange={nav.setSearch}
          searchField={nav.searchField}
          onSearchFieldChange={nav.setSearchField}
          productCategoryFilter={nav.productCategoryFilter}
          onProductCategoryFilterChange={nav.setProductCategoryFilter}
          showZeroStock={nav.showZeroStock}
          onToggleZeroStock={nav.level === 'models' ? nav.setShowZeroStock : undefined}
        />
      )}

      {(hierarchy.error || workspace.actionError) && (
        <div className="alert alert-danger inv-page__alert">
          <AlertCircle size={14} aria-hidden />
          <span>{hierarchy.error ?? workspace.actionError}</span>
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
        <AdminModelTable
          rows={filteredModels}
          loading={hierarchy.loading}
          onSelect={(modelId, label) => {
            workspace.selectItem(null);
            nav.openModel(modelId, label);
          }}
          onAddLaptop={() => setAddOpen(true)}
          onAddAccessory={() => setAddAccessoryOpen(true)}
          onEditModel={setEditModelId}
        />
      )}

      {nav.level === 'serials' && nav.modelId && selectedModel && (
        <InvModelSerialHero
          model={selectedModel}
          unitCount={serialUnits.length}
          availableCount={
            serialUnits.filter((unit) => unit.status === 'available' && !unit.is_archived).length
          }
          onEditModel={() => setEditModelId(selectedModel.id)}
        />
      )}

      {nav.level === 'serials' && nav.modelId && (
        <div
          className={`inv-page__body ${workspace.selectedId ? 'inv-page__body--drawer-open' : ''}`}
        >
          <AdminSerialTable
            units={serialUnits}
            locations={hierarchy.locations}
            loading={hierarchy.loading}
            selectedId={workspace.selectedId}
            onSelect={(id) => void workspace.selectItem(id)}
            onTransfer={handleTransfer}
            onMarkSold={handleMarkSold}
            actionLoading={workspace.actionLoading}
          />
          {workspace.selectedItem && (
            <InventoryDetailDrawer
              workspace={workspace}
              permissions={session.permissions}
              onTransfer={() => {}}
              onMarkSold={() => handleMarkSold(workspace.selectedItem!.id)}
              onArchive={() => void workspace.archiveItem()}
              onRestore={() => void workspace.restoreItem()}
            />
          )}
        </div>
      )}

      {nav.brandId && (
        <AddLaptopWizard
          open={addOpen}
          brandId={nav.brandId}
          brandName={nav.brandName ?? ''}
          locations={hierarchy.locations}
          productModels={hierarchy.models}
          loading={workspace.actionLoading}
          onClose={() => setAddOpen(false)}
          onConfirm={handleAddComplete}
        />
      )}

      {nav.brandId && (
        <AddAccessoryWizard
          open={addAccessoryOpen}
          brandId={nav.brandId}
          brandName={nav.brandName ?? ''}
          locations={hierarchy.locations}
          productModels={hierarchy.models}
          loading={workspace.actionLoading}
          onClose={() => setAddAccessoryOpen(false)}
          onConfirm={handleAddComplete}
        />
      )}

      {markSoldItem && (
        <MarkSoldDialog
          open={markSoldOpen}
          serialNumber={markSoldItem.serial_number}
          loading={workspace.actionLoading}
          onClose={() => setMarkSoldOpen(false)}
          onConfirm={async (payload) => {
            await workspace.markSold(payload);
            setMarkSoldOpen(false);
            await hierarchy.refresh();
          }}
        />
      )}

      <InventoryModelEditDialog
        open={editModel !== null}
        model={editModel}
        loading={modelActionLoading}
        canArchive={canArchiveModel}
        onClose={() => setEditModelId(null)}
        onConfirm={handleUpdateModel}
        onArchive={handleDeleteModel}
      />
    </div>
  );
}
