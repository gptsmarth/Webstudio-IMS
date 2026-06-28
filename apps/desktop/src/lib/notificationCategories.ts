import type { NotificationDetail, NotificationSeverity } from '../services/api/NotificationService';

export type NotificationCategoryLabel = 'Information' | 'Warning' | 'Critical';

export function notificationCategoryLabel(severity: NotificationSeverity): NotificationCategoryLabel {
  if (severity === 'error') return 'Critical';
  if (severity === 'warning') return 'Warning';
  return 'Information';
}

export function notificationCategoryBadgeClass(severity: NotificationSeverity): string {
  if (severity === 'error') return 'badge-danger';
  if (severity === 'warning') return 'badge-warning';
  return 'badge-neutral';
}

export function notificationTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    duplicate_sale: 'Duplicate serial',
    serial_number_missing: 'Missing serial',
    product_model_missing: 'Missing product model',
    product_model_mismatch: 'Tally model mismatch',
    tally_sync_completed: 'Tally sync completed',
    sync_failure: 'Tally sync skipped',
    inventory_alert: 'Inventory alert',
    system_notification: 'System notification',
  };
  return labels[type] ?? type.replaceAll('_', ' ');
}

export function matchesNotificationSearch(item: NotificationDetail, query: string): boolean {
  const term = query.trim().toLowerCase();
  if (!term) return true;
  return [
    item.title,
    item.description,
    item.notification_type,
    item.serial_number ?? '',
    item.category,
  ].some((field) => field.toLowerCase().includes(term));
}

export { parseNotificationDescription } from './structuredData';
