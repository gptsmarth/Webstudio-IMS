import { useRef } from 'react';
import { createPortal } from 'react-dom';
import { Eye, FileDown, FileText, Printer } from 'lucide-react';
import type { SaleListItem } from '../../services/api/SalesService';
import { rowMenuPosition, useRowActionsMenuDismiss } from '../../hooks/useRowActionsMenuDismiss';

interface SalesRowActionsMenuProps {
  item: SaleListItem;
  onView: (item: SaleListItem) => void;
  onClose: () => void;
  anchorRect: DOMRect;
}

export function SalesRowActionsMenu({
  item,
  onView,
  onClose,
  anchorRect,
}: SalesRowActionsMenuProps): JSX.Element {
  const menuRef = useRef<HTMLDivElement>(null);

  useRowActionsMenuDismiss(menuRef, onClose);

  const { top, left } = rowMenuPosition(anchorRect, 220);

  return createPortal(
    <div
      ref={menuRef}
      className="row-actions-menu sales-row-menu"
      style={{ top, left }}
      role="menu"
      aria-label={`Actions for ${item.invoice_number}`}
    >
      <button
        type="button"
        className="sales-row-menu__item"
        role="menuitem"
        onClick={() => onView(item)}
      >
        <Eye size={14} aria-hidden /> View
      </button>
      <button
        type="button"
        className="sales-row-menu__item sales-row-menu__item--disabled"
        disabled
        title="Coming soon"
      >
        <Printer size={14} aria-hidden /> Print invoice
      </button>
      <button
        type="button"
        className="sales-row-menu__item sales-row-menu__item--disabled"
        disabled
        title="Coming soon"
      >
        <FileDown size={14} aria-hidden /> Re-export
      </button>
      <button
        type="button"
        className="sales-row-menu__item sales-row-menu__item--disabled"
        disabled
        title="Coming soon"
      >
        <FileText size={14} aria-hidden /> Preview PDF
      </button>
    </div>,
    document.body,
  );
}
