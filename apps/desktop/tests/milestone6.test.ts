import { describe, expect, it } from 'vitest';
import { canRunBulkOperation, BULK_OPERATIONS } from '../src/lib/bulkOperations';
import { buildInventoryLifecycle } from '../src/lib/inventoryLifecycle';
import { extractMovementHistory, formatMovementChain } from '../src/lib/inventoryMovement';
import { buildInventoryQrPayload, serializeInventoryQrPayload } from '../src/lib/inventoryQr';
import { matchesNotificationSearch, notificationTypeLabel } from '../src/lib/notificationCategories';
import type { InventoryItemDetail } from '../src/services/api/InventoryService';
import type { AuditLogEntry } from '../src/services/api/AuditService';

const baseItem = {
  id: 'inv-1',
  serial_number: 'SN001',
  status: 'available',
  is_archived: false,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
} as InventoryItemDetail;

describe('inventory lifecycle', () => {
  it('marks received and available for new units', () => {
    const steps = buildInventoryLifecycle({ ...baseItem, status: 'received' }, []);
    expect(steps.find((step) => step.id === 'received')?.complete).toBe(true);
    expect(steps.find((step) => step.id === 'available')?.current).toBe(false);
  });

  it('counts transfers from location change audits', () => {
    const audits: AuditLogEntry[] = [
      {
        id: 'a1',
        action: 'LOCATION_CHANGE',
        source: 'USER',
        created_at: '2026-01-03T00:00:00Z',
        old_value: { current_location_name: 'Warehouse' },
        new_value: { current_location_name: 'WEBSTUDIO Store' },
      } as AuditLogEntry,
    ];
    const steps = buildInventoryLifecycle(baseItem, audits);
    expect(steps.find((step) => step.id === 'transferred')?.complete).toBe(true);
    expect(steps.find((step) => step.id === 'transferred')?.detail).toContain('1 movement');
  });
});

describe('movement history', () => {
  it('builds a location chain from audits', () => {
    const audits: AuditLogEntry[] = [
      {
        id: 'a1',
        action: 'LOCATION_CHANGE',
        created_at: '2026-01-01T00:00:00Z',
        old_value: { current_location_name: 'Warehouse' },
        new_value: { current_location_name: 'WEBSTUDIO Store' },
      },
      {
        id: 'a2',
        action: 'LOCATION_CHANGE',
        created_at: '2026-01-02T00:00:00Z',
        old_value: { current_location_name: 'WEBSTUDIO Store' },
        new_value: { current_location_name: 'ASUS Store' },
      },
    ] as AuditLogEntry[];

    const moves = extractMovementHistory(audits);
    expect(moves).toHaveLength(2);
    expect(formatMovementChain(moves)).toBe('Warehouse → WEBSTUDIO Store → ASUS Store');
  });
});

describe('bulk operations', () => {
  it('allows import without selection', () => {
    const importOp = BULK_OPERATIONS.find((op) => op.id === 'import')!;
    expect(canRunBulkOperation(importOp, 0)).toBe(true);
  });

  it('requires selection for transfer', () => {
    const transferOp = BULK_OPERATIONS.find((op) => op.id === 'transfer')!;
    expect(canRunBulkOperation(transferOp, 0)).toBe(false);
    expect(canRunBulkOperation(transferOp, 2)).toBe(true);
  });
});

describe('inventory QR payload', () => {
  it('serializes versioned scanner payload', () => {
    const payload = buildInventoryQrPayload('inv-1', 'SN001');
    expect(JSON.parse(serializeInventoryQrPayload(payload))).toEqual({
      v: 1,
      type: 'inventory',
      id: 'inv-1',
      serial: 'SN001',
    });
  });
});

describe('notification categories', () => {
  it('labels tally sync types', () => {
    expect(notificationTypeLabel('tally_sync_completed')).toBe('Tally sync completed');
    expect(notificationTypeLabel('product_model_mismatch')).toBe('Tally model mismatch');
  });

  it('matches search across title and serial', () => {
    const item = {
      title: 'Inventory sold',
      description: 'Unit moved to sold',
      notification_type: 'inventory_alert',
      serial_number: 'SN999',
      category: 'inventory',
      severity: 'info',
    } as const;

    expect(matchesNotificationSearch(item, 'sn999')).toBe(true);
    expect(matchesNotificationSearch(item, 'missing')).toBe(false);
  });
});
