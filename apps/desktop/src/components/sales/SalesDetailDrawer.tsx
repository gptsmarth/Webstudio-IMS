import { FileDown, FileText, Printer, X } from 'lucide-react';
import { formatDateTime } from '../../lib/datetime';
import { formatSaleSpecs, formatSaleAmount, saleSourceLabel } from '../../lib/sales';
import type { SalesWorkspaceState } from '../../hooks/useSalesWorkspace';
import type { AuditLogEntry } from '../../services/api/AuditService';
import { InventoryBrandCell } from '../inventory/InventoryBrandCell';
import { buildSalesTimelineEvents, SalesTimeline } from './SalesTimeline';

interface SalesDetailDrawerProps {
  workspace: Pick<
    SalesWorkspaceState,
    'selectedId' | 'selectedItem' | 'selectItem' | 'saleDetail' | 'auditLogs' | 'drawerLoading'
  >;
}

function AuditRow({ log }: { log: AuditLogEntry }): JSX.Element {
  return (
    <li className="sales-audit-row">
      <span className="sales-audit-row__action">{log.action.replaceAll('_', ' ')}</span>
      <span className="sales-audit-row__meta">
        {formatDateTime(log.created_at)}
        {log.actor_display_name ? ` · ${log.actor_display_name}` : ''}
      </span>
      {log.description && <span className="sales-audit-row__desc">{log.description}</span>}
    </li>
  );
}

export function SalesDetailDrawer({ workspace }: SalesDetailDrawerProps): JSX.Element | null {
  const item = workspace.selectedItem;
  const detail = workspace.saleDetail;

  if (!workspace.selectedId || !item) return null;

  const timelineEvents = buildSalesTimelineEvents(
    workspace.auditLogs,
    detail?.location_name ?? item.location_name,
  );
  const tallyLogs = workspace.auditLogs.filter((log) => log.source === 'TALLY_SYNC');

  return (
    <aside className="sales-drawer animate-slide-in" aria-label="Sale details">
      <header className="sales-drawer__header">
        <div>
          <p className="sales-drawer__eyebrow">Sale record</p>
          <h2 className="sales-drawer__title">{item.invoice_number}</h2>
        </div>
        <button
          type="button"
          className="app-toolbar-icon-btn"
          onClick={() => workspace.selectItem(null)}
          aria-label="Close drawer"
        >
          <X size={16} aria-hidden />
        </button>
      </header>

      <div className="sales-drawer__actions">
        <button type="button" className="btn btn-ghost btn-sm" disabled title="Coming soon">
          <Printer size={14} aria-hidden />
          Print invoice
        </button>
        <button type="button" className="btn btn-ghost btn-sm" disabled title="Coming soon">
          <FileDown size={14} aria-hidden />
          Re-export
        </button>
        <button type="button" className="btn btn-ghost btn-sm" disabled title="Coming soon">
          <FileText size={14} aria-hidden />
          Preview PDF
        </button>
      </div>

      <div className="sales-drawer__body">
        {workspace.drawerLoading ? (
          <div className="sales-drawer__loading">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="skeleton sales-drawer__skeleton" />
            ))}
          </div>
        ) : (
          <>
            <section className="sales-drawer__section">
              <h3 className="sales-drawer__section-title">Invoice details</h3>
              <dl className="sales-detail-grid">
                <div>
                  <dt>Invoice number</dt>
                  <dd>{detail?.invoice_number ?? item.invoice_number}</dd>
                </div>
                <div>
                  <dt>Invoice date</dt>
                  <dd>{formatDateTime(detail?.sold_at ?? item.sold_at)}</dd>
                </div>
                <div>
                  <dt>Payment mode</dt>
                  <dd>{detail?.payment_mode ?? item.payment_mode ?? '—'}</dd>
                </div>
                <div>
                  <dt>Sale amount</dt>
                  <dd>{formatSaleAmount(detail?.sale_amount ?? item.sale_amount)}</dd>
                </div>
                <div>
                  <dt>Sale source</dt>
                  <dd>{saleSourceLabel(detail?.sale_source ?? item.sale_source)}</dd>
                </div>
                <div>
                  <dt>Sold by</dt>
                  <dd>
                    {detail?.recorded_by_display_name ?? item.recorded_by_display_name ?? '—'}
                  </dd>
                </div>
                <div>
                  <dt>Recorded at</dt>
                  <dd>{detail?.created_at ? formatDateTime(detail.created_at) : '—'}</dd>
                </div>
              </dl>
            </section>

            <section className="sales-drawer__section">
              <h3 className="sales-drawer__section-title">Customer</h3>
              <p className="sales-drawer__text">
                {detail?.customer_name ?? item.customer_name ?? '—'}
              </p>
              {detail?.notes && <p className="sales-drawer__muted">Notes: {detail.notes}</p>}
            </section>

            <section className="sales-drawer__section">
              <h3 className="sales-drawer__section-title">Laptop information</h3>
              <dl className="sales-detail-grid">
                <div>
                  <dt>Brand</dt>
                  <dd>
                    <InventoryBrandCell brandName={detail?.brand_name ?? item.brand_name} />
                  </dd>
                </div>
                <div>
                  <dt>Model</dt>
                  <dd>
                    {detail?.model_number ?? item.model_number} —{' '}
                    {detail?.model_name ?? item.model_name}
                  </dd>
                </div>
                <div>
                  <dt>Serial</dt>
                  <dd className="col-mono">{detail?.serial_number ?? item.serial_number}</dd>
                </div>
                <div>
                  <dt>Store</dt>
                  <dd>{detail?.location_name ?? item.location_name}</dd>
                </div>
                {detail && (
                  <>
                    <div>
                      <dt>Color</dt>
                      <dd>{detail.color}</dd>
                    </div>
                    <div>
                      <dt>Specifications</dt>
                      <dd>{formatSaleSpecs(detail)}</dd>
                    </div>
                  </>
                )}
              </dl>
            </section>

            <section className="sales-drawer__section">
              <h3 className="sales-drawer__section-title">Timeline</h3>
              <SalesTimeline events={timelineEvents} />
            </section>

            <section className="sales-drawer__section">
              <h3 className="sales-drawer__section-title">Tally information</h3>
              {detail?.tally_company_name || detail?.tally_voucher_number ? (
                <dl className="sales-detail-grid">
                  <div>
                    <dt>Company</dt>
                    <dd>{detail.tally_company_name ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Printed invoice</dt>
                    <dd className="col-mono">
                      {detail.printed_invoice_number ?? detail.invoice_number}
                    </dd>
                  </div>
                  <div>
                    <dt>Internal voucher</dt>
                    <dd className="col-mono">{detail.tally_voucher_number ?? '—'}</dd>
                  </div>
                  {detail.tally_voucher_type && (
                    <div>
                      <dt>Voucher type</dt>
                      <dd>{detail.tally_voucher_type}</dd>
                    </div>
                  )}
                </dl>
              ) : tallyLogs.length > 0 ? (
                <ul className="sales-audit-list">
                  {tallyLogs.map((log) => (
                    <AuditRow key={log.id} log={log} />
                  ))}
                </ul>
              ) : (
                <p className="sales-drawer__muted">No Tally sync information recorded.</p>
              )}
            </section>

            <section className="sales-drawer__section">
              <h3 className="sales-drawer__section-title">Audit information</h3>
              {workspace.auditLogs.length === 0 ? (
                <p className="sales-drawer__muted">No audit entries for this sale.</p>
              ) : (
                <ul className="sales-audit-list">
                  {workspace.auditLogs.slice(0, 12).map((log) => (
                    <AuditRow key={log.id} log={log} />
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </div>
    </aside>
  );
}
