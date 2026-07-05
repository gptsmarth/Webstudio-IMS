import 'package:dio/dio.dart';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/app_config.dart';
import '../constants/api_paths.dart';
import '../errors/api_exception.dart';
import 'json_map.dart';
import '../storage/secure_token_storage.dart';
import '../../shared/models/downloaded_file.dart';
import '../../shared/models/pagination.dart';

typedef TokenRefreshCallback = Future<bool> Function();

class ApiClient {
  ApiClient({
    required AppConfig config,
    required SecureTokenStorage tokenStorage,
    Dio? dio,
    TokenRefreshCallback? onRefreshToken,
  })  : _config = config,
        _tokenStorage = tokenStorage,
        _onRefreshToken = onRefreshToken,
        _dio = dio ?? Dio() {
    _configureDio();
  }

  final AppConfig _config;
  final SecureTokenStorage _tokenStorage;
  final TokenRefreshCallback? _onRefreshToken;
  final Dio _dio;

  Dio get dio => _dio;

  void updateConfig(AppConfig config) {
    _dio.options.baseUrl = config.apiBaseUrl;
    _dio.options.headers['X-Client-Version'] = config.clientVersion;
    _dio.options.headers['X-Client-Platform'] = config.clientPlatform;
  }

  void _configureDio() {
    _dio.options = BaseOptions(
      baseUrl: _config.apiBaseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Client-Version': _config.clientVersion,
        'X-Client-Platform': _config.clientPlatform,
      },
    );

    _dio.interceptors.clear();
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _tokenStorage.getAccessToken();
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          final response = error.response;
          final path = error.requestOptions.path;
          final isAuthRoute = path.contains('/auth/login') || path.contains('/auth/refresh');

          if (response?.statusCode == 401 && !isAuthRoute && _onRefreshToken != null) {
            final renewed = await _onRefreshToken();
            if (renewed) {
              final token = await _tokenStorage.getAccessToken();
              error.requestOptions.headers['Authorization'] = 'Bearer $token';
              try {
                final retried = await _dio.fetch<dynamic>(error.requestOptions);
                return handler.resolve(retried);
              } catch (retryError) {
                if (retryError is DioException) {
                  return handler.next(retryError);
                }
                return handler.next(error);
              }
            }
          }

          handler.next(error);
        },
      ),
    );
  }

  Future<T> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    required T Function(Object? json) parser,
  }) async {
    return _request(() => _dio.get<dynamic>(path, queryParameters: queryParameters), parser);
  }

  Future<T> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    required T Function(Object? json) parser,
  }) async {
    return _request(() => _dio.post<dynamic>(path, data: data, queryParameters: queryParameters), parser);
  }

  Future<T> put<T>(
    String path, {
    Object? data,
    required T Function(Object? json) parser,
  }) async {
    return _request(() => _dio.put<dynamic>(path, data: data), parser);
  }

  Future<T> delete<T>(
    String path, {
    Object? data,
    required T Function(Object? json) parser,
  }) async {
    return _request(() => _dio.delete<dynamic>(path, data: data), parser);
  }

  Future<T> patch<T>(
    String path, {
    Object? data,
    required T Function(Object? json) parser,
  }) async {
    return _request(() => _dio.patch<dynamic>(path, data: data), parser);
  }

  Future<DownloadedFile> downloadBytes(
    String path, {
    Map<String, dynamic>? queryParameters,
    String fallbackFilename = 'download.bin',
  }) async {
    try {
      final response = await _dio.get<List<int>>(
        path,
        queryParameters: queryParameters,
        options: Options(responseType: ResponseType.bytes),
      );
      final bytes = response.data;
      if (bytes == null) {
        throw const ApiException(code: 'API_ERROR', message: 'Empty file response.');
      }
      final disposition = response.headers.value('content-disposition');
      final filename = _filenameFromDisposition(disposition, fallbackFilename);
      return DownloadedFile(
        bytes: Uint8List.fromList(bytes),
        filename: filename,
        mimeType: response.headers.value('content-type'),
      );
    } on DioException catch (error) {
      throw _mapDioError(error);
    }
  }

  Future<T> postMultipart<T>({
    required String path,
    required Map<String, dynamic> fields,
    required Map<String, MultipartFile> files,
    required T Function(Object? json) parser,
  }) async {
    final formData = FormData.fromMap({...fields, ...files});
    return _request(() => _dio.post<dynamic>(path, data: formData), parser);
  }

  String _filenameFromDisposition(String? header, String fallback) {
    if (header == null) return fallback;
    final match = RegExp(r'filename="?([^";]+)"?').firstMatch(header);
    return match?.group(1) ?? fallback;
  }

  Future<PaginatedResult<T>> getPaginated<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    required T Function(Object? json) itemParser,
  }) async {
    try {
      final response = await _dio.get<dynamic>(path, queryParameters: queryParameters);
      final envelope = asJsonMapOrNull(response.data);
      if (envelope == null) {
        throw const ApiException(code: 'API_ERROR', message: 'Unexpected list response.');
      }
      final rawItems = envelope['data'];
      final meta = asJsonMapOrNull(envelope['meta']) ?? {};
      final items = rawItems is List
          ? rawItems.map((entry) => itemParser(asJsonMap(entry))).toList()
          : <T>[];
      return PaginatedResult(
        items: items,
        page: meta['page'] as int? ?? 1,
        pageSize: meta['page_size'] as int? ?? items.length,
        totalItems: meta['total_items'] as int? ?? items.length,
        totalPages: meta['total_pages'] as int? ?? 1,
      );
    } on DioException catch (error) {
      throw _mapDioError(error);
    }
  }

  Future<bool> checkHealthLive() => checkHealthLiveAt(_dio.options.baseUrl);

  Future<bool> checkHealthLiveAt(String baseUrl) async {
    try {
      final response = await _dio.get<dynamic>(
        '$baseUrl${ApiPaths.healthLive}',
        options: Options(
        connectTimeout: const Duration(seconds: 4),
        sendTimeout: const Duration(seconds: 4),
        receiveTimeout: const Duration(seconds: 4),
      ),
      );
      return response.statusCode == 200;
    } on DioException {
      return false;
    }
  }

  Future<T> getAt<T>(
    String baseUrl,
    String path, {
    Map<String, dynamic>? queryParameters,
    required T Function(Object? json) parser,
  }) async {
    return _request(
      () => _dio.get<dynamic>(
        '$baseUrl$path',
        queryParameters: queryParameters,
        options: Options(
          connectTimeout: const Duration(seconds: 8),
          sendTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
        ),
      ),
      parser,
    );
  }

  Future<T> _request<T>(
    Future<Response<dynamic>> Function() call,
    T Function(Object? json) parser,
  ) async {
    try {
      final response = await call();
      return _unwrap(response.data, parser);
    } on DioException catch (error) {
      throw _mapDioError(error);
    }
  }

  T _unwrap<T>(dynamic body, T Function(Object? json) parser) {
    final envelope = asJsonMapOrNull(body);
    if (envelope != null && envelope.containsKey('data')) {
      return parser(envelope['data']);
    }
    return parser(body);
  }

  ApiException _mapDioError(DioException error) {
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout) {
      return const NetworkException();
    }

    final response = error.response;
    final data = response?.data;
    final map = asJsonMapOrNull(data);
    if (map != null) {
      if (map.containsKey('error')) {
        return ApiErrorEnvelope.fromJson(map).toException(statusCode: response?.statusCode);
      }
      if (map.containsKey('detail')) {
        return ApiException(
          code: 'API_ERROR',
          message: map['detail'].toString(),
          statusCode: response?.statusCode,
        );
      }
    }

    return ApiException(
      code: 'API_ERROR',
      message: error.message ?? 'Request failed',
      statusCode: response?.statusCode,
    );
  }
}

final secureTokenStorageProvider = Provider<SecureTokenStorage>((ref) => SecureTokenStorage());

final apiClientProvider = Provider<ApiClient>((ref) {
  throw UnimplementedError('apiClientProvider must be overridden in bootstrap');
});
