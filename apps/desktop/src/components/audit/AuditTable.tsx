import { formatDateTime } from '../../lib/datetime';
import type { AuditWorkspaceState } from '../../hooks/useAuditWorkspace';
import { auditResultBadgeClass, auditResultLabel, auditSeverityBadgeClass, auditSeverityLabel, formatActorRole, formatAuditEntity } from '../../lib/audit';
import type { AuditListEntry } from '../../services/api/AuditService';

interface AuditTableProps {
  workspace: AuditWorkspaceState;
  onView: (entry: AuditListEntry) => void;
}

export function AuditTable({ workspace, onView }: AuditTableProps): JSX.Element {
  return (
    <div className="aud-table-shell">
      <div className="aud-table-scroll">
        <table className="table aud-table">
          <thead className="aud-table__head">
            <tr>
              <th>Timestamp</th>
              <th>User</th>
              <th>Role</th>
              <th>Operation</th>
              <th>Module</th>
              <th>Entity</th>
              <th>Serial</th>
              <th>Location</th>
              <th>Severity</th>
              <th>Result</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {workspace.loading &&
              Array.from({ length: 8 }).map((_, index) => (
                <tr key={`sk-${index}`}>
                  <td colSpan={11}>
                    <div className="aud-table__skeleton animate-pulse" />
                  </td>
                </tr>
              ))}
            {!workspace.loading && workspace.items.length === 0 && (
              <tr>
                <td colSpan={11} className="aud-table__empty">
                  No audit events match the current filters.
                </td>
              </tr>
            )}
            {!workspace.loading &&
              workspace.items.map((entry) => (
                <tr
                  key={entry.id}
                  className={[
                    'aud-table__row',
                    workspace.selectedId === entry.id ? 'aud-table__row--selected' : '',
                  ].filter(Boolean).join(' ') || undefined}
                  onClick={() => onView(entry)}
                >
                  <td className="aud-table__cell aud-table__cell--time">{formatDateTime(entry.created_at)}</td>
                  <td className="aud-table__cell aud-table__cell--user">{entry.actor_display_name ?? 'System'}</td>
                  <td className="aud-table__cell">{entry.actor_role ? formatActorRole(entry.actor_role) : '—'}</td>
                  <td className="aud-table__cell aud-table__cell--operation">{entry.operation}</td>
                  <td className="aud-table__cell">{entry.module}</td>
                  <td className="aud-table__cell col-mono aud-table__cell--entity">{formatAuditEntity(entry)}</td>
                  <td className="aud-table__cell col-mono">{entry.serial_number ?? '—'}</td>
                  <td className="aud-table__cell">{entry.location_name ?? '—'}</td>
                  <td className="aud-table__cell">
                    <span className={auditSeverityBadgeClass(entry.severity)}>{auditSeverityLabel(entry.severity)}</span>
                  </td>
                  <td className="aud-table__cell">
                    <span className={auditResultBadgeClass(entry.result)}>{auditResultLabel(entry.result)}</span>
                  </td>
                  <td className="aud-table__desc aud-table__cell">{entry.description ?? '—'}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
