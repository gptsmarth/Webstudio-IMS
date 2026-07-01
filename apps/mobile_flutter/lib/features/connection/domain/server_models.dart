import 'package:equatable/equatable.dart';

class SavedServer extends Equatable {
  const SavedServer({
    required this.url,
    this.label,
    this.lastConnectedAt,
  });

  final String url;
  final String? label;
  final DateTime? lastConnectedAt;

  String get displayLabel => label?.trim().isNotEmpty == true ? label! : url;

  factory SavedServer.fromJson(Map<String, dynamic> json) {
    return SavedServer(
      url: json['url'] as String,
      label: json['label'] as String?,
      lastConnectedAt: json['last_connected_at'] != null
          ? DateTime.tryParse(json['last_connected_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'url': url,
        if (label != null) 'label': label,
        if (lastConnectedAt != null) 'last_connected_at': lastConnectedAt!.toIso8601String(),
      };

  SavedServer copyWith({
    String? url,
    String? label,
    DateTime? lastConnectedAt,
  }) {
    return SavedServer(
      url: url ?? this.url,
      label: label ?? this.label,
      lastConnectedAt: lastConnectedAt ?? this.lastConnectedAt,
    );
  }

  @override
  List<Object?> get props => [url, label, lastConnectedAt];
}

class ConnectionTestResult extends Equatable {
  const ConnectionTestResult({
    required this.success,
    required this.url,
    this.latencyMs,
    this.backendVersion,
    this.companyName,
    this.errorMessage,
  });

  final bool success;
  final String url;
  final int? latencyMs;
  final String? backendVersion;
  final String? companyName;
  final String? errorMessage;

  @override
  List<Object?> get props => [success, url, latencyMs, backendVersion, companyName, errorMessage];
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
