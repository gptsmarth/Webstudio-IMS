export type BulkOperationType =
  | 'import'
  | 'transfer'
  | 'archive'
  | 'restore'
  | 'status_update'
  | 'export';

export interface BulkOperationDefinition {
  id: BulkOperationType;
  label: string;
  description: string;
  requiresSelection: boolean;
  minSelection: number;
}

export const BULK_OPERATIONS: BulkOperationDefinition[] = [
  {
    id: 'import',
    label: 'Bulk import',
    description: 'Add multiple serial numbers under one product model.',
    requiresSelection: false,
    minSelection: 0,
  },
  {
    id: 'transfer',
    label: 'Bulk transfer',
    description: 'Move selected units to another location.',
    requiresSelection: true,
    minSelection: 1,
  },
  {
    id: 'archive',
    label: 'Bulk archive',
    description: 'Archive selected inventory items.',
    requiresSelection: true,
    minSelection: 1,
  },
  {
    id: 'restore',
    label: 'Bulk restore',
    description: 'Restore archived inventory items.',
    requiresSelection: true,
    minSelection: 1,
  },
  {
    id: 'status_update',
    label: 'Bulk status update',
    description: 'Update status for selected units (e.g. received → available).',
    requiresSelection: true,
    minSelection: 1,
  },
  {
    id: 'export',
    label: 'Bulk export',
    description: 'Export selected serial numbers to spreadsheet.',
    requiresSelection: true,
    minSelection: 1,
  },
];

export function canRunBulkOperation(
  operation: BulkOperationDefinition,
  selectedCount: number,
): boolean {
  if (!operation.requiresSelection) return true;
  return selectedCount >= operation.minSelection;
}
