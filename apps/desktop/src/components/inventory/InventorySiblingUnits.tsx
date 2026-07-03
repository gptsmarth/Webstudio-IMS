import type { InventoryItemDetail } from '../../services/api/InventoryService';
import { formatInventoryDate } from '../../lib/inventory';
import { InventoryStatusBadge } from './InventoryStatusBadge';

interface InventorySiblingUnitsProps {
  units: InventoryItemDetail[];
  selectedId: string;
  onSelect: (id: string) => void;
  modelLabel: string;
}

export function InventorySiblingUnits({
  units,
  selectedId,
  onSelect,
  modelLabel,
}: InventorySiblingUnitsProps): JSX.Element {
  const siblings = units.filter((unit) => unit.id !== selectedId);

  if (siblings.length === 0) {
    return (
      <p className="inv-drawer__muted">No other physical units registered for {modelLabel}.</p>
    );
  }

  return (
    <div className="inv-sibling-units">
      <p className="inv-sibling-units__intro">
        {siblings.length + 1} serial numbers share this product model. Select another unit to
        inspect it.
      </p>
      <ul className="inv-sibling-units__list">
        {units.map((unit) => (
          <li key={unit.id}>
            <button
              type="button"
              className={`inv-sibling-units__row ${unit.id === selectedId ? 'inv-sibling-units__row--active' : ''}`}
              onClick={() => onSelect(unit.id)}
              aria-current={unit.id === selectedId ? 'true' : undefined}
            >
              <span className="col-mono inv-sibling-units__serial">{unit.serial_number}</span>
              <InventoryStatusBadge item={unit} />
              <span className="inv-sibling-units__meta">{unit.current_location_name}</span>
              <span className="inv-sibling-units__meta">
                {formatInventoryDate(unit.created_at)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
