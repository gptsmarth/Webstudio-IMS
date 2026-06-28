import type { InventoryItemDetail } from '../../../services/api/InventoryService';
import type { Location } from '../../../services/api/LocationService';
import { InventoryStatusBadge } from '../InventoryStatusBadge';
import { parsePriceInput } from '../../../lib/inventoryPrice';
import { ShoppingBag } from 'lucide-react';

interface AdminSerialTableProps {
  units: InventoryItemDetail[];
  locations: Location[];
  loading?: boolean;
  selectedId: string | null;
  showPurchasePrice?: boolean;
  onSelect: (id: string) => void;
  onTransfer: (itemId: string, locationId: number) => Promise<void>;
  onMarkSold: (itemId: string) => void;
  onUpdatePrices?: (itemId: string, patch: { purchase_price?: number | null; selling_price?: number | null }) => Promise<void>;
  actionLoading?: boolean;
}

export function AdminSerialTable({
  units,
  locations,
  loading,
  selectedId,
  showPurchasePrice = true,
  onSelect,
  onTransfer,
  onMarkSold,
  onUpdatePrices,
  actionLoading,
}: AdminSerialTableProps): JSX.Element {
  if (loading) {
    return <div className="skeleton admin-serial-table__skeleton" />;
  }

  const available = units.filter((item) => !item.is_archived);
  const colSpan = 5 + (showPurchasePrice ? 1 : 0) + 1;

  const savePrice = async (item: InventoryItemDetail, field: 'purchase_price' | 'selling_price', raw: string) => {
    if (!onUpdatePrices) return;
    const parsed = parsePriceInput(raw);
    const current = item[field] ?? null;
    if (parsed === current) return;
    if (raw.trim() && parsed === null) return;
    await onUpdatePrices(item.id, { [field]: parsed });
  };

  return (
    <div className="admin-serial-panel">
      <div className="admin-serial-panel__header">
        <h2 className="admin-serial-panel__title">Serial numbers</h2>
        <p className="admin-serial-panel__subtitle">{available.length} active unit{available.length === 1 ? '' : 's'}</p>
      </div>
      <div className="admin-serial-table-wrap">
        <table className="table-root admin-serial-table">
          <thead>
            <tr>
              <th>Serial number</th>
              <th>Status</th>
              <th>Color</th>
              {showPurchasePrice && <th>Purchase price</th>}
              <th>Selling price</th>
              <th>Location</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {available.length === 0 && (
              <tr>
                <td colSpan={colSpan} className="admin-serial-table__empty">No serial numbers for this model.</td>
              </tr>
            )}
            {available.map((item) => (
              <tr
                key={item.id}
                className={selectedId === item.id ? 'admin-serial-table__row--selected' : ''}
                onClick={() => onSelect(item.id)}
              >
                <td className="col-mono">{item.serial_number}</td>
                <td><InventoryStatusBadge item={item} /></td>
                <td>{item.color}</td>
                {showPurchasePrice && (
                  <td onClick={(event) => event.stopPropagation()}>
                    <input
                      className="input input-sm inv-price-input"
                      type="text"
                      inputMode="decimal"
                      defaultValue={item.purchase_price ?? ''}
                      key={`${item.id}-purchase-${item.purchase_price ?? 'empty'}`}
                      disabled={actionLoading || !onUpdatePrices}
                      placeholder="—"
                      onBlur={(event) => void savePrice(item, 'purchase_price', event.target.value)}
                    />
                  </td>
                )}
                <td onClick={(event) => event.stopPropagation()}>
                  <input
                    className="input input-sm inv-price-input"
                    type="text"
                    inputMode="decimal"
                    defaultValue={item.selling_price ?? ''}
                    key={`${item.id}-selling-${item.selling_price ?? 'empty'}`}
                    disabled={actionLoading || !onUpdatePrices}
                    placeholder="—"
                    onBlur={(event) => void savePrice(item, 'selling_price', event.target.value)}
                  />
                </td>
                <td onClick={(event) => event.stopPropagation()}>
                  {item.status !== 'sold' ? (
                    <select
                      className="input input-sm"
                      value={item.current_location_id}
                      disabled={actionLoading}
                      onChange={(event) => void onTransfer(item.id, Number(event.target.value))}
                    >
                      {locations.map((location) => (
                        <option key={location.id} value={location.id}>{location.name}</option>
                      ))}
                    </select>
                  ) : (
                    item.current_location_name
                  )}
                </td>
                <td onClick={(event) => event.stopPropagation()}>
                  {item.status !== 'sold' && !item.is_archived && (
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => onMarkSold(item.id)}
                      disabled={actionLoading}
                    >
                      <ShoppingBag size={12} aria-hidden />
                      Mark sold
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
