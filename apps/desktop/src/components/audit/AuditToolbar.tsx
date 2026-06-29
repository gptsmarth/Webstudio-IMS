import { Download, LayoutList, RefreshCw, Search, Workflow } from 'lucide-react';
import type { AuditWorkspaceState } from '../../hooks/useAuditWorkspace';
import type { AuditViewMode } from '../../lib/audit';

interface AuditToolbarProps {
  workspace: Pick<
    AuditWorkspaceState,
    | 'search'
    | 'setSearch'
    | 'refresh'
    | 'loading'
    | 'viewMode'
    | 'setViewMode'
    | 'exportAudit'
    | 'actionLoading'
  >;
  canExport: boolean;
}

export function AuditToolbar({ workspace, canExport }: AuditToolbarProps): JSX.Element {
  const setMode = (mode: AuditViewMode) => () => workspace.setViewMode(mode);

  return (
    <div className="aud-toolbar">
      <div className="aud-toolbar__search">
        <Search size={14} className="aud-toolbar__search-icon" aria-hidden />
        <input
          className="input aud-toolbar__search-input"
          type="search"
          placeholder="Search user, serial, invoice, model, entity…"
          value={workspace.search}
          onChange={(event) => workspace.setSearch(event.target.value)}
          aria-label="Search audit logs"
        />
      </div>

      <div className="aud-toolbar__view">
        <button
          type="button"
          className={`btn btn-ghost btn-sm ${workspace.viewMode === 'table' ? 'aud-toolbar__view--active' : ''}`}
          onClick={setMode('table')}
        >
          <LayoutList size={14} aria-hidden />
          Table
        </button>
        <button
          type="button"
          className={`btn btn-ghost btn-sm ${workspace.viewMode === 'timeline' ? 'aud-toolbar__view--active' : ''}`}
          onClick={setMode('timeline')}
        >
          <Workflow size={14} aria-hidden />
          Timeline
        </button>
      </div>

      <div className="aud-toolbar__actions">
        {canExport && (
          <>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => void workspace.exportAudit('xlsx')}
              disabled={workspace.actionLoading}
            >
              <Download size={14} aria-hidden />
              Excel
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => void workspace.exportAudit('pdf')}
              disabled={workspace.actionLoading}
            >
              <Download size={14} aria-hidden />
              PDF
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled
              title="CSV export coming soon"
            >
              <Download size={14} aria-hidden />
              CSV
            </button>
          </>
        )}
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => void workspace.refresh()}
          disabled={workspace.loading}
          aria-label="Refresh audit logs"
        >
          <RefreshCw size={14} className={workspace.loading ? 'aud-spin' : undefined} aria-hidden />
        </button>
      </div>
    </div>
  );
}
