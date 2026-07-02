import type { AuditAction, AuditListEntry, AuditSource } from '../services/api/AuditService';
import { canReadAudit as canReadAuditPermission, canExportAudit as canExportAuditPermission } from '../services/PermissionService';
import { formatRoleLabel } from '../store/useAuthStore';

export type AuditViewMode = 'table' | 'timeline';

export function formatActorRole(role: string | null): string {
  if (!role) return '—';
  if (role === 'system') return 'System';
  if (role === 'main_admin' || role === 'admin' || role === 'salesperson') {
    return formatRoleLabel(role);
  }
  return role.replaceAll('_', ' ');
}

export const AUDIT_ACTIONS: AuditAction[] = [
  'CREATE',
  'UPDATE',
  'ARCHIVE',
  'RESTORE',
  'STATUS_CHANGE',
  'LOCATION_CHANGE',
  'SYSTEM_ACTION',
];

export const AUDIT_SOURCES: AuditSource[] = ['MANUAL', 'TALLY_SYNC', 'BACKGROUND_JOB', 'SYSTEM'];

export const AUDIT_MODULES = [
  'Inventory',
  'Sales',
  'Catalogue',
  'Users',
  'Security',
  'System',
  'Notifications',
  'Reports',
] as const;

export const AUDIT_SEVERITIES = ['low', 'medium', 'high', 'critical'] as const;
export type AuditSeverity = (typeof AUDIT_SEVERITIES)[number];

export const ENTITY_TYPE_BY_MODULE: Record<string, string> = {
  Inventory: 'inventory_item',
  Sales: 'sale',
  Catalogue: 'brand',
  Users: 'user',
  Security: 'permission',
  System: 'system',
  Notifications: 'notification',
  Reports: 'report',
};

export const SECURITY_ENTITY_TYPES = new Set([
  'user',
  'permission',
  'system_setting',
  'integration_api_key',
  'system',
]);

export function canReadAudit(permissions: string[]): boolean {
  return canReadAuditPermission(permissions);
}

export function canExportAudit(permissions: string[]): boolean {
  return canExportAuditPermission(permissions);
}

export function auditResultBadgeClass(result: string): string {
  return result === 'failure' ? 'aud-badge aud-badge--failure' : 'aud-badge aud-badge--success';
}

export function auditResultLabel(result: string): string {
  return result === 'failure' ? 'Failure' : 'Success';
}

export function auditSeverityBadgeClass(severity: string): string {
  if (severity === 'critical') return 'aud-badge aud-badge--critical';
  if (severity === 'high') return 'aud-badge aud-badge--high';
  if (severity === 'medium') return 'aud-badge aud-badge--medium';
  return 'aud-badge aud-badge--low';
}

export function auditSeverityLabel(severity: string): string {
  return severity.charAt(0).toUpperCase() + severity.slice(1);
}

export function formatAuditEntity(entry: AuditListEntry): string {
  if (entry.entity_type === 'inventory_item') return entry.serial_number ?? entry.entity_id.slice(0, 8);
  if (entry.entity_type === 'sale') return entry.invoice_number ?? `Sale #${entry.entity_id}`;
  if (entry.entity_type === 'product_model') return entry.model_number ?? entry.entity_id.slice(0, 8);
  return entry.entity_id;
}

export interface AuditTimelineStep {
  id: string;
  label: string;
  timestamp: string;
  description: string | null;
  entry: AuditListEntry;
}

export function buildAuditTimeline(entries: AuditListEntry[]): AuditTimelineStep[] {
  const sorted = [...entries].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
  return sorted.map((entry) => ({
    id: entry.id,
    label: timelineLabel(entry),
    timestamp: entry.created_at,
    description: entry.description,
    entry,
  }));
}

export function timelineLabel(entry: AuditListEntry): string {
  if (entry.source === 'TALLY_SYNC') return 'Tally synced';
  if (entry.action === 'CREATE' && entry.module === 'Inventory') return 'Laptop added';
  if (entry.action === 'LOCATION_CHANGE') return 'Transferred';
  if (entry.action === 'STATUS_CHANGE') {
    const status = entry.new_value?.status;
    if (status === 'sold') return 'Sold';
    return 'Status changed';
  }
  if (entry.module === 'Reports' || entry.description?.toLowerCase().includes('export')) {
    return 'Report exported';
  }
  if (entry.action === 'SYSTEM_ACTION' && entry.result === 'failure') return 'Operation failed';
  return entry.operation;
}

export function formatAuditValue(value: Record<string, unknown> | null): string {
  if (!value) return '—';
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
