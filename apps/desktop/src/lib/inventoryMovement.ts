import type { AuditLogEntry } from '../services/api/AuditService';
import { formatDateTime } from './datetime';

export interface MovementRecord {
  id: string;
  fromLocation: string;
  toLocation: string;
  movedAt: string;
  actor: string;
  description: string | null;
}

function locationFromValue(value: Record<string, unknown> | null, key: string): string | null {
  if (!value) return null;
  const nested = value[key];
  if (typeof nested === 'string') return nested;
  if (nested && typeof nested === 'object' && 'name' in nested && typeof nested.name === 'string') {
    return nested.name;
  }
  return null;
}

function parseMovement(log: AuditLogEntry): MovementRecord {
  const fromLocation =
    locationFromValue(log.old_value, 'current_location_name')
    ?? locationFromValue(log.old_value, 'location_name')
    ?? 'Unknown';
  const toLocation =
    locationFromValue(log.new_value, 'current_location_name')
    ?? locationFromValue(log.new_value, 'location_name')
    ?? extractToFromDescription(log.description)
    ?? 'Unknown';

  return {
    id: log.id,
    fromLocation,
    toLocation,
    movedAt: log.created_at,
    actor: log.actor_display_name ?? 'System',
    description: log.description,
  };
}

function extractToFromDescription(description: string | null): string | null {
  if (!description) return null;
  const match = description.match(/\bto\s+(.+?)(?:\.|$)/i);
  return match?.[1]?.trim() ?? null;
}

export function extractMovementHistory(auditLogs: AuditLogEntry[]): MovementRecord[] {
  return auditLogs
    .filter((log) => log.action === 'LOCATION_CHANGE')
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    .map(parseMovement);
}

export function formatMovementChain(movements: MovementRecord[]): string {
  if (movements.length === 0) return '';
  const points = [movements[0].fromLocation];
  for (const move of movements) points.push(move.toLocation);
  return points.join(' → ');
}

export function formatMovementTimestamp(value: string): string {
  return formatDateTime(value);
}
