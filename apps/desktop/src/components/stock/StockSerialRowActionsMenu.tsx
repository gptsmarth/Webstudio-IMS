import { useRef } from 'react';
import { createPortal } from 'react-dom';
import { MapPin } from 'lucide-react';
import type { InventoryItemDetail } from '../../services/api/InventoryService';
import { rowMenuPosition, useRowActionsMenuDismiss } from '../../hooks/useRowActionsMenuDismiss';

interface StockSerialRowActionsMenuProps {
  item: InventoryItemDetail;
  canTransfer: boolean;
  onChangeLocation: (item: InventoryItemDetail) => void;
  onClose: () => void;
  anchorRect: DOMRect;
}

export function StockSerialRowActionsMenu({
  item,
  canTransfer,
  onChangeLocation,
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
