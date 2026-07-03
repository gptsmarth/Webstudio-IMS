import type { ReportFilterContext } from './ReportFilterFields';
import { DatePresetFields } from './ReportFilterFields';

export function TallyReportFilters(props: ReportFilterContext): JSX.Element {
  const { filters, setFilters } = props;
  return (
    <>
      <label className="report-builder__field">
        <span>Company</span>
        <input
          className="input"
          value={filters.company}
          onChange={(e) => setFilters({ company: e.target.value })}
          placeholder="Filter by company name"
        />
      </label>
      <DatePresetFields {...props} showPresets dateLabel="Date" />
      <label className="report-builder__field">
        <span>Sync status</span>
        <select
          className="input"
          value={filters.syncStatus}
          onChange={(e) => setFilters({ syncStatus: e.target.value as typeof filters.syncStatus })}
        >
          <option value="">All statuses</option>
          <option value="unread">Unread</option>
          <option value="read">Read</option>
          <option value="resolved">Resolved</option>
        </select>
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
        <span>Outcome</span>
        <select
          className="input"
          value={filters.tallyOutcome}
          onChange={(e) =>
            setFilters({
              tallyOutcome: e.target.value as typeof filters.tallyOutcome,
              notificationType: '',
            })
          }
        >
          <option value="">All outcomes</option>
          <option value="processed">Processed</option>
          <option value="skipped">Skipped</option>
          <option value="duplicate">Duplicate</option>
          <option value="missing_serial">Missing serial</option>
          <option value="missing_model">Missing model</option>
          <option value="model_mismatch">Model mismatch</option>
        </select>
      </label>
      <label className="report-builder__field">
        <span>Notification type</span>
        <select
          className="input"
          value={filters.notificationType}
          onChange={(e) => setFilters({ notificationType: e.target.value, tallyOutcome: '' })}
          disabled={Boolean(filters.tallyOutcome)}
        >
          <option value="">All types</option>
          <option value="tally_sync_completed">Tally sync completed</option>
          <option value="sync_failure">Sync failure</option>
          <option value="duplicate_sale">Duplicate sale</option>
          <option value="serial_number_missing">Serial number missing</option>
          <option value="product_model_missing">Product model missing</option>
          <option value="product_model_mismatch">Product model mismatch</option>
        </select>
      </label>
      <label className="report-builder__field report-builder__field--wide">
        <span>Search</span>
        <input
          className="input"
          value={filters.search}
          onChange={(e) => setFilters({ search: e.target.value })}
          placeholder="Title, description, invoice…"
        />
      </label>
    </>
  );
}
