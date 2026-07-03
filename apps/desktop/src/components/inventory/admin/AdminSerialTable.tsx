import type { InventoryItemDetail } from '../../../services/api/InventoryService';
import type { Location } from '../../../services/api/LocationService';
import { InventoryStatusBadge } from '../InventoryStatusBadge';

interface AdminSerialTableProps {
  units: InventoryItemDetail[];
  locations: Location[];
  loading?: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onTransfer: (itemId: string, locationId: number) => Promise<void>;
  onMarkSold: (itemId: string) => void;
  actionLoading?: boolean;
}

export function AdminSerialTable({
  units,
  locations,
  loading,
  selectedId,
  onSelect,
  onTransfer,
  onMarkSold,
  actionLoading,
}: AdminSerialTableProps): JSX.Element {
  if (loading) {
    return <div className="skeleton admin-serial-table__skeleton" />;
  }

  const activeUnits = units.filter((item) => !item.is_archived);
  const activeLabel = `${activeUnits.length} active unit${activeUnits.length === 1 ? '' : 's'}`;

  return (
    <section className="admin-serial-panel" aria-labelledby="admin-serial-panel-title">
      <header className="admin-serial-panel__header">
        <h2 id="admin-serial-panel-title" className="admin-serial-panel__title">
          Serial numbers
        </h2>
        <p className="admin-serial-panel__meta">{activeLabel}</p>
      </header>

      <div className="admin-serial-table-wrap">
        <table className="table-root admin-serial-table">
          <thead>
            <tr>
              <th scope="col">Serial number</th>
              <th scope="col">Status</th>
              <th scope="col">Color</th>
              <th scope="col">Location</th>
              <th scope="col" className="admin-serial-table__actions-col">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {activeUnits.length === 0 && (
              <tr>
                <td colSpan={5} className="admin-serial-table__empty">
                  No serial numbers for this model.
                </td>
              </tr>
            )}
            {activeUnits.map((item) => {
              const isSelected = selectedId === item.id;
              const canTransfer = item.status !== 'sold';

              return (
                <tr
                  key={item.id}
                  className={isSelected ? 'admin-serial-table__row--selected' : undefined}
                  onClick={() => onSelect(item.id)}
                >
                  <td className="col-mono admin-serial-table__serial">{item.serial_number}</td>
                  <td>
                    <InventoryStatusBadge item={item} />
                  </td>
                  <td className="admin-serial-table__color">{item.color || '—'}</td>
                  <td
                    className="admin-serial-table__location"
                    onClick={(event) => event.stopPropagation()}
                  >
                    {canTransfer ? (
                      <select
                        className="admin-serial-table__select"
                        value={item.current_location_id}
                        disabled={actionLoading}
                        aria-label={`Location for ${item.serial_number}`}
                        onChange={(event) => void onTransfer(item.id, Number(event.target.value))}
                      >
                        {locations.map((location) => (
                          <option key={location.id} value={location.id}>
                            {location.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span>{item.current_location_name}</span>
                    )}
                  </td>
                  <td
                    className="admin-serial-table__actions-col"
                    onClick={(event) => event.stopPropagation()}
                  >
                    {item.status === 'available' && (
                      <button
                        type="button"
                        className="admin-serial-table__action"
                        disabled={actionLoading}
                        onClick={() => onMarkSold(item.id)}
                      >
                        Mark sold
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
