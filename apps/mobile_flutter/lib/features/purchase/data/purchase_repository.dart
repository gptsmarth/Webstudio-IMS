import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/json_map.dart';
import '../domain/purchase_models.dart';

class PurchaseRepository {
  PurchaseRepository(this._api);

  final ApiClient _api;

  Future<List<PurchaseQueueItem>> listQueue({String? status}) async {
    return _api.get(
      ApiPaths.purchaseQueue,
      queryParameters: status == null ? null : {'status': status},
      parser: (json) {
        final list = json as List<dynamic>? ?? const [];
        return list
            .whereType<Map<String, dynamic>>()
            .map(PurchaseQueueItem.fromJson)
            .toList();
      },
    );
  }

  Future<PurchaseVoucherDetail> getVoucher(int voucherId) async {
    return _api.get(
      ApiPaths.purchaseVoucher(voucherId),
      parser: (json) => PurchaseVoucherDetail.fromJson(asJsonMap(json)),
    );
  }

  Future<MatchModelResponse> matchModel({
    required int brandId,
    required String modelNumber,
  }) async {
    return _api.post(
      ApiPaths.purchaseMatchModel,
      data: {'brand_id': brandId, 'model_number': modelNumber},
      parser: (json) => MatchModelResponse.fromJson(asJsonMap(json)),
    );
  }

  Future<MatchAccessoryResponse> matchAccessory({
    required int brandId,
    required String query,
  }) async {
    return _api.post(
      ApiPaths.purchaseMatchAccessory,
      data: {'brand_id': brandId, 'query': query},
      parser: (json) => MatchAccessoryResponse.fromJson(asJsonMap(json)),
    );
  }

  Future<PurchaseImportResult> importGroup(PurchaseImportRequest request) async {
    return _api.post(
      ApiPaths.purchaseImport,
      data: request.toJson(),
      parser: (json) => PurchaseImportResult.fromJson(asJsonMap(json)),
    );
  }

  Future<String> ignoreVoucher(int voucherId) async {
    return _api.post(
      ApiPaths.purchaseIgnore(voucherId),
      data: const <String, dynamic>{},
      parser: (json) => asJsonMap(json)['status'] as String? ?? 'ignored',
    );
  }

  Future<PurchaseBackfillResult> backfill({
    required String fromDate,
    String? toDate,
  }) async {
    return _api.post(
      ApiPaths.purchaseBackfill,
      data: {
        'from_date': fromDate,
        if (toDate != null) 'to_date': toDate,
      },
      // Backfills scan a whole date range against Tally — allow up to 5 minutes.
      receiveTimeout: const Duration(minutes: 5),
      parser: (json) => PurchaseBackfillResult.fromJson(asJsonMap(json)),
    );
  }
}

final purchaseRepositoryProvider = Provider<PurchaseRepository>((ref) {
  return PurchaseRepository(ref.watch(apiClientProvider));
});

final purchaseQueueProvider =
    FutureProvider.autoDispose.family<List<PurchaseQueueItem>, String?>((ref, status) async {
  return ref.watch(purchaseRepositoryProvider).listQueue(status: status);
});

final purchaseVoucherProvider =
    FutureProvider.autoDispose.family<PurchaseVoucherDetail, int>((ref, voucherId) async {
  return ref.watch(purchaseRepositoryProvider).getVoucher(voucherId);
});
