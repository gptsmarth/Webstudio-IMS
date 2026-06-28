import type { ReportBuilderFilters } from '../../../lib/reportBuilder';
import type { Brand } from '../../../services/api/BrandService';
import type { Location } from '../../../services/api/LocationService';
import type { ProductModel } from '../../../services/api/ProductModelService';
import type { DatePreset } from '../../../lib/reportDatePresets';

export interface ReportFilterContext {
  filters: ReportBuilderFilters;
  setFilters: (patch: Partial<ReportBuilderFilters>) => void;
  brands: Brand[];
  locations: Location[];
  productModels: ProductModel[];
}

export function DatePresetFields({
  filters,
  setFilters,
  showPresets,
  dateLabel = 'Date',
}: ReportFilterContext & {
  showPresets: boolean;
  dateLabel?: string;
}): JSX.Element {
  return (
    <>
      {showPresets && (
        <label className="report-builder__field">
          <span>{dateLabel}</span>
          <select
            className="input"
            value={filters.datePreset}
            onChange={(event) => setFilters({ datePreset: event.target.value as DatePreset })}
          >
            <option value="">All dates</option>
            <option value="today">Today</option>
            <option value="yesterday">Yesterday</option>
            <option value="week">This week</option>
            <option value="month">This month</option>
            <option value="quarter">This quarter</option>
            <option value="year">This year</option>
            <option value="custom">Custom range</option>
          </select>
        </label>
      )}
      {(filters.datePreset === 'custom' || !showPresets) && (
        <>
          <label className="report-builder__field">
            <span>{dateLabel} from</span>
            <input
              type="date"
              className="input"
              value={filters.dateFrom}
              onChange={(e) => setFilters({ dateFrom: e.target.value, datePreset: 'custom' })}
            />
          </label>
          <label className="report-builder__field">
            <span>{dateLabel} to</span>
            <input
              type="date"
              className="input"
              value={filters.dateTo}
              onChange={(e) => setFilters({ dateTo: e.target.value, datePreset: 'custom' })}
            />
          </label>
        </>
      )}
    </>
  );
}

export function ReferenceFields({
  filters,
  setFilters,
  brands,
  locations,
  productModels,
  includeStore = true,
}: ReportFilterContext & { includeStore?: boolean }): JSX.Element {
  return (
    <>
      {includeStore && (
        <label className="report-builder__field">
          <span>Store</span>
          <select
            className="input"
            value={filters.locationType}
            onChange={(e) => setFilters({ locationType: e.target.value as ReportBuilderFilters['locationType'] })}
          >
            <option value="">All stores</option>
            <option value="warehouse">Warehouse</option>
            <option value="retail_floor">Retail floor</option>
            <option value="other">Other</option>
          </select>
        </label>
      )}
      <label className="report-builder__field">
        <span>Location</span>
        <select
          className="input"
          value={filters.locationId ?? ''}
          onChange={(e) => setFilters({ locationId: e.target.value ? Number(e.target.value) : null })}
        >
          <option value="">All locations</option>
          {locations.map((location) => (
            <option key={location.id} value={location.id}>{location.name}</option>
          ))}
        </select>
      </label>
      <label className="report-builder__field">
        <span>Brand</span>
        <select
          className="input"
          value={filters.brandId ?? ''}
          onChange={(e) => setFilters({
            brandId: e.target.value ? Number(e.target.value) : null,
            productModelId: null,
          })}
        >
          <option value="">All brands</option>
          {brands.map((brand) => (
            <option key={brand.id} value={brand.id}>{brand.name}</option>
          ))}
        </select>
      </label>
      <label className="report-builder__field">
        <span>Product model</span>
        <select
          className="input"
          value={filters.productModelId ?? ''}
          onChange={(e) => setFilters({ productModelId: e.target.value || null })}
        >
          <option value="">All models</option>
          {productModels.map((model) => (
            <option key={model.id} value={model.id}>{model.model_number} — {model.model_name}</option>
          ))}
        </select>
      </label>
    </>
  );
}
