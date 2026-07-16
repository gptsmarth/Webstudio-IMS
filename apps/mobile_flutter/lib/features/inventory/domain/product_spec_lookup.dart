import '../domain/inventory_models.dart';

ProductModel? findModelByNumber(
  List<ProductModel> models,
  String modelNumber, {
  int? brandId,
}) {
  final normalized = modelNumber.trim().toLowerCase();
  if (normalized.isEmpty) return null;

  final pool = brandId == null ? models : models.where((model) => model.brandId == brandId);
  for (final model in pool) {
    if (model.modelNumber.trim().toLowerCase() == normalized) {
      return model;
    }
  }
  return null;
}

String composeModelNotes(String? description, String? specNotes) {
  final desc = description?.trim() ?? '';
  final specs = specNotes?.trim() ?? '';
  if (desc.isEmpty) return specs;
  if (specs.isEmpty) return desc;
  return '$desc\n---\n$specs';
}

/// Inventory unit `color` is capped at 64 chars by the API.
const int kInventoryColorMaxLength = 64;

String defaultUnitColorFromOptions(String? colorOptions) {
  if (colorOptions == null || colorOptions.trim().isEmpty) {
    return 'Not specified';
  }
  // AI / catalogue often returns "Black / Silver" or long prose without commas.
  for (final entry in colorOptions.split(RegExp(r'[,;/|]'))) {
    final trimmed = entry.trim();
    if (trimmed.isEmpty) continue;
    if (trimmed.length <= kInventoryColorMaxLength) return trimmed;
    return trimmed.substring(0, kInventoryColorMaxLength).trimRight();
  }
  return 'Not specified';
}

class FetchedProductSpec {
  const FetchedProductSpec({
    required this.modelName,
    required this.cpu,
    this.gpu,
    required this.ramGb,
    required this.storageValue,
    required this.storageUnit,
    required this.storageType,
    this.display,
    this.colorOptions,
    this.productImageUrl,
    this.description,
    this.notes,
  });

  final String modelName;
  final String cpu;
  final String? gpu;
  final int ramGb;
  final String storageValue;
  final String storageUnit;
  final String storageType;
  final String? display;
  final String? colorOptions;
  final String? productImageUrl;
  final String? description;
  final String? notes;

  factory FetchedProductSpec.fromApi(Map<String, dynamic> json) {
    return FetchedProductSpec(
      modelName: json['model_name'] as String? ?? '',
      cpu: json['cpu'] as String? ?? '',
      gpu: json['gpu'] as String?,
      ramGb: json['ram_gb'] as int? ?? 16,
      storageValue: json['storage_value']?.toString() ?? '512',
      storageUnit: json['storage_unit'] as String? ?? 'GB',
      storageType: json['storage_type'] as String? ?? 'SSD',
      display: json['display'] as String?,
      colorOptions: json['color_options'] as String?,
      productImageUrl: json['product_image_url'] as String?,
      description: json['description'] as String?,
      notes: json['notes'] as String?,
    );
  }

  factory FetchedProductSpec.fromProductModel(ProductModel model) {
    return FetchedProductSpec(
      modelName: model.modelName,
      cpu: model.cpu,
      gpu: model.gpu,
      ramGb: model.ramGb,
      storageValue: model.storageValue,
      storageUnit: model.storageUnit,
      storageType: model.storageType,
      display: model.display,
      colorOptions: model.colorOptions,
      productImageUrl: model.productImageUrl,
      description: null,
      notes: model.notes,
    );
  }
}

class SerialUnitEntry {
  const SerialUnitEntry({
    required this.serialNumber,
    required this.currentLocationId,
    required this.color,
  });

  final String serialNumber;
  final int currentLocationId;
  final String color;
}

class AddLaptopWizardRequest {
  const AddLaptopWizardRequest({
    required this.brandId,
    required this.mode,
    this.productModelId,
    this.newProductModel,
    required this.units,
  });

  final int brandId;
  final String mode;
  final String? productModelId;
  final Map<String, dynamic>? newProductModel;
  final List<SerialUnitEntry> units;
}
