import 'package:equatable/equatable.dart';

import '../../tally/domain/tally_models.dart';

class AIProviderHealth extends Equatable {
  const AIProviderHealth({
    required this.provider,
    required this.configured,
    required this.status,
    this.lastError,
    this.lastSuccessAt,
  });

  final String provider;
  final bool configured;
  final String status;
  final String? lastError;
  final String? lastSuccessAt;

  factory AIProviderHealth.fromJson(Map<String, dynamic> json) => AIProviderHealth(
        provider: json['provider'] as String,
        configured: json['configured'] as bool? ?? false,
        status: json['status'] as String? ?? 'not_configured',
        lastError: json['last_error'] as String?,
        lastSuccessAt: json['last_success_at'] as String?,
      );

  @override
  List<Object?> get props => [provider, status];
}

class BackupSettingsSummary extends Equatable {
  const BackupSettingsSummary({
    required this.healthStatus,
    this.lastBackupAt,
    this.nextScheduledBackupAt,
    required this.backupFolder,
    required this.retentionPolicy,
    required this.databaseSizeBytes,
  });

  final String healthStatus;
  final String? lastBackupAt;
  final String? nextScheduledBackupAt;
  final String backupFolder;
  final String retentionPolicy;
  final int databaseSizeBytes;

  factory BackupSettingsSummary.fromJson(Map<String, dynamic> json) => BackupSettingsSummary(
        healthStatus: json['health_status'] as String? ?? 'unknown',
        lastBackupAt: json['last_backup_at'] as String?,
        nextScheduledBackupAt: json['next_scheduled_backup_at'] as String?,
        backupFolder: json['backup_folder'] as String? ?? '—',
        retentionPolicy: json['retention_policy'] as String? ?? '—',
        databaseSizeBytes: json['database_size_bytes'] as int? ?? 0,
      );

  @override
  List<Object?> get props => [healthStatus, lastBackupAt];
}

class TallySettingsSummary extends Equatable {
  const TallySettingsSummary({
    required this.connectionStatus,
    required this.enabled,
    required this.tallyHost,
    required this.tallyPort,
    this.tallyCompanyName,
    this.lastSyncAt,
    this.nextSyncAt,
  });

  final String connectionStatus;
  final bool enabled;
  final String tallyHost;
  final String tallyPort;
  final String? tallyCompanyName;
  final String? lastSyncAt;
  final String? nextSyncAt;

  factory TallySettingsSummary.fromJson(Map<String, dynamic> json) => TallySettingsSummary(
        connectionStatus: json['connection_status'] as String? ?? 'disconnected',
        enabled: json['enabled'] as bool? ?? false,
        tallyHost: json['tally_host'] as String? ?? '—',
        tallyPort: json['tally_port'] as String? ?? '—',
        tallyCompanyName: json['tally_company_name'] as String?,
        lastSyncAt: json['last_sync_at'] as String?,
        nextSyncAt: json['next_sync_at'] as String?,
      );

  @override
  List<Object?> get props => [connectionStatus, enabled];
}

class IntegrationsSummary extends Equatable {
  const IntegrationsSummary({
    required this.geminiConfigured,
    required this.aiEnrichmentEnabled,
    required this.geminiModel,
    required this.aiProviderHealth,
  });

  final bool geminiConfigured;
  final bool aiEnrichmentEnabled;
  final String geminiModel;
  final List<AIProviderHealth> aiProviderHealth;

  factory IntegrationsSummary.fromJson(Map<String, dynamic> json) => IntegrationsSummary(
        geminiConfigured: json['gemini_configured'] as bool? ?? false,
        aiEnrichmentEnabled: json['ai_enrichment_enabled'] as bool? ?? false,
        geminiModel: json['gemini_model'] as String? ?? '—',
        aiProviderHealth: (json['ai_provider_health'] as List<dynamic>?)
                ?.whereType<Map<String, dynamic>>()
                .map(AIProviderHealth.fromJson)
                .toList() ??
            const [],
      );

  @override
  List<Object?> get props => [geminiConfigured, aiEnrichmentEnabled];
}

class SettingsWorkspaceSummary extends Equatable {
  const SettingsWorkspaceSummary({
    required this.backup,
    required this.tally,
    required this.integrations,
    required this.systemVersion,
    required this.companyName,
  });

  final BackupSettingsSummary backup;
  final TallySettingsSummary tally;
  final IntegrationsSummary integrations;
  final String systemVersion;
  final String companyName;

  factory SettingsWorkspaceSummary.fromJson(Map<String, dynamic> json) => SettingsWorkspaceSummary(
        backup: BackupSettingsSummary.fromJson(json['backup'] as Map<String, dynamic>? ?? {}),
        tally: TallySettingsSummary.fromJson(json['tally'] as Map<String, dynamic>? ?? {}),
        integrations: IntegrationsSummary.fromJson(json['integrations'] as Map<String, dynamic>? ?? {}),
        systemVersion: (json['system'] as Map<String, dynamic>?)?['app_version'] as String? ?? '—',
        companyName: (json['general'] as Map<String, dynamic>?)?['company_name'] as String? ?? '—',
      );

  @override
  List<Object?> get props => [companyName, systemVersion];
}

class RecoveryCenterSummary extends Equatable {
  const RecoveryCenterSummary({
    required this.systemHealth,
    required this.databaseStatus,
    required this.backupStatus,
    required this.storageStatus,
    required this.recoveryReadiness,
    this.lastBackupAt,
    this.lastRestoreAt,
    required this.failedBackupCount,
    required this.healthIssues,
  });

  final String systemHealth;
  final String databaseStatus;
  final String backupStatus;
  final String storageStatus;
  final String recoveryReadiness;
  final String? lastBackupAt;
  final String? lastRestoreAt;
  final int failedBackupCount;
  final List<RecoveryHealthIssue> healthIssues;

  factory RecoveryCenterSummary.fromJson(Map<String, dynamic> json) => RecoveryCenterSummary(
        systemHealth: json['system_health'] as String? ?? 'unknown',
        databaseStatus: json['database_status'] as String? ?? 'unknown',
        backupStatus: json['backup_status'] as String? ?? 'unknown',
        storageStatus: json['storage_status'] as String? ?? 'unknown',
        recoveryReadiness: json['recovery_readiness'] as String? ?? 'unknown',
        lastBackupAt: json['last_backup_at'] as String?,
        lastRestoreAt: json['last_restore_at'] as String?,
        failedBackupCount: json['failed_backup_count'] as int? ?? 0,
        healthIssues: (json['health_issues'] as List<dynamic>?)
                ?.whereType<Map<String, dynamic>>()
                .map(RecoveryHealthIssue.fromJson)
                .toList() ??
            const [],
      );

  @override
  List<Object?> get props => [recoveryReadiness, failedBackupCount];
}

class RecoveryHealthIssue extends Equatable {
  const RecoveryHealthIssue({
    required this.code,
    required this.severity,
    required this.title,
    required this.message,
  });

  final String code;
  final String severity;
  final String title;
  final String message;

  factory RecoveryHealthIssue.fromJson(Map<String, dynamic> json) => RecoveryHealthIssue(
        code: json['code'] as String,
        severity: json['severity'] as String? ?? 'info',
        title: json['title'] as String? ?? '',
        message: json['message'] as String? ?? '',
      );

  @override
  List<Object?> get props => [code];
}

class BackupAdminDashboardSummary extends Equatable {
  const BackupAdminDashboardSummary({
    required this.storageHealth,
    required this.backupFolder,
    required this.failedBackupCount,
    required this.warningCount,
    required this.totalBackupCount,
    this.newestBackupAt,
  });

  final String storageHealth;
  final String backupFolder;
  final int failedBackupCount;
  final int warningCount;
  final int totalBackupCount;
  final String? newestBackupAt;

  factory BackupAdminDashboardSummary.fromJson(Map<String, dynamic> json) =>
      BackupAdminDashboardSummary(
        storageHealth: json['storage_health'] as String? ?? 'unknown',
        backupFolder: json['backup_folder'] as String? ?? '—',
        failedBackupCount: json['failed_backup_count'] as int? ?? 0,
        warningCount: json['warning_count'] as int? ?? 0,
        totalBackupCount: json['total_backup_count'] as int? ?? 0,
        newestBackupAt: json['newest_backup_at'] as String?,
      );

  @override
  List<Object?> get props => [storageHealth, totalBackupCount];
}

class TallyStatusSummary extends Equatable {
  const TallyStatusSummary({
    required this.available,
    required this.isConnected,
    required this.connectionLabel,
    required this.connectionStatus,
    this.lastSync,
    this.nextScheduledSync,
    required this.connectedCompanies,
    required this.pendingIssues,
    required this.connectionHealth,
    this.lastError,
    this.operational,
    required this.pendingRetry,
    required this.todaysImports,
  });

  final bool available;
  final bool isConnected;
  final String connectionLabel;
  final String connectionStatus;
  final String? lastSync;
  final String? nextScheduledSync;
  final int connectedCompanies;
  final int pendingIssues;
  final String connectionHealth;
  final String? lastError;
  final TallyOperationalSummary? operational;
  final bool pendingRetry;
  final int todaysImports;

  factory TallyStatusSummary.fromJson(Map<String, dynamic> json) {
    final operationalRaw = json['operational'];
    return TallyStatusSummary(
      available: json['available'] as bool? ?? json['is_healthy'] as bool? ?? false,
      isConnected: json['is_connected'] as bool? ?? false,
      connectionLabel: json['connection_label'] as String? ?? 'Disconnected',
      connectionStatus: json['connection_status'] as String? ?? 'unavailable',
      lastSync: json['last_sync'] as String?,
      nextScheduledSync: json['next_scheduled_sync'] as String?,
      connectedCompanies: json['connected_companies'] as int? ?? 0,
      pendingIssues: json['pending_issues'] as int? ?? 0,
      connectionHealth: json['connection_health'] as String? ?? 'offline',
      lastError: json['last_error'] as String?,
      operational: operationalRaw is Map<String, dynamic>
          ? TallyOperationalSummary.fromJson(operationalRaw)
          : null,
      pendingRetry: json['pending_retry'] as bool? ?? false,
      todaysImports: json['todays_imports'] as int? ?? 0,
    );
  }

  @override
  List<Object?> get props => [connectionStatus, connectionHealth, isConnected];
}

String formatBytes(int bytes) {
  if (bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  var value = bytes.toDouble();
  var unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return '${value.toStringAsFixed(value >= 10 ? 0 : 1)} ${units[unit]}';
}
