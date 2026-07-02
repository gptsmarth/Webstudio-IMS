import 'package:equatable/equatable.dart';

enum CatalogueTab { brands, locations }

enum BrandSortField { name, displayOrder, models, available }

enum LocationSortField { name, locationType, stock, capacity }

List<T> paginateItems<T>(List<T> items, int page, int pageSize) {
  final start = (page - 1) * pageSize;
  if (start >= items.length) return [];
  final end = (start + pageSize).clamp(0, items.length);
  return items.sublist(start, end);
}

bool matchesCatalogueSearch(String search, List<String?> values) {
  final term = search.trim().toLowerCase();
  if (term.isEmpty) return true;
  return values.any((value) => value?.toLowerCase().contains(term) ?? false);
}

String locationTypeLabel(String type) => switch (type) {
      'retail_floor' => 'Retail floor',
      'warehouse' => 'Warehouse',
      'other' => 'Other',
      _ => type,
    };

class CatalogueBrand extends Equatable {
  const CatalogueBrand({
    required this.id,
    required this.name,
    this.shortName,
    this.logoFilename,
    required this.displayOrder,
    required this.isActive,
  });

  final int id;
  final String name;
  final String? shortName;
  final String? logoFilename;
  final int displayOrder;
  final bool isActive;

  factory CatalogueBrand.fromJson(Map<String, dynamic> json) => CatalogueBrand(
        id: json['id'] as int,
        name: json['name'] as String,
        shortName: json['short_name'] as String?,
        logoFilename: json['logo_filename'] as String?,
        displayOrder: json['display_order'] as int? ?? 0,
        isActive: json['is_active'] as bool? ?? true,
      );

  Map<String, dynamic> toCreateJson(String name) => {
        'name': name,
        'display_order': displayOrder,
        'is_active': true,
      };

  @override
  List<Object?> get props => [id, name];
}

class CatalogueLocation extends Equatable {
  const CatalogueLocation({
    required this.id,
    required this.name,
    required this.locationType,
    required this.isActive,
    this.sortOrder,
    this.branchId,
  });

  final int id;
  final String name;
  final String locationType;
  final bool isActive;
  final int? sortOrder;
  final int? branchId;

  factory CatalogueLocation.fromJson(Map<String, dynamic> json) => CatalogueLocation(
        id: json['id'] as int,
        name: json['name'] as String,
        locationType: json['location_type'] as String,
        isActive: json['is_active'] as bool? ?? true,
        sortOrder: json['sort_order'] as int?,
        branchId: json['branch_id'] as int?,
      );

  @override
  List<Object?> get props => [id, name];
}

class CreateBrandRequest {
  const CreateBrandRequest({required this.name, this.displayOrder = 0});

  final String name;
  final int displayOrder;

  Map<String, dynamic> toJson() => {'name': name, 'display_order': displayOrder, 'is_active': true};
}

class CreateLocationRequest {
  const CreateLocationRequest({
    required this.name,
    required this.locationType,
    this.sortOrder = 0,
  });

  final String name;
  final String locationType;
  final int sortOrder;

  Map<String, dynamic> toJson() => {
        'name': name,
        'location_type': locationType,
        'sort_order': sortOrder,
        'is_active': true,
      };
}

class LocationDeletePreview {
  const LocationDeletePreview({
    required this.inventoryCount,
    required this.movableInventoryCount,
    required this.requiresTransfer,
  });

  final int inventoryCount;
  final int movableInventoryCount;
  final bool requiresTransfer;

  factory LocationDeletePreview.fromJson(Map<String, dynamic> json) => LocationDeletePreview(
        inventoryCount: json['inventory_count'] as int? ?? 0,
        movableInventoryCount: json['movable_inventory_count'] as int? ?? 0,
        requiresTransfer: json['requires_transfer'] as bool? ?? false,
      );
}

bool canWriteCatalogue(List<String> permissions) {
  const keys = [
    'brands:create',
    'brands:edit',
    'brands:delete',
    'brands:archive',
    'locations:create',
    'locations:edit',
    'locations:delete',
    'locations:archive',
  ];
  return keys.any(permissions.contains);
}

bool canCreateInventory(List<String> permissions) {
  return permissions.contains('inventory:create');
}

bool canViewSales(List<String> permissions) => permissions.contains('sales:view');

bool canViewInventory(List<String> permissions) => permissions.contains('inventory:view');
