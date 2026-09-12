import 'package:equatable/equatable.dart';

import 'product_category.dart';

enum InventoryStatus { received, available, reserved, sold }

InventoryStatus inventoryStatusFromString(String value) {
  return InventoryStatus.values.firstWhere(
    (status) => status.name == value,
    orElse: () => InventoryStatus.available,
  );
}

String inventoryStatusLabel(InventoryStatus status) {
  return switch (status) {
    InventoryStatus.received => 'Received',
    InventoryStatus.available => 'Available',
    InventoryStatus.reserved => 'Reserved',
    InventoryStatus.sold => 'Sold',
  };
}

class InventoryItem extends Equatable {
  const InventoryItem({
    required this.id,
    required this.serialNumber,
    required this.productModelId,
    required this.brandId,
    required this.brandName,
    this.category = ProductCategory.laptop,
    this.accessoryKind,
    this.partNumber,
    required this.modelNumber,
    required this.modelName,
    this.cpu = '',
    this.gpu,
    this.ramGb = 0,
    this.storageValue = '',
    this.storageUnit = 'GB',
    this.storageType = 'SSD',
    required this.color,
    required this.currentLocationId,
    required this.currentLocationName,
    required this.status,
    required this.isArchived,
    this.purchaseDate,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String serialNumber;
  final String productModelId;
  final int brandId;
  final String brandName;
  final ProductCategory category;
  final AccessoryKind? accessoryKind;
  final String? partNumber;
  final String modelNumber;
  final String modelName;
  final String cpu;
  final String? gpu;
  final int ramGb;
  final String storageValue;
  final String storageUnit;
  final String storageType;
  final String color;
  final int currentLocationId;
  final String currentLocationName;
  final InventoryStatus status;
  final bool isArchived;
  final String? purchaseDate;
  final String createdAt;
  final String updatedAt;

  bool get isAccessory => isAccessoryModel(category: category);
  bool get isLaptop => isLaptopModel(category: category);

  String get specsLabel {
    if (isAccessory) {
      final parts = <String>[accessoryKindLabel(accessoryKind)];
      final pn = partNumber?.trim();
      if (pn != null && pn.isNotEmpty) parts.add('PN $pn');
      return parts.join(' • ');
    }
    return '$cpu • ${ramGb}GB RAM • $storageValue $storageUnit $storageType';
  }

  factory InventoryItem.fromJson(Map<String, dynamic> json) {
    final category = productCategoryFromString(json['category'] as String?);
    return InventoryItem(
      id: json['id'] as String,
      serialNumber: json['serial_number'] as String,
      productModelId: json['product_model_id'] as String,
      brandId: json['brand_id'] as int,
      brandName: json['brand_name'] as String,
      category: category,
      accessoryKind: accessoryKindFromString(json['accessory_kind'] as String?),
      partNumber: json['part_number'] as String?,
      modelNumber: json['model_number'] as String,
      modelName: json['model_name'] as String,
      cpu: json['cpu'] as String? ?? '',
      gpu: json['gpu'] as String?,
      ramGb: (json['ram_gb'] as num?)?.toInt() ?? 0,
      storageValue: json['storage_value']?.toString() ?? '',
      storageUnit: json['storage_unit'] as String? ?? 'GB',
      storageType: json['storage_type'] as String? ?? 'SSD',
      color: json['color'] as String,
      currentLocationId: json['current_location_id'] as int,
      currentLocationName: json['current_location_name'] as String,
      status: inventoryStatusFromString(json['status'] as String),
      isArchived: json['is_archived'] as bool? ?? false,
      purchaseDate: json['purchase_date'] as String?,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'serial_number': serialNumber,
        'product_model_id': productModelId,
        'brand_id': brandId,
        'brand_name': brandName,
        'category': productCategoryToApi(category),
        if (accessoryKind != null) 'accessory_kind': accessoryKindToApi(accessoryKind!),
        if (partNumber != null) 'part_number': partNumber,
        'model_number': modelNumber,
        'model_name': modelName,
        'cpu': cpu,
        if (gpu != null) 'gpu': gpu,
        'ram_gb': ramGb,
        'storage_value': storageValue,
        'storage_unit': storageUnit,
        'storage_type': storageType,
        'color': color,
        'current_location_id': currentLocationId,
        'current_location_name': currentLocationName,
        'status': status.name,
        'is_archived': isArchived,
        if (purchaseDate != null) 'purchase_date': purchaseDate,
        'created_at': createdAt,
        'updated_at': updatedAt,
      };

  @override
  List<Object?> get props => [id, serialNumber, status, currentLocationId];
}

class MarkSoldRequest extends Equatable {
  const MarkSoldRequest({
    required this.invoiceNumber,
    required this.customerName,
    required this.paymentMode,
    required this.saleDate,
    this.saleAmount,
    this.remarks,
  });

  final String invoiceNumber;
  final String customerName;
  final String paymentMode;
  final String saleDate;
  final double? saleAmount;
  final String? remarks;

  Map<String, dynamic> toJson() => {
        'invoice_number': invoiceNumber,
        'customer_name': customerName,
        'payment_mode': paymentMode,
        'sale_date': saleDate,
        if (saleAmount != null) 'sale_amount': saleAmount,
        if (remarks != null) 'remarks': remarks,
      };

  @override
  List<Object?> get props => [invoiceNumber, customerName, paymentMode, saleDate];
}

class CreateInventoryItemRequest {
  const CreateInventoryItemRequest({
    required this.serialNumber,
    required this.productModelId,
    required this.color,
    required this.currentLocationId,
    this.purchasePrice,
  });

  final String serialNumber;
  final String productModelId;
  final String color;
  final int currentLocationId;
  final double? purchasePrice;

  Map<String, dynamic> toJson() => {
        'serial_number': serialNumber,
        'product_model_id': productModelId,
        'color': color,
        'current_location_id': currentLocationId,
        'status': 'available',
        if (purchasePrice != null) 'purchase_price': purchasePrice,
      };
}

class Brand extends Equatable {
  const Brand({required this.id, required this.name, required this.isActive, this.logoFilename});

  final int id;
  final String name;
  final bool isActive;
  final String? logoFilename;

  factory Brand.fromJson(Map<String, dynamic> json) => Brand(
        id: (json['id'] as num).toInt(),
        name: json['name'] as String,
        isActive: json['is_active'] as bool? ?? true,
        logoFilename: json['logo_filename'] as String?,
      );

  @override
  List<Object?> get props => [id, name];
}

class Location extends Equatable {
  const Location({required this.id, required this.name, required this.isActive});

  final int id;
  final String name;
  final bool isActive;

  factory Location.fromJson(Map<String, dynamic> json) => Location(
        id: json['id'] as int,
        name: json['name'] as String,
        isActive: json['is_active'] as bool? ?? true,
      );

  @override
  List<Object?> get props => [id, name];
}

class ProductModel extends Equatable {
  const ProductModel({
    required this.id,
    required this.brandId,
    this.brandName,
    this.category = ProductCategory.laptop,
    this.accessoryKind,
    this.partNumber,
    required this.modelNumber,
    required this.modelName,
    this.cpu = '',
    this.gpu,
    this.ramGb = 0,
    this.storageValue = '',
    this.storageUnit = 'GB',
    this.storageType = 'SSD',
    this.display,
    required this.status,
    this.productImageUrl,
    this.sellingPrice,
    this.purchasePrice,
    this.notes,
    this.colorOptions,
    this.livePrice,
    this.livePriceStatus,
    this.livePriceSourceUrl,
    this.livePriceCheckedAt,
    this.livePriceUpdatedAt,
  });

  final String id;
  final int brandId;
  final String? brandName;
  final ProductCategory category;
  final AccessoryKind? accessoryKind;
  final String? partNumber;
  final String modelNumber;
  final String modelName;
  final String cpu;
  final String? gpu;
  final int ramGb;
  final String storageValue;
  final String storageUnit;
  final String storageType;
  final String? display;
  final String status;
  final String? productImageUrl;
  final double? sellingPrice;
  final double? purchasePrice;
  final String? notes;
  final String? colorOptions;
  final double? livePrice;
  final String? livePriceStatus;
  final String? livePriceSourceUrl;
  final DateTime? livePriceCheckedAt;
  final DateTime? livePriceUpdatedAt;

  bool get isAsusBrand => (brandName ?? '').trim().toUpperCase() == 'ASUS';

  bool get isAccessory => isAccessoryModel(category: category);
  bool get isLaptop => isLaptopModel(category: category);

  String get specsLabel {
    if (isAccessory) {
      final parts = <String>[accessoryKindLabel(accessoryKind)];
      final pn = partNumber?.trim();
      if (pn != null && pn.isNotEmpty) parts.add('PN $pn');
      return parts.join(' • ');
    }
    return '$cpu • ${ramGb}GB RAM • $storageValue $storageUnit $storageType';
  }

  factory ProductModel.fromJson(Map<String, dynamic> json) => ProductModel(
        id: json['id'] as String,
        brandId: (json['brand_id'] as num).toInt(),
        brandName: json['brand_name'] as String?,
        category: productCategoryFromString(json['category'] as String?),
        accessoryKind: accessoryKindFromString(json['accessory_kind'] as String?),
        partNumber: json['part_number'] as String?,
        modelNumber: json['model_number'] as String,
        modelName: json['model_name'] as String,
        cpu: json['cpu'] as String? ?? '',
        gpu: json['gpu'] as String?,
        ramGb: (json['ram_gb'] as num?)?.toInt() ?? 0,
        storageValue: json['storage_value']?.toString() ?? '',
        storageUnit: json['storage_unit'] as String? ?? 'GB',
        storageType: json['storage_type'] as String? ?? 'SSD',
        display: json['display'] as String?,
        status: json['status'] as String? ?? 'active',
        productImageUrl: json['product_image_url'] as String?,
        sellingPrice: (json['selling_price'] as num?)?.toDouble(),
        purchasePrice: (json['purchase_price'] as num?)?.toDouble(),
        notes: json['notes'] as String?,
        colorOptions: json['color_options'] as String?,
        livePrice: (json['live_price'] as num?)?.toDouble(),
        livePriceStatus: json['live_price_status'] as String?,
        livePriceSourceUrl: json['live_price_source_url'] as String?,
        livePriceCheckedAt: json['live_price_checked_at'] == null
            ? null
            : DateTime.tryParse(json['live_price_checked_at'] as String),
        livePriceUpdatedAt: json['live_price_updated_at'] == null
            ? null
            : DateTime.tryParse(json['live_price_updated_at'] as String),
      );

  @override
  List<Object?> get props => [id, modelNumber];
}

class InventoryListFilters extends Equatable {
  const InventoryListFilters({
    this.brandId,
    this.productModelId,
    this.currentLocationId,
    this.status,
    this.isArchived,
    this.includeArchived = false,
    this.search,
    this.color,
  });

  final int? brandId;
  final String? productModelId;
  final int? currentLocationId;
  final InventoryStatus? status;
  final bool? isArchived;
  final bool includeArchived;
  final String? search;
  final String? color;

  Map<String, dynamic> toQueryParams({int page = 1, int pageSize = 50}) {
    return {
      'page': page,
      'page_size': pageSize,
      'sort': 'updated_at:desc',
      if (brandId != null) 'brand_id': brandId,
      if (productModelId != null) 'product_model_id': productModelId,
      if (currentLocationId != null) 'current_location_id': currentLocationId,
      if (status != null) 'status': status!.name,
      if (isArchived != null) 'is_archived': isArchived,
      if (includeArchived) 'include_archived': true,
      if (search != null && search!.trim().isNotEmpty) 'search': search!.trim(),
      if (color != null && color!.trim().isNotEmpty) 'color': color!.trim(),
    };
  }

  InventoryListFilters copyWith({
    int? brandId,
    String? productModelId,
    int? currentLocationId,
    InventoryStatus? status,
    bool? isArchived,
    bool? includeArchived,
    String? search,
    String? color,
    bool clearStatus = false,
  }) {
    return InventoryListFilters(
      brandId: brandId ?? this.brandId,
      productModelId: productModelId ?? this.productModelId,
      currentLocationId: currentLocationId ?? this.currentLocationId,
      status: clearStatus ? null : status ?? this.status,
      isArchived: isArchived ?? this.isArchived,
      includeArchived: includeArchived ?? this.includeArchived,
      search: search ?? this.search,
      color: color ?? this.color,
    );
  }

  @override
  List<Object?> get props => [brandId, productModelId, currentLocationId, status, isArchived, search, color];
}
