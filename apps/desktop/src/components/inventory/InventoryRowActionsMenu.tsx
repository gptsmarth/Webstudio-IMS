import { useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  Archive,
  ArchiveRestore,
  Eye,
  MapPin,
  Pencil,
  QrCode,
  ShoppingBag,
  Tag,
} from 'lucide-react';
import type { InventoryItemDetail } from '../../services/api/InventoryService';
import { rowMenuPosition, useRowActionsMenuDismiss } from '../../hooks/useRowActionsMenuDismiss';

export type RowAction = 'view' | 'edit' | 'transfer' | 'markSold' | 'archive' | 'restore';

interface InventoryRowActionsMenuProps {
  item: InventoryItemDetail;
  canWrite: boolean;
  canSell: boolean;
  onAction: (action: RowAction, item: InventoryItemDetail) => void;
  onClose: () => void;
  anchorRect: DOMRect;
}

export function InventoryRowActionsMenu({
  item,
  canWrite,
  canSell,
  onAction,
  onClose,
  anchorRect,
}: InventoryRowActionsMenuProps): JSX.Element {
  const menuRef = useRef<HTMLDivElement>(null);

  useRowActionsMenuDismiss(menuRef, onClose);

  const { top, left } = rowMenuPosition(anchorRect, 280);

  return createPortal(
    <div
      ref={menuRef}
      className="row-actions-menu inv-row-menu"
      style={{ top, left }}
      role="menu"
      aria-label={`Actions for ${item.serial_number}`}
    >
      <button
        type="button"
        className="inv-row-menu__item"
        role="menuitem"
        onClick={() => onAction('view', item)}
      >
        <Eye size={14} aria-hidden /> View
      </button>
      {canWrite && (
        <button
          type="button"
          className="inv-row-menu__item"
          role="menuitem"
          onClick={() => onAction('edit', item)}
        >
          <Pencil size={14} aria-hidden /> Edit
        </button>
      )}
      {canWrite && !item.is_archived && item.status !== 'sold' && (
        <button
          type="button"
          className="inv-row-menu__item"
          role="menuitem"
          onClick={() => onAction('transfer', item)}
        >
          <MapPin size={14} aria-hidden /> Transfer
        </button>
      )}
      {canSell && item.status !== 'sold' && !item.is_archived && (
        <button
          type="button"
          className="inv-row-menu__item"
          role="menuitem"
          onClick={() => onAction('markSold', item)}
        >
          <ShoppingBag size={14} aria-hidden /> Mark sold
        </button>
      )}
      {canWrite && !item.is_archived && (
        <button
          type="button"
          className="inv-row-menu__item"
          role="menuitem"
          onClick={() => onAction('archive', item)}
        >
          <Archive size={14} aria-hidden /> Archive
        </button>
      )}
      {canWrite && item.is_archived && (
        <button
          type="button"
          className="inv-row-menu__item"
          role="menuitem"
          onClick={() => onAction('restore', item)}
        >
          <ArchiveRestore size={14} aria-hidden /> Restore
        </button>
      )}
      <button
        type="button"
        className="inv-row-menu__item inv-row-menu__item--disabled"
        disabled
        title="Coming soon"
      >
        <QrCode size={14} aria-hidden /> Generate QR
      </button>
      <button
        type="button"
        className="inv-row-menu__item inv-row-menu__item--disabled"
        disabled
        title="Coming soon"
      >
        <Tag size={14} aria-hidden /> Print label
      </button>
    </div>,
    document.body,
  );
}
