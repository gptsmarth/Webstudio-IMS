import type { BuilderReportType } from '../../services/api/ReportService';
import type { ReportBuilderFilters } from '../../lib/reportBuilder';
import { REPORT_TYPE_LABELS } from '../../lib/reportBuilder';
import type { Brand } from '../../services/api/BrandService';
import type { Location } from '../../services/api/LocationService';
import type { ProductModel } from '../../services/api/ProductModelService';
import { AuditReportFilters } from './filters/AuditReportFilters';
import { InventoryReportFilters } from './filters/InventoryReportFilters';
import { SalesReportFilters } from './filters/SalesReportFilters';
import { TallyReportFilters } from './filters/TallyReportFilters';

interface ReportFiltersFormProps {
  reportType: BuilderReportType;
  filters: ReportBuilderFilters;
  setFilters: (patch: Partial<ReportBuilderFilters>) => void;
  resetFilters: () => void;
  brands: Brand[];
  locations: Location[];
  productModels: ProductModel[];
}

export function ReportFiltersForm({
  reportType,
  filters,
  setFilters,
  resetFilters,
  brands,
  locations,
  productModels,
}: ReportFiltersFormProps): JSX.Element {
  const context = { filters, setFilters, brands, locations, productModels };

  return (
    <section className="report-builder__filters" aria-label="Report filters">
      <header className="report-builder__filters-header">
        <div>
          <h2 className="report-builder__filters-title">Configure filters</h2>
          <p className="report-builder__filters-subtitle">
            {REPORT_TYPE_LABELS[reportType]} report — all filters are combinable.
          </p>
        </div>
      </header>
      <div className="report-builder__filters-grid">
        {reportType === 'inventory' && <InventoryReportFilters {...context} />}
        {reportType === 'sales' && <SalesReportFilters {...context} />}
        {reportType === 'audit' && <AuditReportFilters {...context} />}
        {reportType === 'tally' && <TallyReportFilters {...context} />}
      </div>
      <div className="report-builder__filters-actions">
        <button type="button" className="btn btn-ghost btn-sm" onClick={resetFilters}>
          Reset filters
        </button>
      </div>
    </section>
  );
}
