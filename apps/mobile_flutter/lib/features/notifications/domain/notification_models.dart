import 'package:equatable/equatable.dart';

enum NotificationSeverity { error, warning, info }

NotificationSeverity notificationSeverityFromString(String value) {
  return NotificationSeverity.values.firstWhere(
    (s) => s.name == value,
    orElse: () => NotificationSeverity.info,
  );
}

class NotificationItem extends Equatable {
  const NotificationItem({
    required this.id,
    required this.notificationType,
    required this.title,
    required this.description,
    required this.category,
    required this.severity,
    required this.status,
    required this.isRead,
    required this.isResolved,
    this.serialNumber,
    required this.createdAt,
  });

  final int id;
  final String notificationType;
  final String title;
  final String description;
  final String category;
  final NotificationSeverity severity;
  final String status;
  final bool isRead;
  final bool isResolved;
  final String? serialNumber;
  final String createdAt;

  factory NotificationItem.fromJson(Map<String, dynamic> json) => NotificationItem(
        id: json['id'] as int,
        notificationType: json['notification_type'] as String,
        title: json['title'] as String,
        description: json['description'] as String,
        category: json['category'] as String,
        severity: notificationSeverityFromString(json['severity'] as String? ?? 'info'),
        status: json['status'] as String,
        isRead: json['is_read'] as bool? ?? false,
        isResolved: json['is_resolved'] as bool? ?? false,
        serialNumber: json['serial_number'] as String?,
        createdAt: json['created_at'] as String,
      );

  @override
  List<Object?> get props => [id, isRead, isResolved];
}
