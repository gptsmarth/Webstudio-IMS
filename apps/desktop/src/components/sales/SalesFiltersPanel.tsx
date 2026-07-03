import type { SalesFilters, SalesWorkspaceState } from '../../hooks/useSalesWorkspace';
import type { Brand } from '../../services/api/BrandService';
import type { Location } from '../../services/api/LocationService';

interface SalesFiltersPanelProps {
  filters: SalesFilters;
  setFilters: SalesWorkspaceState['setFilters'];
  resetFilters: SalesWorkspaceState['resetFilters'];
  brands: Brand[];
  locations: Location[];
  salespeople: SalesWorkspaceState['salespeople'];
}

export function SalesFiltersPanel({
  filters,
  setFilters,
  resetFilters,
  brands,
  locations,
  salespeople,
}: SalesFiltersPanelProps): JSX.Element {
  return (
    <section className="sales-filters" aria-label="Sales filters">
      <div className="sales-filters__grid">
        <label className="sales-filters__field">
          <span className="sales-filters__label">Date from</span>
          <input
            type="date"
            className="input"
            value={filters.dateFrom}
            onChange={(event) => setFilters({ dateFrom: event.target.value })}
          />
        </label>

        <label className="sales-filters__field">
          <span className="sales-filters__label">Date to</span>
          <input
            type="date"
            className="input"
            value={filters.dateTo}
            onChange={(event) => setFilters({ dateTo: event.target.value })}
          />
        </label>

        <label className="sales-filters__field">
          <span className="sales-filters__label">Brand</span>
          <select
            className="input"
            value={filters.brandId ?? ''}
            onChange={(event) =>
              setFilters({ brandId: event.target.value ? Number(event.target.value) : null })
            }
          >
            <option value="">All brands</option>
            {brands.map((brand) => (
              <option key={brand.id} value={brand.id}>
                {brand.name}
              </option>
            ))}
          </select>
        </label>

        <label className="sales-filters__field">
          <span className="sales-filters__label">Store</span>
          <select
            className="input"
            value={filters.locationId ?? ''}
            onChange={(event) =>
              setFilters({ locationId: event.target.value ? Number(event.target.value) : null })
            }
          >
            <option value="">All stores</option>
            {locations.map((location) => (
              <option key={location.id} value={location.id}>
                {location.name}
              </option>
            ))}
          </select>
        </label>

        <label className="sales-filters__field">
          <span className="sales-filters__label">Salesperson</span>
          <select
            className="input"
            value={filters.userId ?? ''}
            onChange={(event) =>
              setFilters({ userId: event.target.value ? Number(event.target.value) : null })
            }
          >
            <option value="">All salespeople</option>
            {salespeople.map((person) => (
              <option key={person.id} value={person.id}>
                {person.displayName}
              </option>
            ))}
          </select>
        </label>

        <label className="sales-filters__field">
          <span className="sales-filters__label">Invoice</span>
          <input
            className="input"
            placeholder="Invoice number"
            value={filters.invoiceNumber}
            onChange={(event) => setFilters({ invoiceNumber: event.target.value })}
          />
        </label>

        <label className="sales-filters__field">
          <span className="sales-filters__label">Customer</span>
          <input
            className="input"
            placeholder="Customer name"
            value={filters.customerName}
            onChange={(event) => setFilters({ customerName: event.target.value })}
          />
        </label>

        <label className="sales-filters__field">
          <span className="sales-filters__label">Payment mode</span>
          <input
            className="input"
            placeholder="Cash, UPI, card…"
            value={filters.paymentMode}
            onChange={(event) => setFilters({ paymentMode: event.target.value })}
          />
        </label>

        <label className="sales-filters__field">
          <span className="sales-filters__label">Sale source</span>
          <select
            className="input"
            value={filters.saleSource}
            onChange={(event) =>
              setFilters({ saleSource: event.target.value as SalesFilters['saleSource'] })
            }
          >
            <option value="">All sources</option>
            <option value="manual">Manual</option>
            <option value="tally">Tally</option>
          </select>
        </label>
      </div>

      <div className="sales-filters__footer">
        <button type="button" className="btn btn-ghost btn-sm" onClick={resetFilters}>
          Reset filters
        </button>
      </div>
    </section>
  );
}
