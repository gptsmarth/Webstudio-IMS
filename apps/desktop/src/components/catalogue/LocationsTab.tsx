import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, MoreHorizontal } from 'lucide-react';
import { useDebounce } from '../../lib/useDebounce';
import {
  canExportCatalogue,
  canWriteCatalogue,
  catalogueActionErrorMessage,
  catalogueStatusBadgeClass,
  catalogueStatusLabel,
  confirmCatalogueRemoval,
  locationTypeLabel,
  matchesSearch,
  paginateItems,
} from '../../lib/catalogue';
import { exportRowsToCsv } from '../../lib/catalogueExport';
import type { DistributionGroup } from '../../services/api/DashboardService';
import {
  LocationService,
  type CreateLocationRequest,
  type Location,
  type UpdateLocationRequest,
} from '../../services/api/LocationService';
import { CatalogueEmptyState } from './CatalogueEmptyState';
import { CataloguePagination } from './CataloguePagination';
import { CatalogueRowActionsMenu, type CatalogueRowAction } from './CatalogueRowActionsMenu';
import { CatalogueToolbar } from './CatalogueToolbar';
import { LocationDeleteDialog } from './LocationDeleteDialog';
import { LocationFormDialog } from './LocationFormDialog';

type LocationSortField = 'name' | 'location_type' | 'stock' | 'capacity';

interface LocationsTabProps {
  permissions: string[];
  distributionByLocation: DistributionGroup[];
  onDataChange: () => void;
}

export function LocationsTab({
  permissions,
  distributionByLocation,
  onDataChange,
}: LocationsTabProps): JSX.Element {
  const [items, setItems] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [page, setPage] = useState(1);
  const [sortField, setSortField] = useState<LocationSortField>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Location | null>(null);
  const [deleteDialog, setDeleteDialog] = useState<{
    location: Location;
    inventoryCount: number;
    movableCount: number;
  } | null>(null);
  const [menu, setMenu] = useState<{ location: Location; rect: DOMRect } | null>(null);
  const pageSize = 25;
  const debouncedSearch = useDebounce(search, 300);
  const canWrite = canWriteCatalogue(permissions);
  const canExport = canExportCatalogue(permissions);

  const stockByLocationId = useMemo(() => {
    const map = new Map<string, DistributionGroup>();
    for (const row of distributionByLocation) map.set(row.id, row);
    return map;
  }, [distributionByLocation]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await LocationService.listLocations());
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to load locations.');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    let rows = [...items];
    if (typeFilter) rows = rows.filter((loc) => loc.location_type === typeFilter);
    rows = rows.filter((loc) => matchesSearch(debouncedSearch, [loc.name, loc.location_type]));
    rows.sort((a, b) => {
      const dir = sortDirection === 'asc' ? 1 : -1;
      if (sortField === 'name') return a.name.localeCompare(b.name) * dir;
      if (sortField === 'location_type')
        return a.location_type.localeCompare(b.location_type) * dir;
      const aStock = stockByLocationId.get(String(a.id));
      const bStock = stockByLocationId.get(String(b.id));
      if (sortField === 'stock') return ((aStock?.available ?? 0) - (bStock?.available ?? 0)) * dir;
      if (sortField === 'capacity') return ((aStock?.total ?? 0) - (bStock?.total ?? 0)) * dir;
      return 0;
    });
    return rows;
  }, [items, typeFilter, debouncedSearch, sortField, sortDirection, stockByLocationId]);

  const pageItems = paginateItems(filtered, page, pageSize);

  const toggleSort = (field: LocationSortField) => {
    if (sortField === field) setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortField(field);
      setSortDirection('asc');
    }
    setPage(1);
  };

  const sortIcon = (field: LocationSortField) => {
    if (sortField !== field)
      return <ArrowUpDown size={12} className="cat-sort-icon cat-sort-icon--idle" />;
    return sortDirection === 'asc' ? (
      <ArrowUp size={12} className="cat-sort-icon" />
    ) : (
      <ArrowDown size={12} className="cat-sort-icon" />
    );
  };

  const handleSave = async (payload: CreateLocationRequest | UpdateLocationRequest) => {
    setActionLoading(true);
    try {
      if (editing)
        await LocationService.updateLocation(editing.id, payload as UpdateLocationRequest);
      else await LocationService.createLocation(payload as CreateLocationRequest);
      await refresh();
      onDataChange();
    } finally {
      setActionLoading(false);
    }
  };

  const handleRowAction = async (action: CatalogueRowAction, location: Location) => {
    if (!canWrite) return;
    if (action === 'delete' && !confirmCatalogueRemoval(location.name, 'location')) return;

    setMenu(null);
    setActionLoading(true);
    setError(null);
    try {
      if (action === 'edit') {
        setEditing(location);
        setDialogOpen(true);
      } else if (action === 'delete') {
        const preview = await LocationService.getDeletePreview(location.id);
        if (preview.requires_transfer) {
          setDeleteDialog({
            location,
            inventoryCount: preview.inventory_count,
            movableCount: preview.movable_inventory_count,
          });
          return;
        }
        await LocationService.deleteLocation(location.id);
        await refresh();
        onDataChange();
      }
    } catch (err: unknown) {
      setError(catalogueActionErrorMessage(err));
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteWithTransfer = async (transferToLocationId: number) => {
    if (!deleteDialog) return;
    setActionLoading(true);
    setError(null);
    try {
      await LocationService.deleteLocation(deleteDialog.location.id, {
        transfer_to_location_id: transferToLocationId,
      });
      setDeleteDialog(null);
      await refresh();
      onDataChange();
    } catch (err: unknown) {
      setError(catalogueActionErrorMessage(err));
      throw err;
    } finally {
      setActionLoading(false);
    }
  };

  const deleteDestinations = useMemo(() => {
    if (!deleteDialog) return [];
    return items.filter((loc) => loc.id !== deleteDialog.location.id);
  }, [deleteDialog, items]);

  const exportCsv = () => {
    exportRowsToCsv(
      'locations.csv',
      ['Location', 'Type', 'Current Stock', 'Capacity', 'Status'],
      filtered.map((loc) => {
        const stock = stockByLocationId.get(String(loc.id));
        return [
          loc.name,
          locationTypeLabel(loc.location_type),
          String(stock?.available ?? 0),
          String(stock?.total ?? 0),
          catalogueStatusLabel(loc.is_active),
        ];
      }),
    );
  };

  return (
    <div className="cat-tab-panel">
      <CatalogueToolbar
        search={search}
        onSearchChange={(v) => {
          setSearch(v);
          setPage(1);
        }}
        searchPlaceholder="Search locations…"
        canWrite={canWrite}
        canExport={canExport}
        onAdd={() => {
          setEditing(null);
          setDialogOpen(true);
        }}
        addLabel="Add location"
        onExport={exportCsv}
        onRefresh={() => void refresh()}
        loading={loading || actionLoading}
      />

      <div className="cat-filters">
        <label className="cat-filters__field">
          <span>Type</span>
          <select
            className="input"
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All types</option>
            <option value="retail_floor">Retail floor</option>
            <option value="warehouse">Warehouse</option>
            <option value="other">Other</option>
          </select>
        </label>
      </div>

      {error && <div className="alert alert-danger cat-tab-panel__alert">{error}</div>}

      <div className="cat-table-shell">
        <div className="cat-table-scroll">
          <table className="table-root cat-table">
            <thead className="cat-table__head">
              <tr>
                <th className="cat-table__th-sortable" onClick={() => toggleSort('name')}>
                  Location {sortIcon('name')}
                </th>
                <th className="cat-table__th-sortable" onClick={() => toggleSort('location_type')}>
                  Type {sortIcon('location_type')}
                </th>
                <th className="cat-table__th-sortable" onClick={() => toggleSort('stock')}>
                  Current Stock {sortIcon('stock')}
                </th>
                <th className="cat-table__th-sortable" onClick={() => toggleSort('capacity')}>
                  Capacity {sortIcon('capacity')}
                </th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {loading &&
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 6 }).map((__, j) => (
                      <td key={j}>
                        <div className="skeleton cat-table__skeleton" />
                      </td>
                    ))}
                  </tr>
                ))}
              {!loading && pageItems.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <CatalogueEmptyState
                      title="No locations found"
                      description="Add a location or adjust filters."
                      onClearFilters={() => {
                        setSearch('');
                        setTypeFilter('');
                      }}
                      onAdd={() => setDialogOpen(true)}
                      canWrite={canWrite}
                      addLabel="Add location"
                    />
                  </td>
                </tr>
              )}
              {!loading &&
                pageItems.map((location) => {
                  const stock = stockByLocationId.get(String(location.id));
                  return (
                    <tr key={location.id}>
                      <td>{location.name}</td>
                      <td>{locationTypeLabel(location.location_type)}</td>
                      <td>{stock?.available ?? 0}</td>
                      <td title="Total units at location">{stock?.total ?? 0}</td>
                      <td>
                        <span className={`badge ${catalogueStatusBadgeClass(location.is_active)}`}>
                          {catalogueStatusLabel(location.is_active)}
                        </span>
                      </td>
                      <td>
                        {canWrite && (
                          <button
                            type="button"
                            className="cat-row-action"
                            onClick={(e) =>
                              setMenu({ location, rect: e.currentTarget.getBoundingClientRect() })
                            }
                            aria-label={`Actions for ${location.name}`}
                          >
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
        <CataloguePagination
          page={page}
          pageSize={pageSize}
          totalItems={filtered.length}
          onPageChange={setPage}
          loading={loading}
        />
      </div>

      {menu && (
        <CatalogueRowActionsMenu
          label={menu.location.name}
          canWrite={canWrite}
          anchorRect={menu.rect}
          onClose={() => setMenu(null)}
          onAction={(action) => void handleRowAction(action, menu.location)}
        />
      )}

      <LocationFormDialog
        open={dialogOpen}
        location={editing}
        loading={actionLoading}
        onClose={() => setDialogOpen(false)}
        onConfirm={handleSave}
      />
      <LocationDeleteDialog
        open={deleteDialog != null}
        location={deleteDialog?.location ?? null}
        inventoryCount={deleteDialog?.inventoryCount ?? 0}
        movableCount={deleteDialog?.movableCount ?? 0}
        destinations={deleteDestinations}
        loading={actionLoading}
        onClose={() => setDeleteDialog(null)}
        onConfirm={handleDeleteWithTransfer}
      />
    </div>
  );
}
