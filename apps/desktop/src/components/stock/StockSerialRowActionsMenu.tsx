import { useRef } from 'react';
import { createPortal } from 'react-dom';
import { IndianRupee, MapPin } from 'lucide-react';
import type { InventoryItemDetail } from '../../services/api/InventoryService';
import { rowMenuPosition, useRowActionsMenuDismiss } from '../../hooks/useRowActionsMenuDismiss';

interface StockSerialRowActionsMenuProps {
  item: InventoryItemDetail;
  canTransfer: boolean;
  canEditSellingPrice: boolean;
  onChangeLocation: (item: InventoryItemDetail) => void;
  onEditSellingPrice: (item: InventoryItemDetail) => void;
  onClose: () => void;
  anchorRect: DOMRect;
}

export function StockSerialRowActionsMenu({
  item,
  canTransfer,
  canEditSellingPrice,
  onChangeLocation,
  onEditSellingPrice,
  onClose,
  anchorRect,
}: StockSerialRowActionsMenuProps): JSX.Element {
  const menuRef = useRef<HTMLDivElement>(null);

  useRowActionsMenuDismiss(menuRef, onClose);

  const { top, left } = rowMenuPosition(anchorRect, 160);

  return createPortal(
    <div
      ref={menuRef}
      className="row-actions-menu stock-serial-menu"
      style={{ top, left }}
      role="menu"
      aria-label={`Actions for ${item.serial_number}`}
    >
      {canEditSellingPrice && (
        <button
          type="button"
          className="inv-row-menu__item"
          role="menuitem"
          onClick={() => {
            onEditSellingPrice(item);
            onClose();
          }}
        >
          <IndianRupee size={14} aria-hidden />
          Edit selling price
        </button>
      )}
      {canTransfer && (
        <button
          type="button"
          className="inv-row-menu__item"
          role="menuitem"
          onClick={() => {
            onChangeLocation(item);
            onClose();
          }}
        >
          <MapPin size={14} aria-hidden />
          Change location
        </button>
      )}
    </div>,
    document.body,
  );
}
