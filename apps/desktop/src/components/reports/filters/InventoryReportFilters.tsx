import type { ReportFilterContext } from './ReportFilterFields';
import { DatePresetFields, ReferenceFields } from './ReportFilterFields';

export function InventoryReportFilters(props: ReportFilterContext): JSX.Element {
  const { filters, setFilters } = props;
  return (
    <>
      <ReferenceFields {...props} />
      <label className="report-builder__field">
        <span>Serial number</span>
        <input
          className="input col-mono"
          value={filters.serialNumber}
          onChange={(e) => setFilters({ serialNumber: e.target.value })}
        />
      </label>
      <label className="report-builder__field">
        <span>Status</span>
        <select
          className="input"
          value={filters.inventoryStatus}
          onChange={(e) =>
            setFilters({ inventoryStatus: e.target.value as typeof filters.inventoryStatus })
          }
        >
          <option value="">All statuses</option>
          <option value="available">Available</option>
          <option value="sold">Sold</option>
          <option value="archived">Archived</option>
        </select>
      </label>
      <DatePresetFields {...props} showPresets dateLabel="Created date" />
      <label className="report-builder__field">
        <span>Color</span>
        <input
          className="input"
          value={filters.color}
          onChange={(e) => setFilters({ color: e.target.value })}
        />
      </label>
      <label className="report-builder__field report-builder__field--wide">
        <span>Search</span>
        <input
          className="input"
          value={filters.search}
          onChange={(e) => setFilters({ search: e.target.value })}
          placeholder="Serial, brand, model, location…"
        />
      </label>
    </>
  );
}
