import 'package:equatable/equatable.dart';

class TallySyncCheckpoint extends Equatable {
  const TallySyncCheckpoint({
    this.lastImportedVoucherDate,
    this.lastProcessedGuid,
    this.lastProcessedMasterId,
    this.lastProcessedVoucherType,
    this.lastProcessedInvoiceNumber,
    this.lastSuccessfulSyncAt,
    required this.schedulerStatus,
    required this.schedulerStatusLabel,
  });

  final String? lastImportedVoucherDate;
  final String? lastProcessedGuid;
  final String? lastProcessedMasterId;
  final String? lastProcessedVoucherType;
  final String? lastProcessedInvoiceNumber;
  final String? lastSuccessfulSyncAt;
  final String schedulerStatus;
  final String schedulerStatusLabel;

  factory TallySyncCheckpoint.fromJson(Map<String, dynamic> json) {
    return TallySyncCheckpoint(
      lastImportedVoucherDate: json['last_imported_voucher_date'] as String?,
      lastProcessedGuid: json['last_processed_guid'] as String?,
      lastProcessedMasterId: json['last_processed_master_id'] as String?,
      lastProcessedVoucherType: json['last_processed_voucher_type'] as String?,
      lastProcessedInvoiceNumber: json['last_processed_invoice_number'] as String?,
      lastSuccessfulSyncAt: json['last_successful_sync_at'] as String?,
      schedulerStatus: json['scheduler_status'] as String? ?? 'disabled',
      schedulerStatusLabel: json['scheduler_status_label'] as String? ?? '—',
    );
  }

  @override
  List<Object?> get props => [lastProcessedGuid, lastImportedVoucherDate, schedulerStatus];
}

class TallyOperationalSummary extends Equatable {
  const TallyOperationalSummary({
    required this.connectionLabel,
    required this.isConnected,
    required this.autoSyncEnabled,
    required this.pollingIntervalSeconds,
    required this.pollingIntervalLabel,
    this.lastSuccessfulSyncAt,
    this.lastInvoiceImported,
    this.lastInvoiceDate,
    this.nextScheduledSyncAt,
    this.lastSyncDurationMs,
    required this.lastSyncDurationLabel,
    required this.importedToday,
    required this.importedThisWeek,
    required this.importedThisMonth,
    required this.totalImported,
    required this.schedulerStatus,
    required this.schedulerStatusLabel,
    this.retryCountdownSeconds,
    this.retryCountdownLabel,
    required this.syncHealth,
    required this.pendingRetry,
    required this.todaysImports,
    this.syncCheckpoint,
  });

  final String connectionLabel;
  final bool isConnected;
  final bool autoSyncEnabled;
  final int pollingIntervalSeconds;
  final String pollingIntervalLabel;
  final String? lastSuccessfulSyncAt;
  final String? lastInvoiceImported;
  final String? lastInvoiceDate;
  final String? nextScheduledSyncAt;
  final int? lastSyncDurationMs;
  final String lastSyncDurationLabel;
  final int importedToday;
  final int importedThisWeek;
  final int importedThisMonth;
  final int totalImported;
  final String schedulerStatus;
  final String schedulerStatusLabel;
  final int? retryCountdownSeconds;
  final String? retryCountdownLabel;
  final String syncHealth;
  final bool pendingRetry;
  final int todaysImports;
  final TallySyncCheckpoint? syncCheckpoint;

  factory TallyOperationalSummary.fromJson(Map<String, dynamic> json) {
    final checkpointJson = json['sync_checkpoint'];
    return TallyOperationalSummary(
      connectionLabel: json['connection_label'] as String? ?? 'Disconnected',
      isConnected: json['is_connected'] as bool? ?? false,
      autoSyncEnabled: json['auto_sync_enabled'] as bool? ?? false,
      pollingIntervalSeconds: json['polling_interval_seconds'] as int? ?? 300,
      pollingIntervalLabel: json['polling_interval_label'] as String? ?? '5 minutes',
      lastSuccessfulSyncAt: json['last_successful_sync_at'] as String?,
      lastInvoiceImported: json['last_invoice_imported'] as String?,
      lastInvoiceDate: json['last_invoice_date'] as String?,
      nextScheduledSyncAt: json['next_scheduled_sync_at'] as String?,
      lastSyncDurationMs: json['last_sync_duration_ms'] as int?,
      lastSyncDurationLabel: json['last_sync_duration_label'] as String? ?? '—',
      importedToday: json['imported_today'] as int? ?? 0,
      importedThisWeek: json['imported_this_week'] as int? ?? 0,
      importedThisMonth: json['imported_this_month'] as int? ?? 0,
      totalImported: json['total_imported'] as int? ?? 0,
      schedulerStatus: json['scheduler_status'] as String? ?? 'disabled',
      schedulerStatusLabel: json['scheduler_status_label'] as String? ?? 'Auto sync disabled',
      retryCountdownSeconds: json['retry_countdown_seconds'] as int?,
      retryCountdownLabel: json['retry_countdown_label'] as String?,
      syncHealth: json['sync_health'] as String? ?? 'offline',
      pendingRetry: json['pending_retry'] as bool? ?? false,
      todaysImports: json['todays_imports'] as int? ?? 0,
      syncCheckpoint: checkpointJson is Map<String, dynamic>
          ? TallySyncCheckpoint.fromJson(checkpointJson)
          : null,
    );
  }

  @override
  List<Object?> get props => [connectionLabel, isConnected, syncHealth, todaysImports];
}

class TallySyncHistoryEntry extends Equatable {
  const TallySyncHistoryEntry({
    required this.syncDate,
    required this.startTime,
    this.endTime,
    required this.startedAt,
    this.completedAt,
    this.durationMs,
    required this.durationLabel,
    required this.invoicesChecked,
    required this.invoicesImported,
    required this.invoicesSkipped,
    required this.errorsCount,
    this.errorSummary,
    required this.status,
    required this.statusLabel,
  });

  final String syncDate;
  final String startTime;
  final String? endTime;
  final String startedAt;
  final String? completedAt;
  final int? durationMs;
  final String durationLabel;
  final int invoicesChecked;
  final int invoicesImported;
  final int invoicesSkipped;
  final int errorsCount;
  final String? errorSummary;
  final String status;
  final String statusLabel;

  factory TallySyncHistoryEntry.fromJson(Map<String, dynamic> json) {
    return TallySyncHistoryEntry(
      syncDate: json['sync_date'] as String? ?? '',
      startTime: json['start_time'] as String? ?? '',
      endTime: json['end_time'] as String?,
      startedAt: json['started_at'] as String? ?? '',
      completedAt: json['completed_at'] as String?,
      durationMs: json['duration_ms'] as int?,
      durationLabel: json['duration_label'] as String? ?? '—',
      invoicesChecked: json['invoices_checked'] as int? ?? 0,
      invoicesImported: json['invoices_imported'] as int? ?? 0,
      invoicesSkipped: json['invoices_skipped'] as int? ?? 0,
      errorsCount: json['errors_count'] as int? ?? 0,
      errorSummary: json['error_summary'] as String?,
      status: json['status'] as String? ?? '',
      statusLabel: json['status_label'] as String? ?? '',
    );
  }

  @override
  List<Object?> get props => [startedAt, status];
}

class TallyDashboardData extends Equatable {
  const TallyDashboardData({
    required this.operational,
    required this.recentSynchronizations,
    this.lastError,
  });

  final TallyOperationalSummary operational;
  final List<TallySyncHistoryEntry> recentSynchronizations;
  final String? lastError;

  factory TallyDashboardData.fromJson(Map<String, dynamic> json) {
    final operationalRaw = json['operational'];
    final recentRaw = json['recent_synchronizations'];
    return TallyDashboardData(
      operational: operationalRaw is Map<String, dynamic>
          ? TallyOperationalSummary.fromJson(operationalRaw)
          : const TallyOperationalSummary(
              connectionLabel: 'Disconnected',
              isConnected: false,
              autoSyncEnabled: false,
              pollingIntervalSeconds: 300,
              pollingIntervalLabel: '5 minutes',
              lastSyncDurationLabel: '—',
              importedToday: 0,
              importedThisWeek: 0,
              importedThisMonth: 0,
              totalImported: 0,
              schedulerStatus: 'disabled',
              schedulerStatusLabel: 'Auto sync disabled',
              syncHealth: 'offline',
              pendingRetry: false,
              todaysImports: 0,
            ),
      recentSynchronizations: recentRaw is List
          ? recentRaw
              .whereType<Map<String, dynamic>>()
              .map(TallySyncHistoryEntry.fromJson)
              .toList()
          : const [],
      lastError: json['last_error'] as String?,
    );
  }

  @override
  List<Object?> get props => [operational, recentSynchronizations.length];
}

String tallyHealthLabel(String health) {
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
