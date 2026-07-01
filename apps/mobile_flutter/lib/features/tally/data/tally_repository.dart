import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';

class TallyRepository {
  TallyRepository(this._api);

  final ApiClient _api;

  Future<Map<String, dynamic>> triggerSync() async {
    return _api.post(
      ApiPaths.tallySyncTrigger,
      data: const {},
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
  }

  Future<Map<String, dynamic>> retrySync() async {
    return _api.post(
      ApiPaths.tallySyncRetry,
      data: const {},
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
  }

  Future<Map<String, dynamic>> testConnection() async {
    return _api.post(
      ApiPaths.tallyConnectionTest,
      data: const {},
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
  }
}

final tallyRepositoryProvider = Provider<TallyRepository>((ref) {
  return TallyRepository(ref.watch(apiClientProvider));
});
