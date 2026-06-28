import type { InventoryItemDetail } from '../services/api/InventoryService';
import type { AuditLogEntry } from '../services/api/AuditService';

export type LifecycleStepId = 'received' | 'available' | 'transferred' | 'sold' | 'tally_synced';

export interface LifecycleStep {
  id: LifecycleStepId;
  label: string;
  complete: boolean;
  current: boolean;
  detail?: string;
}

export function buildInventoryLifecycle(
  item: InventoryItemDetail,
  auditLogs: AuditLogEntry[],
): LifecycleStep[] {
  const transferCount = auditLogs.filter((log) => log.action === 'LOCATION_CHANGE').length;
  const hasTally = auditLogs.some((log) => log.source === 'TALLY_SYNC')
    || item.status === 'sold' && auditLogs.some((log) =>
      log.action === 'STATUS_CHANGE' && log.source === 'TALLY_SYNC',
    );

  const received = true;
  const available = ['available', 'reserved', 'sold'].includes(item.status);
  const transferred = transferCount > 0;
  const sold = item.status === 'sold';
  const tallySynced = hasTally && sold;

  const currentId: LifecycleStepId = (() => {
    if (tallySynced) return 'tally_synced';
    if (sold) return 'sold';
    if (item.status === 'available' || item.status === 'reserved') return transferred ? 'transferred' : 'available';
    if (item.status === 'received') return 'received';
    return 'available';
  })();

  const steps: Array<Omit<LifecycleStep, 'current'> & { id: LifecycleStepId }> = [
    { id: 'received', label: 'Received', complete: received, detail: 'Unit registered' },
    {
      id: 'available',
      label: 'Available',
      complete: available,
      detail: item.status === 'available' ? 'Ready for sale' : available ? 'Stock available' : undefined,
    },
    {
      id: 'transferred',
      label: 'Transferred',
      complete: transferred,
      detail: transferCount > 0 ? `${transferCount} movement${transferCount === 1 ? '' : 's'}` : 'No transfers yet',
    },
    { id: 'sold', label: 'Sold', complete: sold, detail: sold ? 'Sale recorded' : undefined },
    { id: 'tally_synced', label: 'Tally synced', complete: tallySynced, detail: tallySynced ? 'Reflected in Tally' : undefined },
  ];

  return steps.map((step) => ({
    ...step,
    current: step.id === currentId,
  }));
}
