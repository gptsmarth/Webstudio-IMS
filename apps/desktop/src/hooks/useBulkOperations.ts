import { useCallback } from 'react';
import type { BulkOperationType } from '../lib/bulkOperations';

export interface BulkOperationContext {
  selectedIds: string[];
  canWrite: boolean;
}

export interface BulkOperationCallbacks {
  onImport: () => void;
  onTransfer: () => void;
  onArchive: (ids: string[]) => Promise<void>;
  onRestore: (ids: string[]) => Promise<void>;
  onStatusUpdate: (ids: string[]) => void;
  onExport: (ids: string[]) => void;
}

export function useBulkOperations(
  context: BulkOperationContext,
  callbacks: BulkOperationCallbacks,
): (operation: BulkOperationType) => void {
  const { selectedIds, canWrite } = context;

  return useCallback(
    (operation: BulkOperationType) => {
      switch (operation) {
        case 'import':
          callbacks.onImport();
          break;
        case 'transfer':
          if (selectedIds.length > 0) callbacks.onTransfer();
          break;
        case 'archive':
          if (canWrite && selectedIds.length > 0) void callbacks.onArchive(selectedIds);
          break;
        case 'restore':
          if (canWrite && selectedIds.length > 0) void callbacks.onRestore(selectedIds);
          break;
        case 'status_update':
          if (canWrite && selectedIds.length > 0) callbacks.onStatusUpdate(selectedIds);
          break;
        case 'export':
          if (selectedIds.length > 0) callbacks.onExport(selectedIds);
          break;
        default:
          break;
      }
    },
    [callbacks, canWrite, selectedIds],
  );
}
