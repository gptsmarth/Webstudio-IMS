import { useState } from 'react';
import { MapPin, MoreHorizontal } from 'lucide-react';
import type { InventoryItemDetail } from '../../services/api/InventoryService';
import type { Location } from '../../services/api/LocationService';
import type { ProductModel } from '../../services/api/ProductModelService';
import { TransferLocationDialog } from '../inventory/TransferLocationDialog';
import { ProductImagePanel } from '../inventory/ProductImagePanel';
import { canTransferStockLocation } from '../../lib/inventory';
import { buildStockModelSpecLines } from '../../lib/stockModelCard';
import { StockSerialRowActionsMenu } from './StockSerialRowActionsMenu';

interface StockModelDetailProps {
  model: ProductModel;
  units: InventoryItemDetail[];
  locations: Location[];
  role: string;
  loading?: boolean;
  onTransfer: (itemId: string, locationId: number) => Promise<void>;
  actionLoading?: boolean;
}

export function StockModelDetail({
  model,
  units,
  locations,
  role,
  loading,
  onTransfer,
  actionLoading,
}: StockModelDetailProps): JSX.Element {
  const canTransfer = canTransferStockLocation(role);
  const available = units.filter((item) => item.status !== 'sold' && !item.is_archived);
  const specLines = buildStockModelSpecLines(model);
  const [menu, setMenu] = useState<{ item: InventoryItemDetail; rect: DOMRect } | null>(null);
  const [transferItem, setTransferItem] = useState<InventoryItemDetail | null>(null);

  if (loading) {
    return <div className="skeleton stock-detail__skeleton" />;
  }

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
          {model.brand_name && (
            <p className="stock-detail__brand">{model.brand_name}</p>
          )}
          <h2 className="stock-detail__title">{model.model_name}</h2>
          <p className="stock-detail__model-number col-mono">{model.model_number}</p>
          <dl className="stock-detail__spec-grid">
            {specLines.map((line) => (
              <div key={line.label} className="stock-detail__spec-row">
                <dt>{line.label}</dt>
                <dd>{line.value}</dd>
              </div>
            ))}
          </dl>
          <p className="stock-detail__count">
            {available.length} unit{available.length === 1 ? '' : 's'} available
          </p>
        </div>
      </div>

      <section className="stock-detail__units" aria-labelledby="stock-detail-units-title">
        <header className="stock-detail__units-header">
          <div>
            <h3 id="stock-detail-units-title" className="stock-detail__units-title">Serial numbers</h3>
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
                  {canTransfer && <th scope="col" className="stock-detail__actions-col" aria-label="Actions" />}
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
                    {canTransfer && (
                      <td className="stock-detail__actions-col">
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm stock-detail__more-btn"
                          aria-label={`More options for ${item.serial_number}`}
                          onClick={(event) => {
                            const rect = event.currentTarget.getBoundingClientRect();
                            setMenu((current) => (
                              current?.item.id === item.id ? null : { item, rect }
                            ));
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
          anchorRect={menu.rect}
          onClose={() => setMenu(null)}
          onChangeLocation={(item) => setTransferItem(item)}
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
