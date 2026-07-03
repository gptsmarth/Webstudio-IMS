import { useRef } from 'react';
import { createPortal } from 'react-dom';
import { Pencil, Trash2 } from 'lucide-react';
import { rowMenuPosition, useRowActionsMenuDismiss } from '../../hooks/useRowActionsMenuDismiss';

export type CatalogueRowAction = 'edit' | 'delete';

interface CatalogueRowActionsMenuProps {
  label: string;
  canWrite: boolean;
  anchorRect: DOMRect;
  onAction: (action: CatalogueRowAction) => void;
  onClose: () => void;
  hideEdit?: boolean;
}

export function CatalogueRowActionsMenu({
  label,
  canWrite,
  anchorRect,
  onAction,
  onClose,
  hideEdit = false,
}: CatalogueRowActionsMenuProps): JSX.Element | null {
  const menuRef = useRef<HTMLDivElement>(null);

  useRowActionsMenuDismiss(menuRef, onClose);

  if (!canWrite) return null;

  const { top, left } = rowMenuPosition(anchorRect, 180);

  return createPortal(
    <div
      ref={menuRef}
      className="row-actions-menu cat-row-menu"
      style={{ top, left }}
      role="menu"
      aria-label={`Actions for ${label}`}
    >
      {!hideEdit && (
        <button
          type="button"
          className="cat-row-menu__item"
          role="menuitem"
          onClick={() => onAction('edit')}
        >
          <Pencil size={14} aria-hidden /> Edit
        </button>
      )}
      <button
        type="button"
        className="cat-row-menu__item cat-row-menu__item--danger"
        role="menuitem"
        onClick={() => onAction('delete')}
      >
        <Trash2 size={14} aria-hidden /> Delete
      </button>
    </div>,
    document.body,
  );
}
