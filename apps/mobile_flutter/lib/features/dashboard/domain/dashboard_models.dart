import 'package:equatable/equatable.dart';

import '../../../core/network/json_map.dart';

class DistributionGroup extends Equatable {
  const DistributionGroup({
    required this.id,
    required this.name,
    required this.available,
    required this.sold,
    required this.total,
  });

  final String id;
  final String name;
  final int available;
  final int sold;
  final int total;

  factory DistributionGroup.fromJson(Map<String, dynamic> json) => DistributionGroup(
        id: json['id'].toString(),
        name: json['name'] as String,
        available: json['available'] as int? ?? 0,
        sold: json['sold'] as int? ?? 0,
        total: json['total'] as int? ?? 0,
      );

  @override
  List<Object?> get props => [id, name, available, sold, total];
}

class DashboardDistribution extends Equatable {
  const DashboardDistribution({
    required this.totalAvailableInventory,
    required this.byBrand,
    required this.byLocation,
    required this.byProductModel,
    required this.asOf,
  });

  final int totalAvailableInventory;
  final List<DistributionGroup> byBrand;
  final List<DistributionGroup> byLocation;
  final List<DistributionGroup> byProductModel;
  final String asOf;

  factory DashboardDistribution.fromJson(Map<String, dynamic> json) {
    List<DistributionGroup> parseList(dynamic raw) {
      return asJsonMapList(raw).map(DistributionGroup.fromJson).toList();
    }

    return DashboardDistribution(
      totalAvailableInventory: json['total_available_inventory'] as int? ?? 0,
      byBrand: parseList(json['by_brand']),
      byLocation: parseList(json['by_location']),
      byProductModel: parseList(json['by_product_model']),
      asOf: json['as_of'] as String? ?? '',
    );
  }

  @override
  List<Object?> get props => [totalAvailableInventory, byBrand, byLocation, asOf];
}

class RecentActivityEntry extends Equatable {
  const RecentActivityEntry({
    required this.id,
    required this.activityType,
    required this.description,
    this.actorDisplayName,
    required this.createdAt,
  });

  final String id;
  final String activityType;
  final String? description;
  final String? actorDisplayName;
  final String createdAt;

  factory RecentActivityEntry.fromJson(Map<String, dynamic> json) => RecentActivityEntry(
        id: json['id'].toString(),
        activityType: json['activity_type'] as String? ?? '',
        description: json['description'] as String?,
        actorDisplayName: json['actor_display_name'] as String?,
        createdAt: json['created_at'] as String? ?? '',
      );

  @override
  List<Object?> get props => [id, activityType, createdAt];
}

class OperationsDashboard extends Equatable {
  const OperationsDashboard({required this.totalAvailableInventory, required this.asOf});

  final int totalAvailableInventory;
  final String asOf;

  factory OperationsDashboard.fromJson(Map<String, dynamic> json) => OperationsDashboard(
        totalAvailableInventory: json['total_available_inventory'] as int? ?? 0,
        asOf: json['as_of'] as String? ?? '',
      );

  @override
  List<Object?> get props => [totalAvailableInventory, asOf];
}
