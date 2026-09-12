import { useState } from 'react';
import { Ban, FileDown, FileText, Printer, X } from 'lucide-react';
import { formatDateTime } from '../../lib/datetime';
import {
  formatSaleSpecs,
  formatSaleAmount,
  saleSourceLabel,
  tallyInvoiceStatusLabel,
  canCancelSales,
} from '../../lib/sales';
import { canViewPurchasePrice } from '../../lib/inventory';
import { useAuthStore } from '../../store';
import type { SalesWorkspaceState } from '../../hooks/useSalesWorkspace';
import type { AuditLogEntry } from '../../services/api/AuditService';
import type {
  AdditionalInvoiceProduct,
  InvoiceTotals,
  TrackedInvoiceProduct,
  UnmatchedSerializedItem,
} from '../../services/api/SalesService';
import { InventoryBrandCell } from '../inventory/InventoryBrandCell';
import { buildSalesTimelineEvents, SalesTimeline } from './SalesTimeline';
import { SaleCancelDialog } from './SaleCancelDialog';

interface SalesDetailDrawerProps {
  workspace: Pick<
    SalesWorkspaceState,
    | 'selectedId'
    | 'selectedItem'
    | 'selectItem'
    | 'saleDetail'
    | 'auditLogs'
    | 'drawerLoading'
    | 'cancelSale'
    | 'actionLoading'
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

function LineAmount({ value }: { value: string | number | null | undefined }): JSX.Element {
  return <>{formatSaleAmount(value)}</>;
}

function TrackedProductsList({
  products,
  isMainAdmin,
}: {
  products: TrackedInvoiceProduct[];
  isMainAdmin: boolean;
}): JSX.Element {
  return (
    <ul className="sales-line-list">
      {products.map((line) => (
        <li key={`tracked-${line.line_index}`} className="sales-line-list__item">
          <div className="sales-line-list__title">
            {line.product_name ?? 'Tracked product'}
            {line.review_required ? (
              <span className="badge badge-warning sales-line-list__badge">Review</span>
            ) : null}
          </div>
          <dl className="sales-detail-grid sales-detail-grid--compact">
            <div>
              <dt>Serial</dt>
              <dd className="col-mono">{line.serial_number ?? '—'}</dd>
            </div>
            <div>
              <dt>Amount</dt>
              <dd>
                <LineAmount value={line.line_total ?? line.rate} />
              </dd>
            </div>
            {isMainAdmin && line.serial_source_label ? (
              <div>
                <dt>Serial source</dt>
                <dd className="col-mono">{line.serial_source_label}</dd>
              </div>
            ) : null}
          </dl>
        </li>
      ))}
    </ul>
  );
}

function AdditionalProductsList({
  products,
}: {
  products: AdditionalInvoiceProduct[];
}): JSX.Element {
  return (
    <ul className="sales-line-list">
      {products.map((line) => (
        <li key={`additional-${line.line_index}`} className="sales-line-list__item">
          <div className="sales-line-list__title">
            {line.stock_item_name ?? 'Additional product'}
          </div>
          <dl className="sales-detail-grid sales-detail-grid--compact">
            <div>
              <dt>Qty</dt>
              <dd>{line.quantity ?? '—'}</dd>
            </div>
            <div>
              <dt>Amount</dt>
              <dd>
                <LineAmount value={line.line_total ?? line.taxable_amount ?? line.rate} />
              </dd>
            </div>
            {line.decision_reason ? (
              <div>
                <dt>Note</dt>
                <dd>{line.decision_reason}</dd>
              </div>
            ) : null}
          </dl>
        </li>
      ))}
    </ul>
  );
}

function UnmatchedItemsList({
  items,
  isMainAdmin,
}: {
  items: UnmatchedSerializedItem[];
  isMainAdmin: boolean;
}): JSX.Element {
  return (
    <ul className="sales-line-list">
      {items.map((line) => (
        <li key={`unmatched-${line.line_index}`} className="sales-line-list__item">
          <div className="sales-line-list__title">{line.product_name ?? 'Unmatched item'}</div>
          <dl className="sales-detail-grid sales-detail-grid--compact">
            <div>
              <dt>Serial</dt>
              <dd className="col-mono">{line.serial_number ?? '—'}</dd>
            </div>
            <div>
              <dt>Amount</dt>
              <dd>
                <LineAmount value={line.invoice_amount} />
              </dd>
            </div>
            <div>
              <dt>Reason</dt>
              <dd>{line.reason}</dd>
            </div>
            {isMainAdmin && line.serial_source_label ? (
              <div>
                <dt>Serial source</dt>
                <dd className="col-mono">{line.serial_source_label}</dd>
              </div>
            ) : null}
          </dl>
        </li>
      ))}
    </ul>
  );
}

function InvoiceTotalsBlock({ totals }: { totals: InvoiceTotals }): JSX.Element {
  const rows: Array<{ label: string; value: string | number | null }> = [
    { label: 'Subtotal', value: totals.subtotal },
    { label: 'Discount', value: totals.discount_amount },
    { label: 'CGST', value: totals.cgst_amount },
    { label: 'SGST', value: totals.sgst_amount },
    { label: 'IGST', value: totals.igst_amount },
    { label: 'Cess', value: totals.cess_amount },
    { label: 'Round off', value: totals.round_off },
    { label: 'Grand total', value: totals.grand_total },
  ].filter((row) => row.value != null && row.value !== '');

  if (rows.length === 0) {
    return <p className="sales-drawer__muted">No invoice totals recorded.</p>;
  }

  return (
    <dl className="sales-detail-grid">
      {rows.map((row) => (
        <div key={row.label}>
          <dt>{row.label}</dt>
          <dd>
            <LineAmount value={row.value} />
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function SalesDetailDrawer({ workspace }: SalesDetailDrawerProps): JSX.Element | null {
  const session = useAuthStore((state) => state.session);
  const isMainAdmin = session?.role === 'main_admin';
  const showPurchasePrice = session ? canViewPurchasePrice(session.permissions) : false;
  const canCancel = session ? canCancelSales(session.permissions) : false;
  const [confirmingCancel, setConfirmingCancel] = useState(false);
  const item = workspace.selectedItem;
  const detail = workspace.saleDetail;

  if (!workspace.selectedId || !item) return null;

  const timelineEvents = buildSalesTimelineEvents(
    workspace.auditLogs,
    detail?.location_name ?? item.location_name,
  );
  const tallyLogs = workspace.auditLogs.filter((log) => log.source === 'TALLY_SYNC');
  const saleAmountExcludingGst =
    detail?.sale_amount_excluding_gst ?? item.sale_amount_excluding_gst ?? null;
  const saleAmountInclusive = detail?.sale_amount ?? item.sale_amount ?? null;
  const saleCgstAmount = detail?.sale_cgst_amount ?? item.sale_cgst_amount ?? null;
  const saleSgstAmount = detail?.sale_sgst_amount ?? item.sale_sgst_amount ?? null;
  const saleIgstAmount = detail?.sale_igst_amount ?? item.sale_igst_amount ?? null;
  const saleCessAmount = detail?.sale_cess_amount ?? item.sale_cess_amount ?? null;
  const trackedProducts = detail?.tracked_products ?? [];
  const additionalProducts = detail?.additional_products ?? [];
  const unmatchedItems = detail?.unmatched_serialized_items ?? [];
  const hasInvoiceComposition =
    trackedProducts.length > 0 || additionalProducts.length > 0 || unmatchedItems.length > 0;
  const hasTallyMeta = Boolean(
    detail?.tally_company_name ||
    detail?.tally_voucher_number ||
    detail?.printed_invoice_number ||
    detail?.tally_voucher_guid ||
    detail?.invoice_status,
  );

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
        {canCancel && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            style={{ color: 'var(--color-danger, #c0392b)' }}
            onClick={() => setConfirmingCancel(true)}
          >
            <Ban size={14} aria-hidden />
            Delete invoice
          </button>
        )}
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
            {detail?.review_required ? (
              <section className="sales-drawer__section sales-drawer__section--alert" role="status">
                <h3 className="sales-drawer__section-title">Review required</h3>
                <p className="sales-drawer__text">
                  {detail.review_reason ?? 'This Tally invoice needs operator review.'}
                </p>
                {(detail.invoice_model_name || detail.ims_model_name) && (
                  <dl className="sales-detail-grid sales-detail-grid--compact">
                    {detail.invoice_model_name ? (
                      <div>
                        <dt>Invoice model</dt>
                        <dd>{detail.invoice_model_name}</dd>
                      </div>
                    ) : null}
                    {detail.ims_model_name ? (
                      <div>
                        <dt>IMS model</dt>
                        <dd>{detail.ims_model_name}</dd>
                      </div>
                    ) : null}
                  </dl>
                )}
              </section>
            ) : null}

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
                {detail?.invoice_status ? (
                  <div>
                    <dt>Invoice status</dt>
                    <dd>{tallyInvoiceStatusLabel(detail.invoice_status)}</dd>
                  </div>
                ) : null}
                <div>
                  <dt>Payment mode</dt>
                  <dd>{detail?.payment_mode ?? item.payment_mode ?? '—'}</dd>
                </div>
                <div>
                  <dt>Sale amount (incl. GST)</dt>
                  <dd>{formatSaleAmount(saleAmountInclusive)}</dd>
                </div>
                {saleAmountExcludingGst != null && (
                  <div>
                    <dt>Amount excluding GST</dt>
                    <dd>{formatSaleAmount(saleAmountExcludingGst)}</dd>
                  </div>
                )}
                {saleCgstAmount != null && (
                  <div>
                    <dt>CGST</dt>
                    <dd>{formatSaleAmount(saleCgstAmount)}</dd>
                  </div>
                )}
                {saleSgstAmount != null && (
                  <div>
                    <dt>SGST</dt>
                    <dd>{formatSaleAmount(saleSgstAmount)}</dd>
                  </div>
                )}
                {saleIgstAmount != null && (
                  <div>
                    <dt>IGST</dt>
                    <dd>{formatSaleAmount(saleIgstAmount)}</dd>
                  </div>
                )}
                {saleCessAmount != null && (
                  <div>
                    <dt>Cess</dt>
                    <dd>{formatSaleAmount(saleCessAmount)}</dd>
                  </div>
                )}
                {showPurchasePrice && (
                  <div>
                    <dt>Purchase price</dt>
                    <dd>{formatSaleAmount(detail?.purchase_price ?? item.purchase_price)}</dd>
                  </div>
                )}
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
                {detail?.imported_at ? (
                  <div>
                    <dt>Imported at</dt>
                    <dd>{formatDateTime(detail.imported_at)}</dd>
                  </div>
                ) : null}
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
                    {isMainAdmin && detail.serial_source_label ? (
                      <div>
                        <dt>Serial source</dt>
                        <dd className="col-mono">{detail.serial_source_label}</dd>
                      </div>
                    ) : null}
                  </>
                )}
              </dl>
            </section>

            {hasInvoiceComposition ? (
              <>
                {trackedProducts.length > 0 ? (
                  <section className="sales-drawer__section">
                    <h3 className="sales-drawer__section-title">Tracked products</h3>
                    <TrackedProductsList products={trackedProducts} isMainAdmin={isMainAdmin} />
                  </section>
                ) : null}
                {additionalProducts.length > 0 ? (
                  <section className="sales-drawer__section">
                    <h3 className="sales-drawer__section-title">Additional products</h3>
                    <AdditionalProductsList products={additionalProducts} />
                  </section>
                ) : null}
                {unmatchedItems.length > 0 ? (
                  <section className="sales-drawer__section">
                    <h3 className="sales-drawer__section-title">Unmatched serialized items</h3>
                    <UnmatchedItemsList items={unmatchedItems} isMainAdmin={isMainAdmin} />
                  </section>
                ) : null}
              </>
            ) : null}

            {detail?.invoice_totals ? (
              <section className="sales-drawer__section">
                <h3 className="sales-drawer__section-title">Invoice totals</h3>
                <InvoiceTotalsBlock totals={detail.invoice_totals} />
              </section>
            ) : null}

            <section className="sales-drawer__section">
              <h3 className="sales-drawer__section-title">Timeline</h3>
              <SalesTimeline events={timelineEvents} />
            </section>

            <section className="sales-drawer__section">
              <h3 className="sales-drawer__section-title">Tally information</h3>
              {hasTallyMeta && detail ? (
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
                  {detail.invoice_status ? (
                    <div>
                      <dt>Invoice status</dt>
                      <dd>{tallyInvoiceStatusLabel(detail.invoice_status)}</dd>
                    </div>
                  ) : null}
                  {isMainAdmin && detail.tally_voucher_guid ? (
                    <div>
                      <dt>Voucher GUID</dt>
                      <dd className="col-mono">{detail.tally_voucher_guid}</dd>
                    </div>
                  ) : null}
                  {isMainAdmin && detail.tally_master_id ? (
                    <div>
                      <dt>Master ID</dt>
                      <dd className="col-mono">{detail.tally_master_id}</dd>
                    </div>
                  ) : null}
                  {detail.original_xml_available ? (
                    <div>
                      <dt>Original XML</dt>
                      <dd>Archived</dd>
                    </div>
                  ) : null}
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

      <SaleCancelDialog
        open={confirmingCancel}
        sale={confirmingCancel ? item : null}
        loading={workspace.actionLoading}
        onClose={() => setConfirmingCancel(false)}
        onConfirm={async (reason) => {
          await workspace.cancelSale(item.id, reason);
          workspace.selectItem(null);
        }}
      />
    </aside>
  );
}
