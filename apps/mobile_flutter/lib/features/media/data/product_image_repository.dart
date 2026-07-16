import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';

class ProductImageUploadResult {
  const ProductImageUploadResult({
    required this.productModelId,
    required this.productImageUrl,
  });

  final String productModelId;
  final String productImageUrl;

  factory ProductImageUploadResult.fromJson(Map<String, dynamic> json) => ProductImageUploadResult(
        productModelId: json['product_model_id'] as String,
        productImageUrl: json['product_image_url'] as String,
      );
}

class ProductImageRepository {
  ProductImageRepository(this._api);

  final ApiClient _api;
  final Map<String, Uint8List> _byteCache = {};

  Future<ProductImageUploadResult> upload({
    required String productModelId,
    required String filename,
    required List<int> bytes,
    String? mimeType,
  }) async {
    return _api.postMultipart(
      path: ApiPaths.productImagesUpload,
      fields: {'product_model_id': productModelId},
      files: {
        'file': MultipartFile.fromBytes(bytes, filename: filename),
      },
      parser: (json) => ProductImageUploadResult.fromJson(json! as Map<String, dynamic>),
    );
  }

  String proxyUrl(String imageUrl) {
    final trimmed = imageUrl.trim();
    if (trimmed.isEmpty) return trimmed;
    final base = _api.dio.options.baseUrl.replaceAll(RegExp(r'/$'), '');
    if (trimmed.startsWith('https://') || trimmed.startsWith('/assets/')) {
      return '$base${ApiPaths.productImagesProxy}?url=${Uri.encodeComponent(trimmed)}';
    }
    if (trimmed.startsWith('http://')) {
      return trimmed;
    }
    return '$base$trimmed';
  }

  /// Fetches image bytes through the authenticated API proxy (required on mobile).
  Future<Uint8List?> fetchImageBytes(String imageUrl) async {
    final trimmed = imageUrl.trim();
    if (trimmed.isEmpty) return null;
    final cached = _byteCache[trimmed];
    if (cached != null) return cached;

    for (var attempt = 0; attempt < 3; attempt++) {
      final bytes = await _fetchImageBytesOnce(trimmed);
      if (bytes != null) {
        _byteCache[trimmed] = bytes;
        return bytes;
      }
      if (attempt < 2) {
        await Future<void>.delayed(Duration(milliseconds: 400 * (attempt + 1)));
      }
    }
    return null;
  }

  Future<Uint8List?> _fetchImageBytesOnce(String trimmed) async {
    try {
      final String requestPath;
      final Map<String, dynamic>? queryParameters;

      if (trimmed.startsWith('https://') ||
          trimmed.startsWith('http://') ||
          trimmed.startsWith('/assets/')) {
        requestPath = ApiPaths.productImagesProxy;
        queryParameters = {'url': trimmed};
      } else if (trimmed.startsWith('/')) {
        requestPath = trimmed;
        queryParameters = null;
      } else {
        return null;
      }

      final response = await _api.dio.get<List<int>>(
        requestPath,
        queryParameters: queryParameters,
        options: Options(
          responseType: ResponseType.bytes,
          validateStatus: (status) => status != null && status < 500,
        ),
      );
      if (response.statusCode != 200 || response.data == null || response.data!.isEmpty) {
        return null;
      }
      return Uint8List.fromList(response.data!);
    } catch (_) {
      return null;
    }
  }

  /// Resolve a product image. When [wait] is true, blocks until discovery finishes.
  /// When false (default), schedules background work and may return source=pending.
  Future<Map<String, dynamic>> resolveViaAi(
    String productModelId, {
    bool wait = false,
  }) async {
    return _api.post(
      '${ApiPaths.productModelResolveImage(productModelId)}?wait=$wait',
      data: const {},
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
  }

  /// Polls resolve-image until an image URL is available or attempts exhaust.
  Future<String?> resolveAndWaitForImage(
    String productModelId, {
    Duration timeout = const Duration(seconds: 45),
    Duration pollInterval = const Duration(seconds: 2),
  }) async {
    var result = await resolveViaAi(productModelId, wait: true);
    final immediate = (result['product_image_url'] as String?)?.trim();
    if (immediate != null && immediate.isNotEmpty) return immediate;

    final deadline = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(deadline)) {
      await Future<void>.delayed(pollInterval);
      result = await resolveViaAi(productModelId, wait: false);
      final url = (result['product_image_url'] as String?)?.trim();
      if (url != null && url.isNotEmpty) return url;
      if (result['source'] != 'pending') break;
    }
    return null;
  }
}

final productImageRepositoryProvider = Provider<ProductImageRepository>((ref) {
  return ProductImageRepository(ref.watch(apiClientProvider));
});
