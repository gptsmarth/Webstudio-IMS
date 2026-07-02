/** Business-facing Tally display helpers — no technical identifiers. */

export interface TallyOperationalSummary {
  connection_label: string;
  is_connected: boolean;
  auto_sync_enabled: boolean;
  polling_interval_seconds: number;
  polling_interval_label: string;
  last_successful_sync_at: string | null;
  last_invoice_imported: string | null;
  last_invoice_date: string | null;
  next_scheduled_sync_at: string | null;
  last_sync_duration_ms: number | null;
  last_sync_duration_label: string;
  imported_today: number;
  imported_this_week: number;
  imported_this_month: number;
  total_imported: number;
  scheduler_status: string;
  scheduler_status_label: string;
  retry_countdown_seconds: number | null;
  retry_countdown_label: string | null;
  sync_health: 'healthy' | 'degraded' | 'offline';
  pending_retry: boolean;
  todays_imports: number;
}

export interface TallySyncHistoryEntry {
  sync_date: string;
  start_time: string;
  end_time: string | null;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  duration_label: string;
  invoices_checked: number;
  invoices_imported: number;
  invoices_skipped: number;
  errors_count: number;
  error_summary: string | null;
  status: string;
  status_label: string;
}

export function tallyHealthLabel(health: string): string {
  switch (health) {
    case 'healthy':
      return 'Healthy';
    case 'degraded':
      return 'Needs attention';
    case 'offline':
      return 'Offline';
    default:
      return health;
  }
}

export function tallyStatusBadgeClass(status: string): string {
  switch (status) {
    case 'success':
      return 'tally-badge tally-badge--success';
    case 'partial':
      return 'tally-badge tally-badge--warning';
    case 'failed':
      return 'tally-badge tally-badge--danger';
    case 'offline':
      return 'tally-badge tally-badge--muted';
    case 'running':
      return 'tally-badge tally-badge--info';
    default:
      return 'tally-badge';
  }
}

export function formatPollingInterval(seconds: number): string {
  if (seconds % 3600 === 0) {
    const hours = seconds / 3600;
    return `${hours} hour${hours === 1 ? '' : 's'}`;
  }
  if (seconds % 60 === 0) {
    const minutes = seconds / 60;
    return `${minutes} minute${minutes === 1 ? '' : 's'}`;
  }
  return `${seconds} seconds`;
}
