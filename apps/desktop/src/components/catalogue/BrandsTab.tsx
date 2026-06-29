import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, MoreHorizontal } from 'lucide-react';
import { useDebounce } from '../../lib/useDebounce';
import {
  brandLogoSrc,
  catalogueStatusBadgeClass,
  catalogueStatusLabel,
  canExportCatalogue,
  canWriteCatalogue,
  catalogueActionErrorMessage,
  confirmCatalogueRemoval,
  matchesSearch,
  paginateItems,
} from '../../lib/catalogue';
import { exportRowsToCsv } from '../../lib/catalogueExport';
import type { DistributionGroup } from '../../services/api/DashboardService';
import { BrandService, type Brand, type CreateBrandRequest, type UpdateBrandRequest } from '../../services/api/BrandService';
import type { ProductModel } from '../../services/api/ProductModelService';
import { BrandFormDialog } from './BrandFormDialog';
import { CatalogueEmptyState } from './CatalogueEmptyState';
import { CataloguePagination } from './CataloguePagination';
import { CatalogueRowActionsMenu, type CatalogueRowAction } from './CatalogueRowActionsMenu';
import { CatalogueToolbar } from './CatalogueToolbar';

type BrandSortField = 'name' | 'display_order' | 'models' | 'available';

interface BrandsTabProps {
  permissions: string[];
  distributionByBrand: DistributionGroup[];
  modelCounts: Map<number, number>;
  onDataChange: () => void;
}

export function BrandsTab({ permissions, distributionByBrand, modelCounts, onDataChange }: BrandsTabProps): JSX.Element {
  const [items, setItems] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [includeArchived, setIncludeArchived] = useState(false);
  const [brandFilter, setBrandFilter] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [sortField, setSortField] = useState<BrandSortField>('display_order');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Brand | null>(null);
  const [menu, setMenu] = useState<{ brand: Brand; rect: DOMRect } | null>(null);
  const pageSize = 25;
  const debouncedSearch = useDebounce(search, 300);
  const canWrite = canWriteCatalogue(permissions);
  const canExport = canExportCatalogue(permissions);

  const stockByBrandId = useMemo(() => {
    const map = new Map<string, DistributionGroup>();
    for (const row of distributionByBrand) map.set(row.id, row);
    return map;
  }, [distributionByBrand]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await BrandService.listBrands());
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to load brands.');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    let rows = items.filter((brand) => includeArchived || brand.is_active);
    if (brandFilter) rows = rows.filter((b) => b.id === brandFilter);
    rows = rows.filter((brand) => matchesSearch(debouncedSearch, [brand.name, brand.short_name]));
    rows.sort((a, b) => {
      const dir = sortDirection === 'asc' ? 1 : -1;
      if (sortField === 'name') return a.name.localeCompare(b.name) * dir;
      if (sortField === 'display_order') return (a.display_order - b.display_order) * dir;
      if (sortField === 'models') return ((modelCounts.get(a.id) ?? 0) - (modelCounts.get(b.id) ?? 0)) * dir;
      const aStock = stockByBrandId.get(String(a.id));
      const bStock = stockByBrandId.get(String(b.id));
      if (sortField === 'available') return ((aStock?.available ?? 0) - (bStock?.available ?? 0)) * dir;
      return 0;
    });
    return rows;
  }, [items, includeArchived, brandFilter, debouncedSearch, sortField, sortDirection, modelCounts, stockByBrandId]);

  const pageItems = paginateItems(filtered, page, pageSize);

  const toggleSort = (field: BrandSortField) => {
    if (sortField === field) setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortField(field);
      setSortDirection('asc');
    }
    setPage(1);
  };

  const sortIcon = (field: BrandSortField) => {
    if (sortField !== field) return <ArrowUpDown size={12} className="cat-sort-icon cat-sort-icon--idle" />;
    return sortDirection === 'asc' ? <ArrowUp size={12} className="cat-sort-icon" /> : <ArrowDown size={12} className="cat-sort-icon" />;
  };

  const handleSave = async (payload: CreateBrandRequest | UpdateBrandRequest) => {
    setActionLoading(true);
    try {
      if (editing) await BrandService.updateBrand(editing.id, payload as UpdateBrandRequest);
      else await BrandService.createBrand(payload as CreateBrandRequest);
      await refresh();
      onDataChange();
    } finally {
      setActionLoading(false);
    }
  };

  const handleRowAction = async (action: CatalogueRowAction, brand: Brand) => {
    if (!canWrite) return;
    if (action === 'archive' && !confirmCatalogueRemoval(brand.name, 'brand')) return;

    setMenu(null);
    setActionLoading(true);
    setError(null);
    try {
      if (action === 'edit') {
        setEditing(brand);
        setDialogOpen(true);
      } else if (action === 'archive') {
        await BrandService.archiveBrand(brand.id);
        await refresh();
        onDataChange();
      } else if (action === 'restore') {
        await BrandService.restoreBrand(brand.id);
        await refresh();
        onDataChange();
      }
    } catch (err: unknown) {
      setError(catalogueActionErrorMessage(err));
    } finally {
      setActionLoading(false);
    }
  };

  const exportCsv = () => {
    exportRowsToCsv(
      'brands.csv',
      ['Name', 'Models', 'Available', 'Status'],
      filtered.map((brand) => {
        const stock = stockByBrandId.get(String(brand.id));
        return [
          brand.name,
          String(modelCounts.get(brand.id) ?? 0),
          String(stock?.available ?? 0),
          catalogueStatusLabel(brand.is_active),
        ];
      }),
    );
  };

  return (
    <div className="cat-tab-panel">
      <CatalogueToolbar
        search={search}
        onSearchChange={(v) => { setSearch(v); setPage(1); }}
        searchPlaceholder="Search brands…"
        canWrite={canWrite}
        canExport={canExport}
        onAdd={() => { setEditing(null); setDialogOpen(true); }}
        addLabel="Add brand"
        onExport={exportCsv}
        onRefresh={() => void refresh()}
        loading={loading || actionLoading}
        includeArchived={includeArchived}
        onIncludeArchivedChange={(v) => { setIncludeArchived(v); setPage(1); }}
      />

      <div className="cat-filters">
        <label className="cat-filters__field">
          <span>Brand</span>
          <select className="input" value={brandFilter ?? ''} onChange={(e) => { setBrandFilter(e.target.value ? Number(e.target.value) : null); setPage(1); }}>
            <option value="">All brands</option>
            {items.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </label>
      </div>

      {error && <div className="alert alert-danger cat-tab-panel__alert">{error}</div>}

      <div className="cat-table-shell">
        <div className="cat-table-scroll">
          <table className="table-root cat-table">
            <thead className="cat-table__head">
              <tr>
                <th>Logo</th>
                <th className="cat-table__th-sortable" onClick={() => toggleSort('name')}>Name {sortIcon('name')}</th>
                <th className="cat-table__th-sortable" onClick={() => toggleSort('models')}>Models {sortIcon('models')}</th>
                <th className="cat-table__th-sortable" onClick={() => toggleSort('available')}>Available {sortIcon('available')}</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {loading && Array.from({ length: 6 }).map((_, i) => (
                <tr key={i}>{Array.from({ length: 6 }).map((__, j) => <td key={j}><div className="skeleton cat-table__skeleton" /></td>)}</tr>
              ))}
              {!loading && pageItems.length === 0 && (
                <tr><td colSpan={6}><CatalogueEmptyState title="No brands found" description="Add a brand or adjust filters." onClearFilters={() => { setSearch(''); setBrandFilter(null); setIncludeArchived(false); }} onAdd={() => setDialogOpen(true)} canWrite={canWrite} addLabel="Add brand" /></td></tr>
              )}
              {!loading && pageItems.map((brand) => {
                const stock = stockByBrandId.get(String(brand.id));
                return (
                  <tr key={brand.id}>
                    <td><img src={brandLogoSrc(brand.name, brand.logo_filename)} alt="" className="cat-brand-logo" /></td>
                    <td>{brand.name}</td>
                    <td>{modelCounts.get(brand.id) ?? 0}</td>
                    <td>{stock?.available ?? 0}</td>
                    <td><span className={`badge ${catalogueStatusBadgeClass(brand.is_active)}`}>{catalogueStatusLabel(brand.is_active)}</span></td>
                    <td>
                      {canWrite && (
                        <button type="button" className="cat-row-action" aria-label={`Actions for ${brand.name}`} onClick={(e) => setMenu({ brand, rect: e.currentTarget.getBoundingClientRect() })}>
                          <MoreHorizontal size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <CataloguePagination page={page} pageSize={pageSize} totalItems={filtered.length} onPageChange={setPage} loading={loading} />
      </div>

      {menu && (
        <CatalogueRowActionsMenu
          label={menu.brand.name}
          canWrite={canWrite}
          isArchived={!menu.brand.is_active}
          anchorRect={menu.rect}
          onClose={() => setMenu(null)}
          onAction={(action) => void handleRowAction(action, menu.brand)}
        />
      )}

      <BrandFormDialog open={dialogOpen} brand={editing} loading={actionLoading} onClose={() => setDialogOpen(false)} onConfirm={handleSave} />
    </div>
  );
}

// helper export for parent to compute model counts
export function countModelsByBrand(models: ProductModel[]): Map<number, number> {
  const map = new Map<number, number>();
  for (const model of models) {
    map.set(model.brand_id, (map.get(model.brand_id) ?? 0) + 1);
  }
  return map;
}
