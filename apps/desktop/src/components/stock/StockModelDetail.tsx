import { useState } from 'react';
import { MapPin, MoreHorizontal, Pencil } from 'lucide-react';
import type { InventoryItemDetail } from '../../services/api/InventoryService';
import type { Location } from '../../services/api/LocationService';
import type { ProductModel } from '../../services/api/ProductModelService';
import { TransferLocationDialog } from '../inventory/TransferLocationDialog';
import { ProductImagePanel } from '../inventory/ProductImagePanel';
import { canTransferStockLocation, canDeleteInventorySerial } from '../../lib/inventory';
import { buildStockModelSpecLines } from '../../lib/stockModelCard';
import { splitModelNotes } from '../../lib/modelNotes';
import { formatRelativeTime } from '../../lib/datetime';
import { StockSerialRowActionsMenu } from './StockSerialRowActionsMenu';

interface StockModelDetailProps {
  model: ProductModel;
  units: InventoryItemDetail[];
  locations: Location[];
  permissions: string[];
  loading?: boolean;
  onTransfer: (itemId: string, locationId: number) => Promise<void>;
  onDeleteSerial?: (itemId: string) => Promise<void>;
  actionLoading?: boolean;
  onEditModel?: () => void;
  editModelLabel?: string;
  showSellingPrice?: boolean;
  showAsusPrice?: boolean;
}

function formatCurrency(value: number | string | null | undefined): string | null {
  if (value === null || value === undefined || value === '' || Number(value) <= 0) return null;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
    .format(Number(value))
    .replace('₹', '₹ ');
}

export function StockModelDetail({
  model,
  units,
  locations,
  permissions,
  loading = false,
  onTransfer,
  onDeleteSerial,
  actionLoading,
  onEditModel,
  editModelLabel = 'Edit model & price',
  showSellingPrice = true,
  showAsusPrice = false,
}: StockModelDetailProps): JSX.Element {
  const canTransfer = canTransferStockLocation(permissions);
  const canDelete = canDeleteInventorySerial(permissions) && Boolean(onDeleteSerial);
  const showActions = canTransfer || canDelete;
  const available = units.filter((item) => item.status !== 'sold' && !item.is_archived);
  const specLines = buildStockModelSpecLines(model);
  const [menu, setMenu] = useState<{ item: InventoryItemDetail; rect: DOMRect } | null>(null);
  const [transferItem, setTransferItem] = useState<InventoryItemDetail | null>(null);

  const formattedPrice = formatCurrency(model.selling_price);
  const isAsusModel =
    model.brand_name?.trim().toUpperCase() === 'ASUS' && model.category !== 'accessory';
  const formattedLivePrice = isAsusModel ? formatCurrency(model.live_price) : null;
  const showPriceRow = (showSellingPrice && formattedPrice) || (showAsusPrice && isAsusModel);

  if (loading) {
    return <div className="skeleton stock-detail__skeleton" />;
  }

  const notesObj = splitModelNotes(model.notes);
  const notesText = notesObj.description || model.notes?.trim();

  return (
    <div className="stock-detail">
      <div className="stock-detail__hero">
        <ProductImagePanel
          productModelId={model.id}
          modelName={model.model_name}
          imageUrl={model.product_image_url}
          readOnly
        />
        <div className="stock-detail__info">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              gap: 12,
            }}
          >
            <div>
              {model.brand_name && <p className="stock-detail__brand">{model.brand_name}</p>}
              <h2 className="stock-detail__title">{model.model_name}</h2>
            </div>
            {onEditModel && (
              <button type="button" className="btn btn-secondary btn-sm" onClick={onEditModel}>
                <Pencil size={14} aria-hidden />
                {editModelLabel}
              </button>
            )}
          </div>
          <p className="stock-detail__model-number col-mono">{model.model_number}</p>

          {showPriceRow && (
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', margin: '12px 0 16px' }}>
              {showSellingPrice && formattedPrice && (
                <div
                  style={{
                    padding: '10px 14px',
                    background: 'rgba(234, 88, 12, 0.08)',
                    borderRadius: '6px',
                    border: '1px solid rgba(234, 88, 12, 0.2)',
                  }}
                >
                  <p
                    style={{
                      margin: 0,
                      fontSize: '11px',
                      fontWeight: 700,
                      color: 'var(--color-text-tertiary)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                    }}
                  >
                    Selling price
                  </p>
                  <p
                    style={{
                      margin: '2px 0 0',
                      fontSize: '22px',
                      fontWeight: 800,
                      color: '#ea580c',
                    }}
                  >
                    {formattedPrice}
                  </p>
                </div>
              )}
              {showAsusPrice && isAsusModel && (
                <div
                  style={{
                    padding: '10px 14px',
                    background: 'var(--color-bg-raised)',
                    borderRadius: '6px',
                    border: '1px solid var(--color-border)',
                  }}
                >
                  <p
                    style={{
                      margin: 0,
                      fontSize: '11px',
                      fontWeight: 700,
                      color: 'var(--color-text-tertiary)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                    }}
                  >
                    ASUS price
                  </p>
                  <p
                    style={{
                      margin: '2px 0 0',
                      fontSize: '22px',
                      fontWeight: 800,
                      color: 'var(--color-text-primary)',
                    }}
                  >
                    {formattedLivePrice ?? 'NA'}
                  </p>
                  {model.live_price_updated_at && (
                    <p
                      style={{
                        margin: '2px 0 0',
                        fontSize: '11px',
                        color: 'var(--color-text-tertiary)',
                      }}
                      title={model.live_price_source_url ?? undefined}
                    >
                      as of {formatRelativeTime(model.live_price_updated_at)}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          <dl className="stock-detail__spec-grid">
            {specLines.map((line) => (
              <div key={line.label} className="stock-detail__spec-row">
                <dt>{line.label}</dt>
                <dd>{line.value}</dd>
              </div>
            ))}
          </dl>

          {notesText && (
            <div
              style={{
                marginTop: '16px',
                padding: '12px 14px',
                background: 'var(--color-bg-raised)',
                borderRadius: '6px',
                border: '1px solid var(--color-border)',
              }}
            >
              <h4
                style={{
                  margin: '0 0 6px',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--color-text-secondary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                Additional details & description
              </h4>
              <p
                style={{
                  margin: 0,
                  fontSize: '13px',
                  lineHeight: 1.5,
                  color: 'var(--color-text-primary)',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {notesText}
              </p>
            </div>
          )}

          <p className="stock-detail__count">
            {available.length} unit{available.length === 1 ? '' : 's'} available
          </p>
        </div>
      </div>

      <section className="stock-detail__units" aria-labelledby="stock-detail-units-title">
        <header className="stock-detail__units-header">
          <div>
            <h3 id="stock-detail-units-title" className="stock-detail__units-title">
              Serial numbers
            </h3>
            <p className="stock-detail__units-subtitle">
              {available.length} active unit{available.length === 1 ? '' : 's'}
            </p>
          </div>
        </header>

        {available.length === 0 ? (
          <p className="stock-detail__empty">No available units for this model right now.</p>
        ) : (
          <div className="stock-detail__table-wrap">
            <table className="stock-detail__table">
              <thead>
                <tr>
                  <th scope="col">Serial number</th>
                  <th scope="col">Color</th>
                  <th scope="col">Location</th>
                  {showActions && (
                    <th scope="col" className="stock-detail__actions-col" aria-label="Actions" />
                  )}
                </tr>
              </thead>
              <tbody>
                {available.map((item) => (
                  <tr key={item.id}>
                    <td className="stock-detail__serial col-mono">{item.serial_number}</td>
                    <td className="stock-detail__color">{item.color || '—'}</td>
                    <td className="stock-detail__location">
                      <span className="stock-detail__location-pill">
                        <MapPin size={13} aria-hidden />
                        {item.current_location_name}
                      </span>
                    </td>
                    {showActions && (
                      <td className="stock-detail__actions-col">
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm stock-detail__more-btn"
                          aria-label={`More options for ${item.serial_number}`}
                          onClick={(event) => {
                            const rect = event.currentTarget.getBoundingClientRect();
                            setMenu((current) =>
                              current?.item.id === item.id ? null : { item, rect },
                            );
                          }}
                        >
                          <MoreHorizontal size={16} aria-hidden />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {menu && (
        <StockSerialRowActionsMenu
          item={menu.item}
          canTransfer={canTransfer}
          canDelete={canDelete}
          anchorRect={menu.rect}
          onClose={() => setMenu(null)}
          onChangeLocation={(item) => setTransferItem(item)}
          onDelete={(item) => {
            if (
              !window.confirm(
                `Delete serial ${item.serial_number} from live stock?\n\nThis removes the unit from available inventory. Past sales for this serial (if any) are not changed — sold units cannot be deleted.`,
              )
            ) {
              return;
            }
            void onDeleteSerial?.(item.id);
          }}
        />
      )}

      <TransferLocationDialog
        open={transferItem !== null}
        locations={locations}
        currentLocationId={transferItem?.current_location_id ?? 0}
        loading={Boolean(actionLoading)}
        onClose={() => setTransferItem(null)}
        onConfirm={async (locationId) => {
          if (!transferItem) return;
          await onTransfer(transferItem.id, locationId);
          setTransferItem(null);
        }}
      />
    </div>
  );
}
