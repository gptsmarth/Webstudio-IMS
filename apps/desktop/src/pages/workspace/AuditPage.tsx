import { useMemo } from 'react';
import { AlertCircle } from 'lucide-react';
import { CataloguePagination } from '../../components/catalogue/CataloguePagination';
import {
  AuditDetailDrawer,
  AuditFiltersPanel,
  AuditTable,
  AuditTimeline,
  AuditToolbar,
} from '../../components/audit';
import { useAuditWorkspace } from '../../hooks/useAuditWorkspace';
import { canReadAudit } from '../../lib/audit';
import { hasActiveAuditFilters } from '../../lib/auditExport';
import { useAuthStore } from '../../store';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';

export function AuditPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const workspace = useAuditWorkspace();

  const permissionDenied = useMemo(() => {
    if (!session) return 'Sign in again to access the audit center.';
    if (!canReadAudit(session.permissions)) {
      return 'Your account does not have permission to view audit logs.';
    }
    return null;
  }, [session]);

  const canExport = hasActiveAuditFilters(workspace.filters, workspace.search);

  if (permissionDenied) {
    return (
      <div className="aud-page">
        <div className="aud-empty">
          <p className="aud-empty__title">Access restricted</p>
          <p className="aud-empty__text">{permissionDenied}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="aud-page animate-fade-in">
      <header className="aud-page__header">
        <WorkspacePageBack />
        <div>
          <h1 className="aud-page__title">Audit Center</h1>
          <p className="aud-page__subtitle">Immutable history of business operations, system events, and integrations.</p>
        </div>
      </header>

      <div className="aud-page__panel">
        <AuditToolbar workspace={workspace} canExport={canExport} />

        {!canExport && (
          <p className="aud-page__hint">Apply search or filters to enable filtered Excel/PDF exports.</p>
        )}

        <AuditFiltersPanel
          filters={workspace.filters}
          setFilters={workspace.setFilters}
          resetFilters={workspace.resetFilters}
          users={workspace.users}
          locations={workspace.locations}
        />

        {workspace.error && (
          <div className="alert alert-danger aud-page__alert">
            <AlertCircle size={14} aria-hidden />
            <span>{workspace.error}</span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => void workspace.refresh()}>
              Retry
            </button>
          </div>
        )}

        {workspace.actionError && (
          <div className="alert alert-danger aud-page__alert">
            <AlertCircle size={14} aria-hidden />
            <span>{workspace.actionError}</span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={workspace.clearActionError}>
              Dismiss
            </button>
          </div>
        )}

        <div className={`aud-page__body ${workspace.selectedId ? 'aud-page__body--drawer-open' : ''}`}>
          {workspace.viewMode === 'table' ? (
            <AuditTable workspace={workspace} onView={(entry) => workspace.selectEntry(entry.id)} />
          ) : (
            <AuditTimeline workspace={workspace} />
          )}
          <AuditDetailDrawer workspace={workspace} />
        </div>

        <CataloguePagination
          page={workspace.page}
          pageSize={workspace.pageSize}
          totalItems={workspace.totalItems}
          onPageChange={workspace.setPage}
          loading={workspace.loading}
        />
      </div>
    </div>
  );
}
