import { inventoryStatusBadgeClass, inventoryStatusLabel } from '../../lib/inventory';
import type { InventoryItemDetail } from '../../services/api/InventoryService';

interface InventoryStatusBadgeProps {
  item: Pick<InventoryItemDetail, 'status' | 'is_archived'>;
}

export function InventoryStatusBadge({ item }: InventoryStatusBadgeProps): JSX.Element {
  const label = item.is_archived ? 'Archived' : inventoryStatusLabel(item.status);
  const className = item.is_archived
    ? 'badge-neutral'
    : inventoryStatusBadgeClass(item.status, item.is_archived);

  return <span className={`badge ${className}`}>{label}</span>;
}
