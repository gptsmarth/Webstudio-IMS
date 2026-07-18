import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../../../shared/models/pagination.dart';
import '../domain/sales_models.dart';

class SalesRepository {
  SalesRepository(this._api);

  final ApiClient _api;

  Future<PaginatedResult<SaleListItem>> listSales({
    SalesListFilters filters = const SalesListFilters(),
    String search = '',
    int page = 1,
    int pageSize = 50,
    SalesSortField sortField = SalesSortField.soldAt,
    String sortDirection = 'desc',
  }) async {
    return _api.getPaginated(
      ApiPaths.sales,
      queryParameters: filters.toQueryParams(
        page: page,
        pageSize: pageSize,
        search: search,
        sortField: sortField,
        sortDirection: sortDirection,
      ),
      itemParser: (json) => SaleListItem.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<SaleDetail> getSale(int saleId) async {
    return _api.get(
      '${ApiPaths.sales}/$saleId',
      parser: (json) => SaleDetail.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<CancelSaleResult> cancelSale(int saleId, {String? reason}) async {
    return _api.post(
      '${ApiPaths.sales}/$saleId/cancel',
      data: {'reason': reason},
      parser: (json) => CancelSaleResult.fromJson(json! as Map<String, dynamic>),
    );
  }

  Future<SalesBackfillResult> backfillSales({
    required String fromDate,
    String? toDate,
  }) async {
    return _api.post(
      ApiPaths.tallySalesBackfill,
      data: {
        'from_date': fromDate,
        if (toDate != null) 'to_date': toDate,
      },
      parser: (json) => SalesBackfillResult.fromJson(json! as Map<String, dynamic>),
    );
  }
}

final salesRepositoryProvider = Provider<SalesRepository>((ref) {
  return SalesRepository(ref.watch(apiClientProvider));
});
