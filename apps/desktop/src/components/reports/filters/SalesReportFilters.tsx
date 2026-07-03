import type { ReportFilterContext } from './ReportFilterFields';
import { DatePresetFields, ReferenceFields } from './ReportFilterFields';

export function SalesReportFilters(props: ReportFilterContext): JSX.Element {
  const { filters, setFilters } = props;
  return (
    <>
      <DatePresetFields {...props} showPresets dateLabel="Sale date" />
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
        <span>Invoice number</span>
        <input
          className="input"
          value={filters.invoiceNumber}
          onChange={(e) => setFilters({ invoiceNumber: e.target.value })}
        />
      </label>
      <label className="report-builder__field">
        <span>Customer</span>
        <input
          className="input"
          value={filters.customerName}
          onChange={(e) => setFilters({ customerName: e.target.value })}
        />
      </label>
      <label className="report-builder__field">
        <span>Salesperson (user ID)</span>
        <input
          className="input"
          type="number"
          min={1}
          value={filters.userId ?? ''}
          onChange={(e) => setFilters({ userId: e.target.value ? Number(e.target.value) : null })}
        />
      </label>
      <label className="report-builder__field">
        <span>Payment mode</span>
        <input
          className="input"
          value={filters.paymentMode}
          onChange={(e) => setFilters({ paymentMode: e.target.value })}
        />
      </label>
      <label className="report-builder__field">
        <span>Sale source</span>
        <select
          className="input"
          value={filters.saleSource}
          onChange={(e) => setFilters({ saleSource: e.target.value as typeof filters.saleSource })}
        >
          <option value="">All sources</option>
          <option value="manual">Manual</option>
          <option value="tally">Tally</option>
        </select>
      </label>
      <label className="report-builder__field report-builder__field--wide">
        <span>Search</span>
        <input
          className="input"
          value={filters.search}
          onChange={(e) => setFilters({ search: e.target.value })}
          placeholder="Invoice, customer, serial…"
        />
      </label>
    </>
  );
}
