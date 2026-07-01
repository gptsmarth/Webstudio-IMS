import 'package:equatable/equatable.dart';

class AuditLogEntry extends Equatable {
  const AuditLogEntry({
    required this.id,
    required this.operation,
    required this.module,
    required this.description,
    required this.createdAt,
    this.actorDisplayName,
    this.severity,
  });

  final String id;
  final String operation;
  final String module;
  final String description;
  final String createdAt;
  final String? actorDisplayName;
  final String? severity;

  factory AuditLogEntry.fromJson(Map<String, dynamic> json) => AuditLogEntry(
        id: json['id']?.toString() ?? '',
        operation: json['operation'] as String? ?? json['action']?.toString() ?? '',
        module: json['module'] as String? ?? json['entity_type'] as String? ?? '',
        description: json['description'] as String? ?? json['summary'] as String? ?? '',
        createdAt: json['created_at']?.toString() ?? '',
        actorDisplayName: json['actor_display_name'] as String?,
        severity: json['severity'] as String?,
      );

  @override
  List<Object?> get props => [id];
}
