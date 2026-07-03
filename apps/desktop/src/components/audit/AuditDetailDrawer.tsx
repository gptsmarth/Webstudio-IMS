import { X } from 'lucide-react';
import { StructuredDataPanel } from '../common/StructuredDataPanel';
import { formatDateTime } from '../../lib/datetime';
import type { AuditWorkspaceState } from '../../hooks/useAuditWorkspace';
import { auditResultBadgeClass, auditResultLabel, formatActorRole } from '../../lib/audit';

interface AuditDetailDrawerProps {
  workspace: Pick<
    AuditWorkspaceState,
    'selectedId' | 'selectedEntry' | 'selectEntry' | 'drawerLoading'
  >;
}

export function AuditDetailDrawer({ workspace }: AuditDetailDrawerProps): JSX.Element | null {
  const entry = workspace.selectedEntry;
  if (!workspace.selectedId) return null;

  return (
    <aside className="aud-drawer animate-slide-in" aria-label="Audit event details">
      <header className="aud-drawer__header">
        <div>
          <p className="aud-drawer__eyebrow">Audit event</p>
          <h2 className="aud-drawer__title">{entry?.operation ?? 'Loading…'}</h2>
          {entry && (
            <p className="aud-drawer__subtitle">
              {entry.module} · {formatDateTime(entry.created_at)}
            </p>
          )}
        </div>
        <button
          type="button"
          className="app-toolbar-icon-btn"
          onClick={() => workspace.selectEntry(null)}
          aria-label="Close drawer"
        >
          <X size={16} aria-hidden />
        </button>
      </header>

      {workspace.drawerLoading && <p className="aud-drawer__loading">Loading event details…</p>}

      {entry && !workspace.drawerLoading && (
        <div className="aud-drawer__body">
          <section className="aud-drawer__section aud-drawer__section--card">
            <h3 className="aud-drawer__section-title">Who & when</h3>
            <dl className="aud-drawer__dl">
              <div>
                <dt>User</dt>
                <dd>{entry.actor_display_name ?? 'System'}</dd>
              </div>
              <div>
                <dt>Role</dt>
                <dd>{formatActorRole(entry.actor_role)}</dd>
              </div>
              <div>
                <dt>Timestamp</dt>
                <dd>{formatDateTime(entry.created_at)}</dd>
              </div>
              <div>
                <dt>Result</dt>
                <dd>
                  <span className={auditResultBadgeClass(entry.result)}>
                    {auditResultLabel(entry.result)}
                  </span>
                </dd>
              </div>
            </dl>
          </section>

          <section className="aud-drawer__section">
            <h3 className="aud-drawer__section-title">What changed</h3>
            <p className="aud-drawer__section-hint">
              Plain-language summary of the values before and after this event.
            </p>
            <div className="aud-drawer__diff-grid">
              <StructuredDataPanel
                title="Before"
                value={entry.old_value}
                variant="before"
                emptyLabel="Nothing recorded before"
              />
              <StructuredDataPanel
                title="After"
                value={entry.new_value}
                variant="after"
                emptyLabel="Nothing recorded after"
              />
            </div>
          </section>

          <section className="aud-drawer__section aud-drawer__section--card">
            <h3 className="aud-drawer__section-title">Related records</h3>
            <dl className="aud-drawer__dl">
              <div>
                <dt>Inventory item</dt>
                <dd className="col-mono">
                  {entry.related_inventory_item_id ?? entry.serial_number ?? '—'}
                </dd>
              </div>
              <div>
                <dt>Sale</dt>
                <dd className="col-mono">{entry.related_sale_id ?? entry.invoice_number ?? '—'}</dd>
              </div>
              <div>
                <dt>Tally sync</dt>
                <dd>{entry.related_tally_sync ? 'Yes' : 'No'}</dd>
              </div>
              <div>
                <dt>Request ID</dt>
                <dd className="col-mono aud-drawer__mono">{entry.request_id ?? '—'}</dd>
              </div>
            </dl>
          </section>

          {entry.description && (
            <section className="aud-drawer__section aud-drawer__section--card">
              <h3 className="aud-drawer__section-title">Notes</h3>
              <p className="aud-drawer__notes">{entry.description}</p>
            </section>
          )}
        </div>
      )}
    </aside>
  );
}
