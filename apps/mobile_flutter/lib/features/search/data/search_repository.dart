import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../domain/search_models.dart';

class SearchRepository {
  SearchRepository(this._api);

  final ApiClient _api;

  Future<GlobalSearchResult> search(String query, {List<String>? types, int limit = 15}) async {
    return _api.get(
      ApiPaths.search,
      queryParameters: {
        'q': query,
        'limit': limit,
        if (types != null && types.isNotEmpty) 'types': types,
      },
      parser: (json) => GlobalSearchResult.fromJson(json! as Map<String, dynamic>),
    );
  }
}

final searchRepositoryProvider = Provider<SearchRepository>((ref) {
  return SearchRepository(ref.watch(apiClientProvider));
});
