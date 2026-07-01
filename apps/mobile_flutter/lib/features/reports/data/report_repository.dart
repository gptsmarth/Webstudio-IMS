import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/errors/api_exception.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/json_map.dart';
import '../../../shared/models/downloaded_file.dart';
import '../domain/report_models.dart';

class ReportRepository {
  ReportRepository(this._api);

  final ApiClient _api;

  Future<ReportPreviewResult> preview(ReportType type, ReportQueryParams params) async {
    try {
      final response = await _api.dio.get<dynamic>(
        type.previewPath,
        queryParameters: params.toQueryParams(type),
      );
      return _parsePreviewResponse(response.data, params);
    } on DioException catch (error) {
      throw _mapDioError(error);
    }
  }

  ReportPreviewResult _parsePreviewResponse(Object? body, ReportQueryParams params) {
    final envelope = asJsonMapOrNull(body);
    if (envelope == null) {
      throw const FormatException('Unexpected report response');
    }
    final data = asJsonMapOrNull(envelope['data']);
    if (data == null) {
      throw const FormatException('Report response missing data');
    }
    final meta = asJsonMapOrNull(envelope['meta']) ?? {};
    final rows = asJsonMapList(data['rows']);
    return ReportPreviewResult(
      rows: rows,
      page: meta['page'] as int? ?? params.page,
      pageSize: meta['page_size'] as int? ?? params.pageSize,
      totalItems: meta['total_items'] as int? ?? rows.length,
      totalPages: meta['total_pages'] as int? ?? 1,
      summary: asJsonMapOrNull(data['summary']),
    );
  }

  Future<DownloadedFile> exportReport(
    ReportType type,
    ReportQueryParams params, {
    String format = 'xlsx',
  }) async {
    final query = {
      'report_type': type.exportType,
      'format': format,
      ...params.toQueryParams(type),
    };
    return _api.downloadBytes(
      ApiPaths.reportsExport,
      queryParameters: query,
      fallbackFilename: 'report-${type.name}.$format',
    );
  }

  ApiException _mapDioError(DioException error) {
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout) {
      return const NetworkException();
    }

    final map = asJsonMapOrNull(error.response?.data);
    if (map != null) {
      if (map.containsKey('error')) {
        return ApiErrorEnvelope.fromJson(map).toException(statusCode: error.response?.statusCode);
      }
      if (map.containsKey('detail')) {
        return ApiException(
          code: 'API_ERROR',
          message: map['detail'].toString(),
          statusCode: error.response?.statusCode,
        );
      }
    }

    return ApiException(
      code: 'API_ERROR',
      message: error.message ?? 'Request failed',
      statusCode: error.response?.statusCode,
    );
  }
}

final reportRepositoryProvider = Provider<ReportRepository>((ref) {
  return ReportRepository(ref.watch(apiClientProvider));
});
