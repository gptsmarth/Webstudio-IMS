import 'inventory_models.dart';
import 'product_category.dart';

class FetchedAccessorySpec {
  const FetchedAccessorySpec({
    required this.modelName,
    this.modelNumber,
    this.partNumber,
    this.accessoryKind,
    this.colorOptions,
    this.productImageUrl,
    this.description,
    this.notes,
    this.source = AccessorySpecSource.gemini,
  });

  final String modelName;
  final String? modelNumber;
  final String? partNumber;
  final AccessoryKind? accessoryKind;
  final String? colorOptions;
  final String? productImageUrl;
  final String? description;
  final String? notes;
  final AccessorySpecSource source;
}

enum AccessorySpecSource { database, gemini }

ProductModel? findAccessoryByIdentifier(
  List<ProductModel> models,
  String identifier, {
  int? brandId,
}) {
  final normalized = identifier.trim().toLowerCase();
  if (normalized.isEmpty) return null;

  final pool = brandId == null
      ? models.where((model) => model.isAccessory)
      : models.where((model) => model.brandId == brandId && model.isAccessory);

  for (final model in pool) {
    final modelNumber = model.modelNumber.trim().toLowerCase();
    final partNumber = model.partNumber?.trim().toLowerCase();
    if (modelNumber == normalized || partNumber == normalized) {
      return model;
    }
  }
  return null;
}

FetchedAccessorySpec accessoryToDisplaySpec(ProductModel model) {
  return FetchedAccessorySpec(
    modelName: model.modelName,
    modelNumber: model.modelNumber,
    partNumber: model.partNumber,
    accessoryKind: model.accessoryKind,
    colorOptions: model.colorOptions,
    productImageUrl: model.productImageUrl,
    description: null,
    notes: model.notes,
    source: AccessorySpecSource.database,
  );
}

FetchedAccessorySpec fetchedAccessorySpecFromApi(Map<String, dynamic> json) {
  return FetchedAccessorySpec(
    modelName: json['model_name'] as String? ?? '',
    modelNumber: json['model_number'] as String?,
    partNumber: json['part_number'] as String?,
    accessoryKind: accessoryKindFromString(json['accessory_kind'] as String?),
    colorOptions: json['color_options'] as String?,
    productImageUrl: json['product_image_url'] as String?,
    description: json['description'] as String?,
    notes: json['notes'] as String?,
    source: AccessorySpecSource.gemini,
  );
}

final _inflightAccessoryLookups = <String, Future<FetchedAccessorySpec?>>{};

Future<FetchedAccessorySpec?> fetchAccessorySpecFromInternet(
  Future<FetchedAccessorySpec?> Function() lookup, {
  required String identifier,
  required AccessoryIdentifierType identifierType,
  String? brandName,
  bool forceRefresh = false,
}) {
  final normalized = identifier.trim();
  final normalizedBrand = brandName?.trim().toLowerCase() ?? '';
  final inflightKey =
      '${identifierTypeToApi(identifierType)}:${normalized.toLowerCase()}|$normalizedBrand${forceRefresh ? '|refresh' : ''}';
  final existing = _inflightAccessoryLookups[inflightKey];
  if (existing != null) return existing;

  late final Future<FetchedAccessorySpec?> lookupPromise;
  lookupPromise = lookup().whenComplete(() {
    if (_inflightAccessoryLookups[inflightKey] == lookupPromise) {
      _inflightAccessoryLookups.remove(inflightKey);
    }
  });
  _inflightAccessoryLookups[inflightKey] = lookupPromise;
  return lookupPromise;
}
