import type { InventoryFilters, InventoryWorkspaceState } from '../../hooks/useInventoryWorkspace';
import type { Brand } from '../../services/api/BrandService';
import type { Location } from '../../services/api/LocationService';
import type { InventoryStatus } from '../../services/api/InventoryService';

interface InventoryFiltersPanelProps {
  filters: InventoryFilters;
  setFilters: InventoryWorkspaceState['setFilters'];
  resetFilters: InventoryWorkspaceState['resetFilters'];
  brands: Brand[];
  locations: Location[];
}

const STATUS_OPTIONS: Array<{ value: InventoryStatus | 'archived' | ''; label: string }> = [
  { value: '', label: 'All statuses' },
  { value: 'received', label: 'Received' },
  { value: 'available', label: 'Available' },
  { value: 'sold', label: 'Sold' },
  { value: 'archived', label: 'Archived only' },
];

export function InventoryFiltersPanel({
  filters,
  setFilters,
  resetFilters,
  brands,
  locations,
}: InventoryFiltersPanelProps): JSX.Element {
  return (
    <section className="inv-filters" aria-label="Inventory filters">
      <div className="inv-filters__grid">
        <label className="inv-filters__field">
          <span className="inv-filters__label">Brand</span>
          <select
            className="input"
            value={filters.brandId ?? ''}
            onChange={(event) => setFilters({ brandId: event.target.value ? Number(event.target.value) : null })}
          >
            <option value="">All brands</option>
            {brands.map((brand) => (
              <option key={brand.id} value={brand.id}>
                {brand.name}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-filters__field">
          <span className="inv-filters__label">Location</span>
          <select
            className="input"
            value={filters.locationId ?? ''}
            onChange={(event) => setFilters({ locationId: event.target.value ? Number(event.target.value) : null })}
          >
            <option value="">All locations</option>
            {locations.map((location) => (
              <option key={location.id} value={location.id}>
                {location.name}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-filters__field">
          <span className="inv-filters__label">Status</span>
          <select
            className="input"
            value={filters.status}
            onChange={(event) => setFilters({ status: event.target.value as InventoryFilters['status'] })}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-filters__field">
          <span className="inv-filters__label">Color</span>
          <input
            type="text"
            className="input"
            placeholder="Any color"
            value={filters.color}
            onChange={(event) => setFilters({ color: event.target.value })}
          />
        </label>

        <label className="inv-filters__field">
          <span className="inv-filters__label">Date added from</span>
          <input
            type="date"
            className="input"
            value={filters.createdDateFrom}
            onChange={(event) => setFilters({ createdDateFrom: event.target.value })}
          />
        </label>

        <label className="inv-filters__field">
          <span className="inv-filters__label">Date added to</span>
          <input
            type="date"
            className="input"
            value={filters.createdDateTo}
            onChange={(event) => setFilters({ createdDateTo: event.target.value })}
          />
        </label>

        <label className="inv-filters__field inv-filters__field--checkbox">
          <input
            type="checkbox"
            checked={filters.includeArchived}
            onChange={(event) => setFilters({ includeArchived: event.target.checked })}
          />
          <span className="inv-filters__label">Include archived</span>
        </label>
      </div>

      <div className="inv-filters__footer">
        <button type="button" className="btn btn-ghost btn-sm" onClick={resetFilters}>
          Reset filters
        </button>
        <button type="button" className="btn btn-ghost btn-sm" disabled title="Coming soon">
          Save preset
        </button>
      </div>
    </section>
  );
}
