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
    if (!trimmed.startsWith('https://') && !trimmed.startsWith('/assets/')) {
      return null;
    }

    try {
      final response = await _api.dio.get<List<int>>(
        ApiPaths.productImagesProxy,
        queryParameters: {'url': trimmed},
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

  Future<Map<String, dynamic>> resolveViaAi(String productModelId) async {
    return _api.post(
      ApiPaths.productModelResolveImage(productModelId),
      data: const {},
      parser: (json) => Map<String, dynamic>.from(json! as Map),
    );
  }
}

final productImageRepositoryProvider = Provider<ProductImageRepository>((ref) {
  return ProductImageRepository(ref.watch(apiClientProvider));
});
