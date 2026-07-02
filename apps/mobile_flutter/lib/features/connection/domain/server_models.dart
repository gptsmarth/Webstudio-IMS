import 'package:equatable/equatable.dart';

enum ConnectionStageId {
  hostResolution,
  reachability,
  httpConnection,
  backendHealth,
  apiCompatibility,
  authenticationEndpoint,
}

class ConnectionStageResult extends Equatable {
  const ConnectionStageResult({
    required this.stage,
    required this.label,
    required this.success,
    required this.message,
  });

  final ConnectionStageId stage;
  final String label;
  final bool success;
  final String message;

  @override
  List<Object?> get props => [stage, success, message];
}

class SavedServer extends Equatable {
  const SavedServer({
    required this.url,
    this.label,
    this.friendlyName,
    this.companyName,
    this.hostname,
    this.currentIp,
    this.backendVersion,
    this.lastConnectedAt,
    this.lastSeenAt,
  });

  final String url;
  final String? label;
  final String? friendlyName;
  final String? companyName;
  final String? hostname;
  final String? currentIp;
  final String? backendVersion;
  final DateTime? lastConnectedAt;
  final DateTime? lastSeenAt;

  String get displayLabel {
    final name = friendlyName?.trim().isNotEmpty == true
        ? friendlyName!
        : label?.trim().isNotEmpty == true
            ? label!
            : companyName?.trim().isNotEmpty == true
                ? companyName!
                : url;
    return name;
  }

  factory SavedServer.fromJson(Map<String, dynamic> json) {
    return SavedServer(
      url: json['url'] as String,
      label: json['label'] as String?,
      friendlyName: json['friendly_name'] as String?,
      companyName: json['company_name'] as String?,
      hostname: json['hostname'] as String?,
      currentIp: json['current_ip'] as String?,
      backendVersion: json['backend_version'] as String?,
      lastConnectedAt: json['last_connected_at'] != null
          ? DateTime.tryParse(json['last_connected_at'] as String)
          : null,
      lastSeenAt: json['last_seen_at'] != null
          ? DateTime.tryParse(json['last_seen_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'url': url,
        if (label != null) 'label': label,
        if (friendlyName != null) 'friendly_name': friendlyName,
        if (companyName != null) 'company_name': companyName,
        if (hostname != null) 'hostname': hostname,
        if (currentIp != null) 'current_ip': currentIp,
        if (backendVersion != null) 'backend_version': backendVersion,
        if (lastConnectedAt != null) 'last_connected_at': lastConnectedAt!.toIso8601String(),
        if (lastSeenAt != null) 'last_seen_at': lastSeenAt!.toIso8601String(),
      };

  SavedServer copyWith({
    String? url,
    String? label,
    String? friendlyName,
    String? companyName,
    String? hostname,
    String? currentIp,
    String? backendVersion,
    DateTime? lastConnectedAt,
    DateTime? lastSeenAt,
  }) {
    return SavedServer(
      url: url ?? this.url,
      label: label ?? this.label,
      friendlyName: friendlyName ?? this.friendlyName,
      companyName: companyName ?? this.companyName,
      hostname: hostname ?? this.hostname,
      currentIp: currentIp ?? this.currentIp,
      backendVersion: backendVersion ?? this.backendVersion,
      lastConnectedAt: lastConnectedAt ?? this.lastConnectedAt,
      lastSeenAt: lastSeenAt ?? this.lastSeenAt,
    );
  }

  @override
  List<Object?> get props => [
        url,
        label,
        friendlyName,
        companyName,
        hostname,
        currentIp,
        backendVersion,
        lastConnectedAt,
        lastSeenAt,
      ];
}

class DiscoveredServer extends Equatable {
  const DiscoveredServer({
    required this.id,
    required this.serverName,
    required this.companyName,
    required this.backendVersion,
    required this.apiVersion,
    required this.buildVersion,
    required this.environment,
    required this.port,
    required this.host,
    required this.url,
    required this.lastSeen,
    required this.status,
  });

  final String id;
  final String serverName;
  final String companyName;
  final String backendVersion;
  final String apiVersion;
  final String buildVersion;
  final String environment;
  final int port;
  final String host;
  final String url;
  final DateTime lastSeen;
  final String status;

  @override
  List<Object?> get props => [id, url, lastSeen];
}

class ConnectionTestResult extends Equatable {
  const ConnectionTestResult({
    required this.success,
    required this.url,
    this.latencyMs,
    this.backendVersion,
    this.companyName,
    this.errorMessage,
    this.stages = const [],
    this.failedStage,
  });

  final bool success;
  final String url;
  final int? latencyMs;
  final String? backendVersion;
  final String? companyName;
  final String? errorMessage;
  final List<ConnectionStageResult> stages;
  final ConnectionStageId? failedStage;

  @override
  List<Object?> get props => [
        success,
        url,
        latencyMs,
        backendVersion,
        companyName,
        errorMessage,
        stages,
        failedStage,
      ];
}

class SetupStatus extends Equatable {
  const SetupStatus({
    required this.systemInitialized,
    this.companyName,
  });

  final bool systemInitialized;
  final String? companyName;

  factory SetupStatus.fromJson(Map<String, dynamic> json) {
    return SetupStatus(
      systemInitialized: json['system_initialized'] as bool? ?? false,
      companyName: json['company_name'] as String?,
    );
  }

  @override
  List<Object?> get props => [systemInitialized, companyName];
}
