import { describe, expect, it } from 'vitest';
import {
  auditSeverityBadgeClass,
  auditSeverityLabel,
  buildAuditTimeline,
  canReadAudit,
  formatActorRole,
  timelineLabel,
} from '../src/lib/audit';
import { auditFiltersToExportParams, hasActiveAuditFilters } from '../src/lib/auditExport';
import { DEFAULT_AUDIT_FILTERS } from '../src/hooks/useAuditWorkspace';
import type { AuditListEntry } from '../src/services/api/AuditService';

function entry(overrides: Partial<AuditListEntry> = {}): AuditListEntry {
  return {
    id: '1',
    entity_type: 'inventory_item',
    entity_id: 'abc',
    inventory_item_id: 'abc',
    actor_user_id: 1,
    actor_display_name: 'Admin',
    actor_role: 'admin',
    action: 'CREATE',
    source: 'MANUAL',
    field_name: null,
    old_value: null,
    new_value: null,
    description: 'Laptop added',
    created_at: '2026-01-01T10:00:00Z',
    module: 'Inventory',
    operation: 'Create',
    serial_number: 'SN-001',
    location_name: 'Store A',
    invoice_number: null,
    model_number: 'X1',
    result: 'success',
    ...overrides,
  };
}

describe('audit helpers', () => {
  it('checks audit:view permission', () => {
    expect(canReadAudit(['audit:view'])).toBe(true);
    expect(canReadAudit(['audit:lifecycle'])).toBe(false);
  });

  it('formats actor roles', () => {
    expect(formatActorRole('system')).toBe('System');
    expect(formatActorRole('admin')).toBe('Administrator');
  });

  it('builds timeline labels', () => {
    expect(timelineLabel(entry({ action: 'CREATE', module: 'Inventory' }))).toBe('Laptop added');
    expect(timelineLabel(entry({ action: 'LOCATION_CHANGE' }))).toBe('Transferred');
    expect(timelineLabel(entry({ source: 'TALLY_SYNC' }))).toBe('Tally synced');
  });

  it('orders timeline chronologically', () => {
    const steps = buildAuditTimeline([
      entry({ id: '2', created_at: '2026-01-02T10:00:00Z', action: 'LOCATION_CHANGE' }),
      entry({ id: '1', created_at: '2026-01-01T10:00:00Z', action: 'CREATE' }),
    ]);
    expect(steps.map((step) => step.id)).toEqual(['1', '2']);
  });

  it('formats severity badges', () => {
    expect(auditSeverityLabel('critical')).toBe('Critical');
    expect(auditSeverityBadgeClass('high')).toContain('aud-badge--high');
  });

  it('maps security filters to export params', () => {
    expect(
      auditFiltersToExportParams(
        { ...DEFAULT_AUDIT_FILTERS, module: 'Security', severity: 'critical' },
        '',
      ).security_only,
    ).toBe(true);
    expect(
      auditFiltersToExportParams({ ...DEFAULT_AUDIT_FILTERS, severity: 'high' }, '').audit_severity,
    ).toBe('high');
  });

  it('requires filters before export', () => {
    expect(hasActiveAuditFilters(DEFAULT_AUDIT_FILTERS, '')).toBe(false);
    expect(hasActiveAuditFilters({ ...DEFAULT_AUDIT_FILTERS, severity: 'critical' }, '')).toBe(true);
    expect(hasActiveAuditFilters({ ...DEFAULT_AUDIT_FILTERS, module: 'Security' }, '')).toBe(true);
    expect(auditFiltersToExportParams({ ...DEFAULT_AUDIT_FILTERS, operation: 'CREATE' }, '').audit_action).toBe(
      'CREATE',
    );
  });
});
