import { X } from 'lucide-react';
import {
  BULK_OPERATIONS,
  canRunBulkOperation,
  type BulkOperationType,
} from '../../lib/bulkOperations';

interface BulkOperationsDialogProps {
  open: boolean;
  selectedCount: number;
  onClose: () => void;
  onSelect: (operation: BulkOperationType) => void;
}

export function BulkOperationsDialog({
  open,
  selectedCount,
  onClose,
  onSelect,
}: BulkOperationsDialogProps): JSX.Element | null {
  if (!open) return null;

  return (
    <div className="inv-dialog-overlay" role="presentation" onClick={onClose}>
      <div
        className="inv-dialog inv-dialog--wide animate-slide-in"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="inv-dialog__header">
          <div>
            <h2 className="inv-dialog__title">Bulk operations</h2>
            <p className="inv-dialog__lead">
              Reusable architecture for import, transfer, archive, restore, status, and export.
            </p>
          </div>
          <button
            type="button"
            className="app-toolbar-icon-btn"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={16} aria-hidden />
          </button>
        </header>
        <div className="inv-dialog__body bulk-ops">
          {selectedCount > 0 && (
            <p className="bulk-ops__selection">
              {selectedCount} unit{selectedCount === 1 ? '' : 's'} selected
            </p>
          )}
          <ul className="bulk-ops__list">
            {BULK_OPERATIONS.map((operation) => {
              const enabled = canRunBulkOperation(operation, selectedCount);
              return (
                <li key={operation.id}>
                  <button
                    type="button"
                    className="bulk-ops__item"
                    disabled={!enabled}
                    onClick={() => onSelect(operation.id)}
                  >
                    <span className="bulk-ops__label">{operation.label}</span>
                    <span className="bulk-ops__desc">{operation.description}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}
