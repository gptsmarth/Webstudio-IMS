import type { ReportFilterContext } from './ReportFilterFields';
import { DatePresetFields, ReferenceFields } from './ReportFilterFields';

export function AuditReportFilters(props: ReportFilterContext): JSX.Element {
  const { filters, setFilters } = props;
  return (
    <>
      <label className="report-builder__field">
        <span>User (ID)</span>
        <input
          className="input"
          type="number"
          min={1}
          value={filters.userId ?? ''}
          onChange={(e) => setFilters({ userId: e.target.value ? Number(e.target.value) : null })}
        />
      </label>
      <label className="report-builder__field">
        <span>Role</span>
        <select className="input" value={filters.actorRole} onChange={(e) => setFilters({ actorRole: e.target.value })}>
          <option value="">All roles</option>
          <option value="main_admin">Main admin</option>
          <option value="admin">Admin</option>
          <option value="salesperson">Salesperson</option>
        </select>
      </label>
      <label className="report-builder__field">
        <span>Operation</span>
        <select className="input" value={filters.auditAction} onChange={(e) => setFilters({ auditAction: e.target.value })}>
          <option value="">All operations</option>
          <option value="CREATE">Create</option>
          <option value="UPDATE">Update</option>
          <option value="ARCHIVE">Archive</option>
          <option value="RESTORE">Restore</option>
          <option value="STATUS_CHANGE">Status change</option>
          <option value="LOCATION_CHANGE">Location change</option>
          <option value="SYSTEM_ACTION">System action</option>
        </select>
      </label>
      <DatePresetFields {...props} showPresets={false} dateLabel="Date" />
      <label className="report-builder__field">
        <span>Serial number</span>
        <input className="input col-mono" value={filters.serialNumber} onChange={(e) => setFilters({ serialNumber: e.target.value })} />
      </label>
      <ReferenceFields {...props} includeStore={false} />
      <label className="report-builder__field">
        <span>Action source</span>
        <select className="input" value={filters.auditSource} onChange={(e) => setFilters({ auditSource: e.target.value })}>
          <option value="">All sources</option>
          <option value="MANUAL">Manual</option>
          <option value="TALLY_SYNC">Tally sync</option>
          <option value="BACKGROUND_JOB">Background job</option>
          <option value="SYSTEM">System</option>
        </select>
      </label>
      <label className="report-builder__field report-builder__field--wide">
        <span>Search</span>
        <input
          className="input"
          value={filters.search}
          onChange={(e) => setFilters({ search: e.target.value })}
          placeholder="Description, actor, serial…"
        />
      </label>
    </>
  );
}
