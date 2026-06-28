export const ACTIVITY_LABELS: Record<string, string> = {
  inventory_created: 'Inventory added',
  manual_sale: 'Marked sold',
  location_transfer: 'Location transfer',
  user_created: 'User created',
  status_change: 'Status changed',
  inventory_archived: 'Inventory archived',
  inventory_restored: 'Inventory restored',
  create: 'Created',
  update: 'Updated',
  delete: 'Deleted',
};

export function formatActivityType(activityType: string): string {
  return ACTIVITY_LABELS[activityType] ?? activityType.replaceAll('_', ' ');
}

export function extractActivityLocation(description: string | null): string {
  if (!description) return '—';
  const toMatch = description.match(/\bto\s+(.+?)(?:\.|$)/i);
  if (toMatch?.[1]) return toMatch[1].trim();
  const atMatch = description.match(/\bat\s+(.+?)(?:\.|$)/i);
  if (atMatch?.[1]) return atMatch[1].trim();
  return '—';
}

export function locationSharePercent(available: number, totalAvailable: number): number {
  if (totalAvailable <= 0) return 0;
  return Math.round((available / totalAvailable) * 100);
}
