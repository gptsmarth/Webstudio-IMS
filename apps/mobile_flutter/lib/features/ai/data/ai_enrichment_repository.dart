import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/json_map.dart';

class AiEnrichmentRepository {
  AiEnrichmentRepository(this._api);

  final ApiClient _api;

  Future<Map<String, dynamic>> lookupSpecs({
    required String brandName,
    required String modelNumber,
    String? modelName,
  }) async {
    return _api.post(
      ApiPaths.productModelsSpecLookup,
      data: {
        'brand_name': brandName,
        'model_number': modelNumber,
        if (modelName != null) 'model_name': modelName,
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
