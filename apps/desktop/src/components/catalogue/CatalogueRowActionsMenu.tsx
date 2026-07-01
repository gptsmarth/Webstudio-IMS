import { useRef } from 'react';
import { createPortal } from 'react-dom';
import { Archive, ArchiveRestore, Pencil, Trash2 } from 'lucide-react';
import { rowMenuPosition, useRowActionsMenuDismiss } from '../../hooks/useRowActionsMenuDismiss';

export type CatalogueRowAction = 'edit' | 'archive' | 'restore';

interface CatalogueRowActionsMenuProps {
  label: string;
  canWrite: boolean;
  isArchived: boolean;
  anchorRect: DOMRect;
  onAction: (action: CatalogueRowAction) => void;
  onClose: () => void;
  hideEdit?: boolean;
  permanentDelete?: boolean;
}

export function CatalogueRowActionsMenu({
  label,
  canWrite,
  isArchived,
  anchorRect,
  onAction,
  onClose,
  hideEdit = false,
  permanentDelete = false,
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
        <button type="button" className="cat-row-menu__item" role="menuitem" onClick={() => onAction('edit')}>
          <Pencil size={14} aria-hidden /> Edit
        </button>
      )}
      {!isArchived && (
        <button type="button" className="cat-row-menu__item" role="menuitem" onClick={() => onAction('archive')}>
          {permanentDelete ? <Trash2 size={14} aria-hidden /> : <Archive size={14} aria-hidden />}
          {permanentDelete ? 'Delete' : 'Remove'}
        </button>
      )}
      {isArchived && !permanentDelete && (
        <button type="button" className="cat-row-menu__item" role="menuitem" onClick={() => onAction('restore')}>
          <ArchiveRestore size={14} aria-hidden /> Restore
        </button>
      )}
    </div>,
    document.body,
  );
}
