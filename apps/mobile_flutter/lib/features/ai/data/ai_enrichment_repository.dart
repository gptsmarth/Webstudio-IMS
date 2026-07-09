import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/json_map.dart';
import '../../inventory/domain/product_category.dart';

class AiEnrichmentRepository {
  AiEnrichmentRepository(this._api);

  final ApiClient _api;

  Future<Map<String, dynamic>> lookupSpecs({
    required String brandName,
    required String modelNumber,
    String? modelName,
    bool forceRefresh = false,
  }) async {
    return _api.post(
      ApiPaths.productModelsSpecLookup,
      data: {
        'brand_name': brandName,
        'model_number': modelNumber,
        if (modelName != null) 'model_name': modelName,
        if (forceRefresh) 'force_refresh': true,
      },
      parser: (json) => asJsonMap(json),
    );
  }

  Future<Map<String, dynamic>> lookupAccessorySpec({
    required String identifier,
    AccessoryIdentifierType identifierType = AccessoryIdentifierType.modelNumber,
    String? brandName,
    String? modelName,
    bool forceRefresh = false,
  }) async {
    return _api.post(
      ApiPaths.productModelsAccessorySpecLookup,
      data: {
        'identifier': identifier,
        'identifier_type': identifierTypeToApi(identifierType),
        if (brandName != null && brandName.trim().isNotEmpty) 'brand_name': brandName.trim(),
        if (modelName != null && modelName.trim().isNotEmpty) 'model_name': modelName.trim(),
        if (forceRefresh) 'force_refresh': true,
      },
      parser: (json) => asJsonMap(json),
    );
  }

  Future<Map<String, dynamic>> testAiProvider() async {
    return _api.post(
      ApiPaths.settingsIntegrationsAiTest,
      data: const {},
      parser: (json) => asJsonMap(json),
    );
  }
}

final aiEnrichmentRepositoryProvider = Provider<AiEnrichmentRepository>((ref) {
  return AiEnrichmentRepository(ref.watch(apiClientProvider));
});
