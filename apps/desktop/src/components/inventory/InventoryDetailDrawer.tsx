import { useEffect, useMemo, useState } from 'react';
import {
  Archive,
  ArchiveRestore,
  MapPin,
  Pencil,
  QrCode,
  ShoppingBag,
  Tag,
  X,
} from 'lucide-react';
import { canMarkSold, canViewPurchasePrice, canWriteInventory, formatInventorySpecs } from '../../lib/inventory';
import { formatInventoryPrice } from '../../lib/inventoryPrice';
import { buildInventoryLifecycle } from '../../lib/inventoryLifecycle';
import {
  colorVariantsLabel,
  modelDisplayName,
  saleStatusBadgeClass,
  saleStatusLabel,
} from '../../lib/inventoryDomain';
import { formatDateTime } from '../../lib/datetime';
import { formatSaleAmount } from '../../lib/sales';
import type { InventoryWorkspaceState } from '../../hooks/useInventoryWorkspace';
import type { AuditLogEntry } from '../../services/api/AuditService';
import { InventoryBrandCell } from './InventoryBrandCell';
import { InventoryLifecycleStepper } from './InventoryLifecycleStepper';
import { InventoryMovementHistory } from './InventoryMovementHistory';
import { InventoryQrDialog } from './InventoryQrDialog';
import { InventorySiblingUnits } from './InventorySiblingUnits';
import { InventoryStatusBadge } from './InventoryStatusBadge';
import { ProductImagePanel } from './ProductImagePanel';
import { ProductModelSummaryPanel } from './ProductModelSummaryPanel';

interface InventoryDetailDrawerProps {
  workspace: Pick<
    InventoryWorkspaceState,
    | 'selectedItem'
    | 'selectedId'
    | 'selectItem'
    | 'auditLogs'
    | 'saleDetail'
    | 'productModel'
    | 'siblingUnits'
    | 'drawerLoading'
    | 'actionLoading'
    | 'actionError'
    | 'clearActionError'
    | 'updateItem'
  >;
  permissions: string[];
  editRequestId?: string | null;
  onEditRequestHandled?: () => void;
  onTransfer: () => void;
  onMarkSold: () => void;
  onArchive: () => void;
  onRestore: () => void;
}

function AuditRow({ log }: { log: AuditLogEntry }): JSX.Element {
  return (
    <li id={`audit-${log.id}`} className="inv-audit-row">
      <span className="inv-audit-row__action">{log.action.replaceAll('_', ' ')}</span>
      <span className="inv-audit-row__meta">
        {formatDateTime(log.created_at)}
        {log.actor_display_name ? ` · ${log.actor_display_name}` : ''}
      </span>
      {log.description && <span className="inv-audit-row__desc">{log.description}</span>}
    </li>
  );
}

export function InventoryDetailDrawer({
  workspace,
  permissions,
  editRequestId,
  onEditRequestHandled,
  onTransfer,
  onMarkSold,
  onArchive,
  onRestore,
}: InventoryDetailDrawerProps): JSX.Element | null {
  const item = workspace.selectedItem;
  const [editing, setEditing] = useState(false);
  const [serial, setSerial] = useState('');
  const [color, setColor] = useState('');
  const [qrOpen, setQrOpen] = useState(false);

  useEffect(() => {
    if (!editRequestId || !item || item.id !== editRequestId) return;
    setSerial(item.serial_number);
    setColor(item.color);
    setEditing(true);
    onEditRequestHandled?.();
  }, [editRequestId, item, onEditRequestHandled]);

  const lifecycleSteps = useMemo(
    () => (item ? buildInventoryLifecycle(item, workspace.auditLogs) : []),
    [item, workspace.auditLogs],
  );

  if (!workspace.selectedId || !item) return null;

  const writable = canWriteInventory(permissions);
  const markSoldAllowed = canMarkSold(permissions) && item.status !== 'sold' && !item.is_archived;
  const tallyLogs = workspace.auditLogs.filter((log) => log.source === 'TALLY_SYNC');
  const modelLabel = modelDisplayName(item);

  const startEdit = () => {
    setSerial(item.serial_number);
    setColor(item.color);
    setEditing(true);
  };

  const saveEdit = async () => {
    await workspace.updateItem({
      serial_number: serial.trim(),
      color: color.trim(),
    });
    setEditing(false);
  };

  return (
    <aside className="inv-drawer animate-slide-in" aria-label="Inventory item details">
      <header className="inv-drawer__header">
        <div>
          <p className="inv-drawer__eyebrow">Physical unit · {modelLabel}</p>
          <h2 className="inv-drawer__title col-mono">{item.serial_number}</h2>
          <InventoryStatusBadge item={item} />
        </div>
        <button type="button" className="app-toolbar-icon-btn" onClick={() => workspace.selectItem(null)} aria-label="Close drawer">
          <X size={16} aria-hidden />
        </button>
      </header>

      <div className="inv-drawer__actions">
        {writable && !item.is_archived && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={onTransfer} disabled={workspace.actionLoading}>
            <MapPin size={14} aria-hidden />
            Transfer
          </button>
        )}
        {markSoldAllowed && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={onMarkSold} disabled={workspace.actionLoading}>
            <ShoppingBag size={14} aria-hidden />
            Mark sold
          </button>
        )}
        {writable && !item.is_archived && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={onArchive} disabled={workspace.actionLoading}>
            <Archive size={14} aria-hidden />
            Archive
          </button>
        )}
        {writable && item.is_archived && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={onRestore} disabled={workspace.actionLoading}>
            <ArchiveRestore size={14} aria-hidden />
            Restore
          </button>
        )}
        {writable && (
          <button type="button" className="btn btn-ghost btn-sm" onClick={editing ? () => void saveEdit() : startEdit} disabled={workspace.actionLoading}>
            <Pencil size={14} aria-hidden />
            {editing ? 'Save' : 'Edit unit'}
          </button>
        )}
        <button type="button" className="btn btn-ghost btn-sm" disabled title="Coming soon">
          <Tag size={14} aria-hidden />
          Print label
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setQrOpen(true)}>
          <QrCode size={14} aria-hidden />
          QR
        </button>
      </div>

      <InventoryQrDialog
        open={qrOpen}
        serialNumber={item.serial_number}
        inventoryId={item.id}
        onClose={() => setQrOpen(false)}
      />

      {workspace.actionError && (
        <div className="inv-drawer__alert">
          <span>{workspace.actionError}</span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={workspace.clearActionError}>
            Dismiss
          </button>
        </div>
      )}

      <div className="inv-drawer__body">
        {workspace.drawerLoading ? (
          <div className="inv-drawer__loading">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="skeleton inv-drawer__skeleton" />
            ))}
          </div>
        ) : (
          <>
            <section className="inv-drawer__section">
              <h3 className="inv-drawer__section-title">Inventory information</h3>
              <p className="inv-drawer__section-lead">Fields unique to this physical laptop (serial-tracked unit).</p>
              <dl className="inv-detail-grid">
                <div>
                  <dt>Serial number</dt>
                  <dd className="col-mono">
                    {editing ? <input className="input" value={serial} onChange={(event) => setSerial(event.target.value)} /> : item.serial_number}
                  </dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd><InventoryStatusBadge item={item} /></dd>
                </div>
                <div>
                  <dt>Location</dt>
                  <dd>{item.current_location_name}</dd>
                </div>
                <div>
                  <dt>Date added</dt>
                  <dd>{formatDateTime(item.created_at)}</dd>
                </div>
                <div>
                  <dt>Unit color</dt>
                  <dd>{editing ? <input className="input" value={color} onChange={(event) => setColor(event.target.value)} /> : item.color}</dd>
                </div>
                {canViewPurchasePrice(permissions) && workspace.productModel && (
                  <div>
                    <dt>Purchase price (model)</dt>
                    <dd>{formatInventoryPrice(workspace.productModel.purchase_price)}</dd>
                  </div>
                )}
                {workspace.productModel && (
                  <div>
                    <dt>Selling price (model)</dt>
                    <dd>{formatInventoryPrice(workspace.productModel.selling_price)}</dd>
                  </div>
                )}
                <div>
                  <dt>Sale status</dt>
                  <dd>
                    <span className={`badge ${saleStatusBadgeClass(item.status, item.is_archived)}`}>
                      {saleStatusLabel(item.status, item.is_archived)}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt>Last updated</dt>
                  <dd>{formatDateTime(item.updated_at)}</dd>
                </div>
              </dl>
            </section>

            <section className="inv-drawer__section">
              <h3 className="inv-drawer__section-title">Lifecycle</h3>
              <p className="inv-drawer__section-lead">Received → Available → Transferred → Sold → Tally synced</p>
              <InventoryLifecycleStepper steps={lifecycleSteps} />
            </section>

            <section className="inv-drawer__section inv-drawer__section--catalogue">
              <h3 className="inv-drawer__section-title">Product model information</h3>
              <p className="inv-drawer__section-lead">
                Catalogue entry shared by {workspace.siblingUnits.length || 1} physical unit{(workspace.siblingUnits.length || 1) === 1 ? '' : 's'}.
                Specifications are maintained once per model.
              </p>
              <ProductImagePanel
                productModelId={item.product_model_id}
                modelName={item.model_name}
                imageUrl={workspace.productModel?.product_image_url ?? null}
                readOnly
              />
              <ProductModelSummaryPanel model={workspace.productModel} />
              <dl className="inv-detail-grid">
                <div>
                  <dt>Brand</dt>
                  <dd><InventoryBrandCell brandName={item.brand_name} /></dd>
                </div>
                <div>
                  <dt>Model</dt>
                  <dd>{modelLabel}</dd>
                </div>
                <div>
                  <dt>Generation</dt>
                  <dd>{workspace.productModel?.display ?? '—'}</dd>
                </div>
                <div>
                  <dt>Color variants</dt>
                  <dd>{colorVariantsLabel(workspace.productModel)}</dd>
                </div>
                <div className="inv-detail-grid__full">
                  <dt>Specifications</dt>
                  <dd>{formatInventorySpecs(item)}</dd>
                </div>
                {item.gpu && (
                  <div>
                    <dt>GPU</dt>
                    <dd>{item.gpu}</dd>
                  </div>
                )}
              </dl>
            </section>

            <section className="inv-drawer__section">
              <h3 className="inv-drawer__section-title">Other units of same model</h3>
              <InventorySiblingUnits
                units={workspace.siblingUnits}
                selectedId={item.id}
                modelLabel={modelLabel}
                onSelect={(id) => workspace.selectItem(id)}
              />
            </section>

            <section className="inv-drawer__section">
              <h3 className="inv-drawer__section-title">Movement history</h3>
              <InventoryMovementHistory auditLogs={workspace.auditLogs} />
            </section>

            <section className="inv-drawer__section">
              <h3 className="inv-drawer__section-title">Audit timeline</h3>
              {workspace.auditLogs.length === 0 ? (
                <p className="inv-drawer__muted">No audit entries for this unit.</p>
              ) : (
                <ul className="inv-audit-list">
                  {workspace.auditLogs.slice(0, 12).map((log) => (
                    <AuditRow key={log.id} log={log} />
                  ))}
                </ul>
              )}
            </section>

            <section className="inv-drawer__section">
              <h3 className="inv-drawer__section-title">Sale information</h3>
              {workspace.saleDetail ? (
                <dl className="inv-detail-grid">
                  <div>
                    <dt>Invoice</dt>
                    <dd>{workspace.saleDetail.invoice_number}</dd>
                  </div>
                  <div>
                    <dt>Customer</dt>
                    <dd>{workspace.saleDetail.customer_name ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Payment</dt>
                    <dd>{workspace.saleDetail.payment_mode ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Amount</dt>
                    <dd>{formatSaleAmount(workspace.saleDetail.sale_amount)}</dd>
                  </div>
                  <div>
                    <dt>Sold at</dt>
                    <dd>{formatDateTime(workspace.saleDetail.sold_at)}</dd>
                  </div>
                </dl>
              ) : (
                <p className="inv-drawer__muted">{item.status === 'sold' ? 'Sale details unavailable.' : 'Not sold.'}</p>
              )}
            </section>

            <section className="inv-drawer__section">
              <h3 className="inv-drawer__section-title">Tally information</h3>
              {tallyLogs.length > 0 ? (
                <ul className="inv-audit-list">
                  {tallyLogs.map((log) => (
                    <AuditRow key={log.id} log={log} />
                  ))}
                </ul>
              ) : (
                <p className="inv-drawer__muted">No Tally sync events recorded.</p>
              )}
            </section>
          </>
        )}
      </div>
    </aside>
  );
}
